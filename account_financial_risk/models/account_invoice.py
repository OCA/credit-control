# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    company_currency_id = fields.Many2one(store=True)
    risk_currency_id = fields.Many2one(
        related="partner_id.risk_currency_id")
    risk_amount_total_currency = fields.Monetary(
        string="Risk Amount Total",
        currency_field="risk_currency_id",
        compute="_compute_risk_amount_total_currency")

    @api.multi
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount',
                 'tax_line_ids.amount_rounding', 'currency_id', 'company_id',
                 'date_invoice', 'type',
                 'partner_id.credit_currency',
                 'partner_id.manual_credit_currency_id',
                 'partner_id.property_account_receivable_id.currency_id',
                 'partner_id.country_id',
                 'company_id.currency_id')
    def _compute_risk_amount_total_currency(self):
        for invoice in self:
            invoice.risk_amount_total_currency = \
                invoice.company_currency_id._convert(
                    invoice.amount_total_company_signed,
                    invoice.risk_currency_id, invoice.company_id,
                    invoice.date_invoice or fields.Date.context_today(self),
                    round=False)

    def risk_exception_msg(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = _("Financial risk exceeded.\n")
        elif partner.risk_invoice_open_limit and (
                (partner.risk_invoice_open + self.risk_amount_total_currency)
                > partner.risk_invoice_open_limit):
            exception_msg = _(
                "This invoice exceeds the open invoices risk.\n")
        # If risk_invoice_draft_include this invoice included in risk_total
        elif not partner.risk_invoice_draft_include and (
                partner.risk_invoice_open_include and
                (partner.risk_total + self.risk_amount_total_currency) >
                partner.credit_limit):
            exception_msg = _(
                "This invoice exceeds the financial risk.\n")
        return exception_msg

    @api.multi
    def action_invoice_open(self):
        if (self.env.context.get('bypass_risk', False) or
                self.company_id.allow_overrisk_invoice_validation):
            return super(AccountInvoice, self).action_invoice_open()
        for invoice in self.filtered(lambda x: x.type == 'out_invoice'):
            exception_msg = invoice.risk_exception_msg()
            if exception_msg:
                return self.env['partner.risk.exceeded.wiz'].create({
                    'exception_msg': exception_msg,
                    'partner_id': invoice.partner_id.commercial_partner_id.id,
                    'origin_reference':
                        '%s,%s' % ('account.invoice', invoice.id),
                    'continue_method': 'action_invoice_open',
                }).action_show()
        return super(AccountInvoice, self).action_invoice_open()
