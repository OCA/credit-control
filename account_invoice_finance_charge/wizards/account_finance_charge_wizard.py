# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from datetime import timedelta

from psycopg2.errors import UniqueViolation

from odoo import Command, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import format_date, formatLang


class AccountFinanceChargeWizard(models.TransientModel):
    _name = "account.finance.charge.wizard"
    _description = "Finance Charge Review"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date(
        string="Charge Through",
        required=True,
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        comodel_name="account.finance.charge.wizard.line",
        inverse_name="wizard_id",
        string="Potential Charges",
    )
    line_count = fields.Integer(compute="_compute_selection")
    selected_count = fields.Integer(compute="_compute_selection")
    selection_summary = fields.Char(compute="_compute_selection")
    policy_summary = fields.Char(compute="_compute_policy_summary")

    @api.constrains("date")
    def _check_date_not_future(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            if wizard.date > today:
                raise ValidationError(
                    self.env._("Finance charges cannot run through a future date.")
                )

    @api.depends("company_id")
    def _compute_display_name(self):
        for wizard in self:
            wizard.display_name = self.env._("Finance Charges")

    @api.depends("line_ids.selected", "line_ids.amount", "line_ids.currency_id")
    def _compute_selection(self):
        for wizard in self:
            selected = wizard.line_ids.filtered("selected")
            totals = defaultdict(float)
            for line in selected:
                totals[line.currency_id] += line.amount
            amount = " + ".join(
                formatLang(self.env, total, currency_obj=currency)
                for currency, total in totals.items()
            ) or formatLang(self.env, 0.0, currency_obj=wizard.company_id.currency_id)
            wizard.line_count = len(wizard.line_ids)
            wizard.selected_count = len(selected)
            wizard.selection_summary = self.env._(
                "%(selected)s of %(total)s selected: %(amount)s",
                selected=len(selected),
                total=len(wizard.line_ids),
                amount=amount,
            )

    @api.depends("company_id")
    def _compute_policy_summary(self):
        for wizard in self:
            company = wizard.company_id
            parts = [
                self.env._(
                    "%(rate)s%% per year", rate=f"{company.finance_charge_rate:g}"
                ),
                self.env._(
                    "%(days)s grace days", days=company.finance_charge_grace_days
                ),
                self.env._(
                    "at least %(days)s days between charges",
                    days=company.finance_charge_interval_days,
                ),
            ]
            if company.finance_charge_min_amount:
                parts.append(
                    self.env._(
                        "minimum %(amount)s",
                        amount=formatLang(
                            self.env,
                            company.finance_charge_min_amount,
                            currency_obj=company.currency_id,
                        ),
                    )
                )
            if company.finance_charge_cap_percent:
                parts.append(
                    self.env._(
                        "capped at %(cap)s%% of the invoice",
                        cap=f"{company.finance_charge_cap_percent:g}",
                    )
                )
            wizard.policy_summary = " · ".join(parts)

    @api.model
    def action_open(self):
        """Build the review screen for the current company."""
        wizard = self.create({})
        wizard._check_configured()
        wizard._load_lines()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Finance Charges"),
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def _check_configured(self):
        self.ensure_one()
        company = self.company_id
        if company.finance_charge_rate and company.finance_charge_account_id:
            return
        if not (
            self.env.user.has_group("base.group_system")
            and self.env.user.has_group("account.group_account_manager")
        ):
            raise UserError(
                self.env._(
                    "Finance charges are not set up yet. Ask an administrator "
                    "to set the annual rate and income account."
                )
            )
        raise RedirectWarning(
            self.env._(
                "Set the annual rate and income account for finance charges "
                "before reviewing them."
            ),
            self.env.ref("account.action_account_config").id,
            self.env._("Open Settings"),
        )

    def _get_candidate_invoices(self):
        self.ensure_one()
        latest_due = self.date - timedelta(
            days=self.company_id.finance_charge_grace_days
        )
        return self.env["account.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("is_finance_charge", "=", False),
                (
                    "payment_state",
                    "not in",
                    ("reversed", "blocked", "invoicing_legacy"),
                ),
                ("invoice_date_due", "<", latest_due),
                ("amount_residual", ">", 0),
            ],
            order="invoice_date_due, id",
        )

    def _get_billed_history(self, invoices):
        """Return {invoice id: (billed through, total charged)}."""
        groups = self.env["account.finance.charge.line"]._read_group(
            [
                ("source_move_id", "in", invoices.ids),
                ("charge_state", "!=", "cancel"),
            ],
            ["source_move_id"],
            ["date_to:max", "amount:sum"],
        )
        return {move.id: (through, total) for move, through, total in groups}

    def _get_partners_with_pending_payment(self, invoices):
        """Return customers with a validated payment that has no journal entry."""
        payments = self.env["account.payment"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "in_process"),
                ("move_id", "=", False),
                ("payment_type", "=", "inbound"),
                ("partner_type", "=", "customer"),
                ("partner_id", "child_of", invoices.commercial_partner_id.ids),
            ]
        )
        return set(payments.partner_id.commercial_partner_id.ids)

    def _prepare_candidate(
        self, invoice, billed_through, billed_total, pending_partners
    ):
        """Return the screen values for one invoice, or None if nothing is due."""
        self.ensure_one()
        company = self.company_id
        currency = invoice.currency_id
        accrues_after = invoice.invoice_date_due + timedelta(
            days=company.finance_charge_grace_days
        )
        if billed_through:
            days_since = (self.date - billed_through).days
            if days_since < company.finance_charge_interval_days:
                return None
            accrues_after = max(accrues_after, billed_through)
        days = (self.date - accrues_after).days
        if days <= 0:
            return None
        amount = currency.round(
            invoice.amount_residual * company.finance_charge_rate / 100 * days / 365
        )
        notes = []
        if company.finance_charge_min_amount:
            minimum = company.currency_id._convert(
                company.finance_charge_min_amount, currency, company, self.date
            )
            if (
                currency.compare_amounts(amount, minimum) < 0
                and currency.compare_amounts(invoice.amount_residual, minimum) >= 0
            ):
                amount = minimum
                notes.append(self.env._("Minimum applied"))
        if company.finance_charge_cap_percent:
            room = currency.round(
                invoice.amount_total * company.finance_charge_cap_percent / 100
                - billed_total
            )
            if currency.compare_amounts(amount, room) > 0:
                amount = room
                notes.append(self.env._("Cap applied"))
        if currency.compare_amounts(amount, 0.0) <= 0:
            return None
        review_note = ""
        if (
            invoice.payment_state in ("in_payment", "paid")
            or invoice.commercial_partner_id.id in pending_partners
        ):
            review_note = self.env._("Payment in process")
        elif invoice.invoice_has_outstanding:
            review_note = self.env._("Unapplied payment or credit on account")
        return {
            "move_id": invoice.id,
            "partner_id": invoice.commercial_partner_id.id,
            "currency_id": currency.id,
            "date_due": invoice.invoice_date_due,
            "days_past_due": (self.date - invoice.invoice_date_due).days,
            "residual": invoice.amount_residual,
            "date_from": accrues_after + timedelta(days=1),
            "days": days,
            "amount": amount,
            "note": ", ".join(notes),
            "review_note": review_note,
        }

    def _get_candidates(self):
        """Return {invoice id: screen values} for everything chargeable now."""
        self.ensure_one()
        invoices = self._get_candidate_invoices()
        history = self._get_billed_history(invoices)
        pending_partners = self._get_partners_with_pending_payment(invoices)
        candidates = {}
        for invoice in invoices:
            billed_through, billed_total = history.get(invoice.id, (False, 0.0))
            values = self._prepare_candidate(
                invoice, billed_through, billed_total, pending_partners
            )
            if values:
                candidates[invoice.id] = values
        return candidates

    def _load_lines(self):
        self.ensure_one()
        kept = set(self.line_ids.filtered("selected").move_id.ids)
        candidates = self._get_candidates()
        ordered = sorted(
            candidates.values(),
            key=lambda vals: (
                self.env["res.partner"].browse(vals["partner_id"]).name or "",
                vals["date_due"],
                vals["move_id"],
            ),
        )
        self.line_ids = [Command.clear()] + [
            Command.create(
                {
                    **vals,
                    "selected": vals["move_id"] in kept and not vals["review_note"],
                }
            )
            for vals in ordered
        ]

    def action_recalculate(self):
        self.ensure_one()
        self._check_configured()
        self._load_lines()

    def action_select_all(self):
        """Tick every row except those flagged for a person to review."""
        self.ensure_one()
        flagged = self.line_ids.filtered("review_note")
        flagged.selected = False
        (self.line_ids - flagged).selected = True

    def action_select_none(self):
        self.ensure_one()
        self.line_ids.selected = False

    def action_create_charges(self):
        """Create one draft invoice per customer and currency."""
        self.ensure_one()
        self._check_configured()
        selected = self.line_ids.filtered("selected")
        if not selected:
            raise UserError(self.env._("Select at least one invoice to charge."))
        self._check_selection_current(selected)
        grouped = defaultdict(lambda: self.env["account.finance.charge.wizard.line"])
        for line in selected:
            grouped[(line.partner_id, line.currency_id)] |= line
        charges = self.env["account.move"]
        try:
            with self.env.cr.savepoint():
                for (partner, currency), lines in grouped.items():
                    charges |= self._create_charge_invoice(partner, currency, lines)
                self.env["account.finance.charge.line"].flush_model()
        except UniqueViolation as error:
            raise UserError(
                self.env._(
                    "Someone else just billed one of these periods. "
                    "Click Recalculate and review the list again."
                )
            ) from error
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Draft Finance Charges"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", charges.ids)],
            "context": {"default_move_type": "out_invoice"},
            "target": "current",
        }

    def _check_selection_current(self, selected):
        """Refuse to bill figures that changed since the screen was built."""
        candidates = self._get_candidates()
        for line in selected:
            current = candidates.get(line.move_id.id)
            if (
                not current
                or current["date_from"] != line.date_from
                or current["days"] != line.days
                or current["partner_id"] != line.partner_id.id
                or current["currency_id"] != line.currency_id.id
                or line.currency_id.compare_amounts(current["amount"], line.amount)
                or line.currency_id.compare_amounts(current["residual"], line.residual)
                or current["review_note"] != (line.review_note or "")
            ):
                raise UserError(
                    self.env._(
                        "%(invoice)s no longer matches this list because the date, "
                        "balance, payments or billing history changed. "
                        "Click Recalculate and review the amounts again.",
                        invoice=line.move_id.name,
                    )
                )

    def _prepare_charge_label(self, line):
        label = self.env._(
            "Finance charge on %(invoice)s: %(days)s days at %(rate)s%% per year "
            "on %(balance)s (%(start)s to %(end)s)",
            invoice=line.move_id.name,
            days=line.days,
            rate=f"{self.company_id.finance_charge_rate:g}",
            balance=formatLang(self.env, line.residual, currency_obj=line.currency_id),
            start=format_date(self.env, line.date_from),
            end=format_date(self.env, self.date),
        )
        return f"{label} - {line.note}" if line.note else label

    def _prepare_charge_line(self, line):
        company = self.company_id
        values = {
            "name": self._prepare_charge_label(line),
            "quantity": 1,
            "price_unit": line.amount,
            "account_id": company.finance_charge_account_id.id,
            "tax_ids": [Command.clear()],
        }
        if company.finance_charge_product_id:
            values["product_id"] = company.finance_charge_product_id.id
        return values

    def _prepare_charge_invoice(self, partner, currency, lines):
        company = self.company_id
        values = {
            "move_type": "out_invoice",
            "company_id": company.id,
            "partner_id": partner.id,
            "currency_id": currency.id,
            "invoice_date": self.date,
            "invoice_origin": ", ".join(lines.move_id.mapped("name")),
            "is_finance_charge": True,
            "invoice_line_ids": [
                Command.create(self._prepare_charge_line(line)) for line in lines
            ],
        }
        if company.finance_charge_journal_id:
            values["journal_id"] = company.finance_charge_journal_id.id
        return values

    def _create_charge_invoice(self, partner, currency, lines):
        charge = (
            self.env["account.move"]
            .with_context(default_move_type="out_invoice")
            .create(self._prepare_charge_invoice(partner, currency, lines))
        )
        invoice_lines = charge.invoice_line_ids.sorted("id")
        self.env["account.finance.charge.line"].sudo().create(
            [
                {
                    "source_move_id": line.move_id.id,
                    "charge_line_id": invoice_line.id,
                    "date_from": line.date_from,
                    "date_to": self.date,
                    "base_amount": line.residual,
                    "rate": self.company_id.finance_charge_rate,
                    "days": line.days,
                }
                for line, invoice_line in zip(lines, invoice_lines, strict=True)
            ]
        )
        reviewed = lines.filtered("review_note")
        if reviewed:
            charge.message_post(
                body=self.env._(
                    "Charged after review: %(details)s",
                    details="; ".join(
                        f"{line.move_id.name}: {line.review_note}" for line in reviewed
                    ),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return charge


class AccountFinanceChargeWizardLine(models.TransientModel):
    _name = "account.finance.charge.wizard.line"
    _description = "Potential Finance Charge"
    _order = "id"

    wizard_id = fields.Many2one(
        comodel_name="account.finance.charge.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="Charge")
    move_id = fields.Many2one(
        comodel_name="account.move", string="Invoice", required=True, readonly=True
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Customer", required=True, readonly=True
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", required=True, readonly=True
    )
    date_due = fields.Date(string="Due", readonly=True)
    days_past_due = fields.Integer(string="Past Due", readonly=True)
    residual = fields.Monetary(
        string="Balance", currency_field="currency_id", readonly=True
    )
    date_from = fields.Date(string="Charged From", readonly=True)
    days = fields.Integer(readonly=True)
    amount = fields.Monetary(
        string="Finance Charge", currency_field="currency_id", readonly=True
    )
    note = fields.Char(readonly=True)
    review_note = fields.Char(string="Review", readonly=True)

    def action_open_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
