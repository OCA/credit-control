# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def risk_exception_msg(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = _("Financial risk exceeded.\n")
        elif partner.risk_invoice_open_limit and (
                (partner.risk_invoice_open + self.amount_total) >
                partner.risk_invoice_open_limit):
            exception_msg = _(
                "This invoice exceeds the open invoices risk.\n")
        # If risk_invoice_draft_include this invoice included in risk_total
        elif not partner.risk_invoice_draft_include and (
                partner.risk_invoice_open_include and
                (partner.risk_total + self.amount_total) >
                partner.credit_limit):
            exception_msg = _(
                "This invoice exceeds the financial risk.\n")
        return exception_msg

    @api.multi
    def action_invoice_open(self):
        if self.env.context.get('bypass_risk', False):
            return super(AccountInvoice, self).action_invoice_open()
        for invoice in self.filtered(lambda x: x.type in (
                'out_invoice', 'out_refund') and x.amount_total_signed > 0.0):
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
