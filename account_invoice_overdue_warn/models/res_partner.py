# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2025 Engenere.one
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    overdue_invoice_count = fields.Integer(
        compute="_compute_overdue_invoice_count_amount",
        string="# of Overdue Invoices",
    )
    # the currency_id field on res.partner =
    # partner.company_id.currency_id or self.env.company.cueency_id
    overdue_invoice_amount = fields.Monetary(
        compute="_compute_overdue_invoice_count_amount",
        string="Overdue Invoices Residual",
        help="Overdue invoice total residual amount in company currency.",
    )

    def _get_overdue_company(self):
        """Return the company to use for overdue computation with multi-company safety."""
        allowed_companies = self.env.companies
        return (
            self.company_id.id
            if self.company_id and self.company_id in allowed_companies
            else self.env.company.id
        )

    def _compute_overdue_invoice_count_amount(self):
        for partner in self:
            company_id = partner._get_overdue_company()
            (
                count,
                amount_company_currency,
            ) = partner._prepare_overdue_invoice_count_amount(company_id)
            partner.overdue_invoice_count = count
            partner.overdue_invoice_amount = amount_company_currency

    def _get_overdue_invoices(self, company_id):
        self.ensure_one()
        if company_id is None:
            company_id = self.env.company.id
        domain = [
            ("move_type", "=", "out_invoice"),
            ("company_id", "=", company_id),
            ("commercial_partner_id", "=", self.commercial_partner_id.id),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
        ]
        return self.env["account.move"].search(domain)

    def _get_overdue_invoices_data(self, company_id):
        today = fields.Date.context_today(self)
        overdue_data = []
        for invoice in self._get_overdue_invoices(company_id):
            overdue_amount = self._compute_invoice_overdue_amount(invoice, today)
            if overdue_amount:
                overdue_data.append((invoice, overdue_amount))
        return overdue_data

    def _prepare_overdue_invoice_count_amount(self, company_id):
        # This method is also called by the module
        # account_invoice_overdue_warn_sale where the company_id arg is used
        self.ensure_one()
        invoices_data = self._get_overdue_invoices_data(company_id)
        overdue_invoice_amount = sum(amount for _, amount in invoices_data)
        count = len(invoices_data)
        return (count, overdue_invoice_amount)

    def _compute_invoice_overdue_amount(self, invoice, today):
        matured_amount = self._compute_invoice_matured_amount(invoice, today)
        if not matured_amount:
            return 0.0
        total_amount = abs(invoice.amount_total_signed)
        residual_amount = abs(invoice.amount_residual_signed)
        paid_amount = total_amount - residual_amount
        overdue_amount = max(matured_amount - paid_amount, 0.0)
        return min(overdue_amount, residual_amount)

    def _compute_invoice_matured_amount(self, invoice, today):
        if invoice.invoice_payment_term_id:
            terms = self._get_invoice_payment_terms(invoice)
            matured_amount = sum(
                abs(term.get("company_amount", 0.0))
                for term in terms
                if term.get("date") and term["date"] < today
            )
        else:
            due_date = invoice.invoice_date_due or invoice.date
            matured_amount = (
                abs(invoice.amount_total_signed)
                if due_date and due_date < today
                else 0.0
            )
        return matured_amount

    def _get_invoice_payment_terms(self, invoice):
        sign = 1 if invoice.is_inbound(include_receipts=True) else -1
        tax_amount_currency = invoice.amount_tax * sign
        tax_amount = invoice.amount_tax_signed
        untaxed_amount_currency = invoice.amount_untaxed * sign
        untaxed_amount = invoice.amount_untaxed_signed
        date_ref = (
            invoice.invoice_date or invoice.date or fields.Date.context_today(invoice)
        )
        return invoice.invoice_payment_term_id._compute_terms(
            date_ref=date_ref,
            currency=invoice.currency_id,
            tax_amount_currency=tax_amount_currency,
            tax_amount=tax_amount,
            untaxed_amount_currency=untaxed_amount_currency,
            untaxed_amount=untaxed_amount,
            company=invoice.company_id,
            cash_rounding=invoice.invoice_cash_rounding_id,
            sign=sign,
        )

    def _prepare_invoice_domain(self, invoice_ids):
        return [("id", "in", invoice_ids)]

    def _prepare_jump_to_overdue_invoices(self, company_id):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        overdue_invoices = [
            invoice.id
            for invoice, _amount in self._get_overdue_invoices_data(company_id)
        ]
        action["domain"] = self._prepare_invoice_domain(overdue_invoices)
        action["context"] = {
            "journal_type": "sale",
            "move_type": "out_invoice",
            "default_move_type": "out_invoice",
            "default_partner_id": self.id,
        }
        return action

    def jump_to_overdue_invoices(self):
        self.ensure_one()
        company_id = self._get_overdue_company()
        action = self._prepare_jump_to_overdue_invoices(company_id)
        return action
