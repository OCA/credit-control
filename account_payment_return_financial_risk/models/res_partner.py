# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    risk_payment_return_include = fields.Boolean(
        string='Include Payments Returns',
        help='Full risk computation.\n'
             'Residual amount of move lines not reconciled with returned '
             'lines related.')
    risk_payment_return_limit = fields.Monetary(
        string='Limit Payments Returns',
        currency_field="risk_currency_id",
        help='Set 0 if it is not locked')
    risk_payment_return = fields.Monetary(
        compute='_compute_risk_account_amount',
        string='Total Payments Returns',
        currency_field="risk_currency_id",
        help='Residual amount of move lines not reconciled with returned '
             'lines related.')

    @api.model
    def _risk_account_groups(self):
        res = super(ResPartner, self)._risk_account_groups()
        res['open']['domain'] += [
            ('partial_reconcile_returned_ids', '=', False),
        ]
        res['unpaid']['domain'] += [
            ('partial_reconcile_returned_ids', '=', False),
        ]
        res['returned'] = {
            'domain': self._get_risk_company_domain() + [
                ('reconciled', '=', False),
                ('user_type_id.type', '=', 'receivable'),
                ('partial_reconcile_returned_ids', '!=', False)
            ],
            'fields': ['partner_id', 'account_id', 'amount_residual'],
            'group_by': ['partner_id', 'account_id']
        }
        return res

    @api.multi
    def _prepare_risk_account_vals(self, groups):
        vals = super(ResPartner, self)._prepare_risk_account_vals(groups)
        vals.update({'risk_payment_return': 0.0})
        for reg in groups['returned']['read_group']:
            if reg['partner_id'][0] != self.id:
                continue  # pragma: no cover
            account = self.env['account.account'].browse(reg['account_id'][0])
            vals['risk_payment_return'] += \
                account.company_id.currency_id._convert(
                    reg['amount_residual'], self.risk_currency_id,
                    account.company_id, fields.Date.context_today(self),
                    round=False)
        return vals

    @api.model
    def _risk_field_list(self):
        res = super(ResPartner, self)._risk_field_list()
        res.append(('risk_payment_return', 'risk_payment_return_limit',
                    'risk_payment_return_include'))
        return res

    def _get_field_risk_model_domain(self, field_name):
        if field_name == 'risk_payment_return':
            domain = self._risk_account_groups()['returned']['domain']
            domain.append(('partner_id', 'in', self.ids))
            return 'account.move.line', domain
        else:
            return super()._get_field_risk_model_domain(field_name)
