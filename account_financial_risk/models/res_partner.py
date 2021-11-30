# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    move_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="partner_id",
        string="Account Moves",
    )
    risk_invoice_draft_include = fields.Boolean(
        string="Include Draft Invoices", help="Full risk computation"
    )
    risk_invoice_draft_limit = fields.Monetary(
        string="Limit In Draft Invoices",
        currency_field="risk_currency_id",
        help="Set 0 if it is not locked",
    )
    risk_invoice_draft = fields.Monetary(
        compute="_compute_risk_account_amount",
        string="Total Draft Invoices",
        currency_field="risk_currency_id",
        help="Total amount of invoices in Draft or Pro-forma state",
    )
    risk_invoice_open_include = fields.Boolean(
        string="Include Open Invoices/Principal Balance",
        help="Full risk computation.\n"
        "Residual amount of move lines not reconciled with the same "
        "account that is set as partner receivable and date maturity "
        "not exceeded, considering Due Margin set in account settings.",
    )
    risk_invoice_open_limit = fields.Monetary(
        string="Limit In Open Invoices/Principal Balance",
        currency_field="risk_currency_id",
        help="Set 0 if it is not locked",
    )
    risk_invoice_open = fields.Monetary(
        compute="_compute_risk_account_amount",
        string="Total Open Invoices/Principal Balance",
        currency_field="risk_currency_id",
        help="Residual amount of move lines not reconciled with the same "
        "account that is set as partner receivable and date maturity "
        "not exceeded, considering Due Margin set in account settings.",
    )
    risk_invoice_unpaid_include = fields.Boolean(
        string="Include Unpaid Invoices/Principal Balance",
        help="Full risk computation.\n"
        "Residual amount of move lines not reconciled with the same "
        "account that is set as partner receivable and date maturity "
        "exceeded, considering Due Margin set in account settings.",
    )
    risk_invoice_unpaid_limit = fields.Monetary(
        string="Limit In Unpaid Invoices/Principal Balance",
        currency_field="risk_currency_id",
        help="Set 0 if it is not locked",
    )
    risk_invoice_unpaid = fields.Monetary(
        compute="_compute_risk_account_amount",
        string="Total Unpaid Invoices/Principal Balance",
        currency_field="risk_currency_id",
        help="Residual amount of move lines not reconciled with the same "
        "account that is set as partner receivable and date maturity "
        "exceeded, considering Due Margin set in account settings.",
    )
    risk_account_amount_include = fields.Boolean(
        string="Include Other Account Open Amount",
        help="Full risk computation.\n"
        "Residual amount of move lines not reconciled with distinct "
        "account that is set as partner receivable and date maturity "
        "not exceeded, considering Due Margin set in account settings.",
    )
    risk_account_amount_limit = fields.Monetary(
        string="Limit Other Account Open Amount",
        currency_field="risk_currency_id",
        help="Set 0 if it is not locked",
    )
    risk_account_amount = fields.Monetary(
        compute="_compute_risk_account_amount",
        string="Total Other Account Open Amount",
        currency_field="risk_currency_id",
        help="Residual amount of move lines not reconciled with distinct "
        "account that is set as partner receivable and date maturity "
        "not exceeded, considering Due Margin set in account settings.",
    )
    risk_account_amount_unpaid_include = fields.Boolean(
        string="Include Other Account Unpaid Amount",
        help="Full risk computation.\n"
        "Residual amount of move lines not reconciled with distinct "
        "account that is set as partner receivable and date maturity "
        "exceeded, considering Due Margin set in account settings.",
    )
    risk_account_amount_unpaid_limit = fields.Monetary(
        string="Limit Other Account Unpaid Amount",
        currency_field="risk_currency_id",
        help="Set 0 if it is not locked",
    )
    risk_account_amount_unpaid = fields.Monetary(
        compute="_compute_risk_account_amount",
        string="Total Other Account Unpaid Amount",
        currency_field="risk_currency_id",
        help="Residual amount of move lines not reconciled with distinct "
        "account that is set as partner receivable and date maturity "
        "exceeded, considering Due Margin set in account settings.",
    )
    risk_total = fields.Monetary(
        compute="_compute_risk_exception",
        string="Total Risk",
        currency_field="risk_currency_id",
        help="Sum of total risk included",
    )
    risk_exception = fields.Boolean(
        compute="_compute_risk_exception",
        search="_search_risk_exception",
        help="It Indicate if partner risk exceeded",
    )
    risk_amount_exceeded = fields.Monetary(
        string="Risk Over Limit",
        currency_field="risk_currency_id",
        compute="_compute_risk_exception",
    )
    credit_policy = fields.Char()
    risk_allow_edit = fields.Boolean(compute="_compute_risk_allow_edit")
    credit_limit = fields.Float(tracking=True)
    credit_currency = fields.Selection(
        selection=[
            ("company", "Company Currency"),
            ("receivable", "Receivable Currency"),
            ("pricelist", "Pricelist Currency"),
            ("manual", "Manual Credit Currency"),
        ],
        default="company",
        tracking=True,
    )
    manual_credit_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Manual Credit Currency",
    )
    risk_currency_id = fields.Many2one(
        comodel_name="res.currency", compute="_compute_credit_currency"
    )

    @api.depends(
        "credit_currency",
        "manual_credit_currency_id",
        "property_account_receivable_id.currency_id",
        "country_id",
        "company_id.currency_id",
    )
    def _compute_credit_currency(self):
        for partner in self:
            if partner.credit_currency == "manual":
                partner.risk_currency_id = (
                    partner.manual_credit_currency_id or partner.currency_id
                )
            elif partner.credit_currency == "receivable":
                partner.risk_currency_id = (
                    partner.property_account_receivable_id.currency_id
                    or partner.currency_id
                )
            elif partner.credit_currency == "pricelist":
                partner.risk_currency_id = (
                    partner.property_product_pricelist.currency_id
                    or partner.currency_id
                )
            else:
                partner.risk_currency_id = partner.currency_id

    @api.onchange("credit_currency")
    def _onchange_credit_currency(self):
        for partner in self:
            if partner.credit_currency == "manual":
                partner.manual_credit_currency_id = partner.risk_currency_id
            else:
                partner.manual_credit_currency_id = False

    @api.onchange("risk_currency_id")
    def _onchange_risk_currency_id(self):
        self._compute_risk_account_amount()

    @api.constrains("credit_currency", "manual_credit_currency_id")
    def _check_credit_currency(self):
        for partner in self:
            if (
                partner.credit_currency == "manual"
                and not partner.manual_credit_currency_id
            ):
                raise ValidationError(_("Choose Manual Credit Currency."))

    def _compute_risk_allow_edit(self):
        self.update(
            {
                "risk_allow_edit": self.env.user.has_group(
                    "account.group_account_manager"
                )
            }
        )

    @api.model
    def _get_risk_company_domain(self):
        return [("company_id", "in", self.env.companies.ids)]

    def _get_field_risk_model_domain(self, field_name):
        """Returns a tuple with model name and domain"""
        risk_account_groups = self._risk_account_groups()
        if field_name == "risk_invoice_draft":
            domain = risk_account_groups["draft"]["domain"]
        elif field_name.endswith("_unpaid"):
            domain = risk_account_groups["unpaid"]["domain"]
        else:
            domain = risk_account_groups["open"]["domain"]
        # Usually this method is called in form view (one record in self)
        account_receivable_id = self[:1].property_account_receivable_id.id
        # Partner receivable account determines if amount is in invoice field
        if field_name != "risk_invoice_draft":
            if field_name.startswith("risk_invoice_"):
                domain.append(("account_id", "=", account_receivable_id))
            else:
                domain.append(("account_id", "!=", account_receivable_id))
        domain.append(("partner_id", "in", self.ids))
        return "account.move.line", domain

    @api.model
    def _risk_account_groups(self):
        max_date = self._max_risk_date_due()
        company_domain = self._get_risk_company_domain()
        return {
            "draft": {
                "domain": company_domain
                + [
                    ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                    ("account_internal_type", "=", "receivable"),
                    ("parent_state", "in", ["draft", "proforma", "proforma2"]),
                ],
                "fields": ["partner_id", "account_id", "amount_residual"],
                "group_by": ["partner_id", "account_id"],
            },
            "open": {
                "domain": company_domain
                + [
                    ("reconciled", "=", False),
                    ("account_internal_type", "=", "receivable"),
                    "|",
                    "&",
                    ("date_maturity", "!=", False),
                    ("date_maturity", ">=", max_date),
                    "&",
                    ("date_maturity", "=", False),
                    ("date", ">=", max_date),
                    ("parent_state", "=", "posted"),
                ],
                "fields": ["partner_id", "account_id", "amount_residual"],
                "group_by": ["partner_id", "account_id"],
            },
            "unpaid": {
                "domain": company_domain
                + [
                    ("reconciled", "=", False),
                    ("account_internal_type", "=", "receivable"),
                    "|",
                    "&",
                    ("date_maturity", "!=", False),
                    ("date_maturity", "<", max_date),
                    "&",
                    ("date_maturity", "=", False),
                    ("date", "<", max_date),
                    ("parent_state", "=", "posted"),
                ],
                "fields": ["partner_id", "account_id", "amount_residual"],
                "group_by": ["partner_id", "account_id"],
            },
        }

    @api.depends(
        "move_line_ids.amount_residual",
        "move_line_ids.date_maturity",
        "company_id.invoice_unpaid_margin",
    )
    def _compute_risk_account_amount(self):
        self.update(
            {
                "risk_invoice_draft": 0.0,
                "risk_invoice_open": 0.0,
                "risk_invoice_unpaid": 0.0,
                "risk_account_amount": 0.0,
                "risk_account_amount_unpaid": 0.0,
            }
        )
        AccountMoveLine = self.env["account.move.line"].sudo()
        customers = self.filtered(
            lambda p: p == p.commercial_partner_id
            or (p._origin and p._origin.id in p.commercial_partner_id.ids)
        )
        if not customers:
            return  # pragma: no cover
        groups = self._risk_account_groups()
        for _key, group in groups.items():
            group["read_group"] = AccountMoveLine.read_group(
                group["domain"] + [("partner_id", "in", customers.ids)],
                group["fields"],
                group["group_by"],
                orderby="id",
                lazy=False,
            )
        for partner in customers:
            partner.update(partner._prepare_risk_account_vals(groups))

    def _prepare_risk_account_vals(self, groups):
        vals = {
            "risk_invoice_draft": 0.0,
            "risk_invoice_open": 0.0,
            "risk_invoice_unpaid": 0.0,
            "risk_account_amount": 0.0,
            "risk_account_amount_unpaid": 0.0,
        }
        # Partner receivable account determines if amount is in invoice field
        for reg in groups["draft"]["read_group"]:
            if reg["partner_id"][0] not in self.ids:
                continue  # pragma: no cover
            account = self.env["account.account"].browse(reg["account_id"][0])
            vals["risk_invoice_draft"] += account.company_id.currency_id._convert(
                reg["amount_residual"],
                self.risk_currency_id,
                account.company_id,
                fields.Date.context_today(self),
                round=False,
            )
        for reg in groups["open"]["read_group"]:
            if reg["partner_id"][0] not in self.ids:
                continue  # pragma: no cover
            account = self.env["account.account"].browse(reg["account_id"][0])
            if self.property_account_receivable_id.id == reg["account_id"][0]:
                vals["risk_invoice_open"] += account.company_id.currency_id._convert(
                    reg["amount_residual"],
                    self.risk_currency_id,
                    account.company_id,
                    fields.Date.context_today(self),
                    round=False,
                )
            else:
                vals["risk_account_amount"] += account.company_id.currency_id._convert(
                    reg["amount_residual"],
                    self.risk_currency_id,
                    account.company_id,
                    fields.Date.context_today(self),
                    round=False,
                )
        for reg in groups["unpaid"]["read_group"]:
            if reg["partner_id"][0] not in self.ids:
                continue  # pragma: no cover
            account = self.env["account.account"].browse(reg["account_id"][0])
            if self.property_account_receivable_id.id == reg["account_id"][0]:
                vals["risk_invoice_unpaid"] += account.company_id.currency_id._convert(
                    reg["amount_residual"],
                    self.risk_currency_id,
                    account.company_id,
                    fields.Date.context_today(self),
                    round=False,
                )
            else:
                vals[
                    "risk_account_amount_unpaid"
                ] += account.company_id.currency_id._convert(
                    reg["amount_residual"],
                    self.risk_currency_id,
                    account.company_id,
                    fields.Date.context_today(self),
                    round=False,
                )
        return vals

    @api.depends(lambda x: x._get_depends_compute_risk_exception())
    def _compute_risk_exception(self):
        risk_field_list = self._risk_field_list()
        for partner in self:
            amount = 0.0
            amount_exceeded = 0.0
            risk_exception = False
            for risk_field in risk_field_list:
                field_value = getattr(partner, risk_field[0], 0.0)
                max_value = getattr(partner, risk_field[1], 0.0)
                include = getattr(partner, risk_field[2], False)
                if include and max_value and field_value > max_value:
                    risk_exception = True
                    amount_exceeded += field_value - max_value
                if include:
                    amount += field_value
            if partner.credit_limit and amount > partner.credit_limit:
                risk_exception = True
                amount_exceeded = amount - partner.credit_limit
            partner.risk_total = amount
            partner.risk_amount_exceeded = amount_exceeded
            partner.risk_exception = risk_exception

    @api.model
    def _search_risk_exception(self, operator, value):
        commercial_partners = self.search(
            [
                ("customer_rank", ">", 0),
                "|",
                ("is_company", "=", True),
                ("parent_id", "=", False),
            ],
            order="id",
        )
        risk_partner_ids = commercial_partners.filtered("risk_exception").ids
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [("id", "in", risk_partner_ids)]
        else:
            return [("id", "not in", risk_partner_ids)]

    @api.model
    def _max_risk_date_due(self):
        return fields.Date.to_string(
            fields.Date.today()
            - relativedelta(days=self.env.company.invoice_unpaid_margin)
        )

    @api.model
    def _risk_field_list(self):
        return [
            (
                "risk_invoice_draft",
                "risk_invoice_draft_limit",
                "risk_invoice_draft_include",
            ),
            (
                "risk_invoice_open",
                "risk_invoice_open_limit",
                "risk_invoice_open_include",
            ),
            (
                "risk_invoice_unpaid",
                "risk_invoice_unpaid_limit",
                "risk_invoice_unpaid_include",
            ),
            (
                "risk_account_amount",
                "risk_account_amount_limit",
                "risk_account_amount_include",
            ),
            (
                "risk_account_amount_unpaid",
                "risk_account_amount_unpaid_limit",
                "risk_account_amount_unpaid_include",
            ),
        ]

    @api.model
    def _get_depends_compute_risk_exception(self):
        res = []
        for x in self._risk_field_list():
            res.extend(
                (
                    x[0],
                    x[1],
                    x[2],
                    "child_ids.%s" % x[0],
                    "child_ids.%s" % x[1],
                    "child_ids.%s" % x[2],
                )
            )
        res.extend(("credit_limit", "child_ids.credit_limit"))
        return res

    def open_risk_pivot_info(self):
        open_risk_field = self.env.context.get("open_risk_field")
        if not open_risk_field:
            return  # pragma: no cover
        model_name, domain = self._get_field_risk_model_domain(open_risk_field)
        view_name = "financial_risk_{}_pivot_view".format(model_name.replace(".", "_"))
        view_id = (
            self.env["ir.model.data"]
            .search(
                [("name", "=", view_name), ("model", "=", "ir.ui.view")],
                limit=1,
            )
            .res_id
        )
        return {
            "name": _("Financial risk information"),
            "view_mode": "pivot",
            "res_model": model_name,
            "view_id": view_id,
            "type": "ir.actions.act_window",
            "context": self.env.context,
            "domain": domain,
        }
