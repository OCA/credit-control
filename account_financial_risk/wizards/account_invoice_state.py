# Copyright 2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountInvoiceConfirm(models.TransientModel):

    _inherit = 'account.invoice.confirm'

    @api.multi
    def _default_info_risk(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        info = ""
        for invoice in self.env['account.invoice'].browse(active_ids):
            exception_msg = invoice.risk_exception_msg()
            if exception_msg:
                info += '%s %s\n' % (invoice.partner_id.name, exception_msg)
        return info

    info_risk = fields.Text(default=_default_info_risk, readonly=True)
