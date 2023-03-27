# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    move_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='partner_id',
        string='Account Moves'
    )
    risk_invoice_draft_include = fields.Boolean(
        string='Include Draft Invoices', help='Full risk computation')
    risk_invoice_draft_limit = fields.Monetary(
        string='Limit In Draft Invoices', help='Set 0 if it is not locked')
    risk_invoice_draft = fields.Monetary(
        compute='_compute_risk_invoice',
        string='Total Draft Invoices',
        help='Total amount of invoices in Draft or Pro-forma state')
    risk_invoice_open_include = fields.Boolean(
        string='Include Open Invoices/Principal Balance',
        help='Full risk computation.\n'
             'Residual amount of move lines not reconciled with the same '
             'account that is set as partner receivable and date maturity '
             'not exceeded, considering Due Margin set in account settings.',
    )
    risk_invoice_open_limit = fields.Monetary(
        string='Limit In Open Invoices/Principal Balance',
        help='Set 0 if it is not locked',
    )
    risk_invoice_open = fields.Monetary(
        compute='_compute_risk_account_amount',
        string='Total Open Invoices/Principal Balance',
        help='Residual amount of move lines not reconciled with the same '
             'account that is set as partner receivable and date maturity '
             'not exceeded, considering Due Margin set in account settings.',
    )
    risk_invoice_unpaid_include = fields.Boolean(
        string='Include Unpaid Invoices/Principal Balance',
        help='Full risk computation.\n'
             'Residual amount of move lines not reconciled with the same '
             'account that is set as partner receivable and date maturity '
             'exceeded, considering Due Margin set in account settings.',
    )
    risk_invoice_unpaid_limit = fields.Monetary(
        string='Limit In Unpaid Invoices/Principal Balance',
        help='Set 0 if it is not locked',
    )
    risk_invoice_unpaid = fields.Monetary(
        compute='_compute_risk_account_amount',
        string='Total Unpaid Invoices/Principal Balance',
        help='Residual amount of move lines not reconciled with the same '
             'account that is set as partner receivable and date maturity '
             'exceeded, considering Due Margin set in account settings.',
    )
    risk_account_amount_include = fields.Boolean(
        string='Include Other Account Open Amount',
        help='Full risk computation.\n'
             'Residual amount of move lines not reconciled with distinct '
             'account that is set as partner receivable and date maturity '
             'not exceeded, considering Due Margin set in account settings.',
    )
    risk_account_amount_limit = fields.Monetary(
        string='Limit Other Account Open Amount',
        help='Set 0 if it is not locked',
    )
    risk_account_amount = fields.Monetary(
        compute='_compute_risk_account_amount',
        string='Total Other Account Open Amount',
        help='Residual amount of move lines not reconciled with distinct '
             'account that is set as partner receivable and date maturity '
             'not exceeded, considering Due Margin set in account settings.',
    )
    risk_account_amount_unpaid_include = fields.Boolean(
        string='Include Other Account Unpaid Amount',
        help='Full risk computation.\n'
             'Residual amount of move lines not reconciled with distinct '
             'account that is set as partner receivable and date maturity '
             'exceeded, considering Due Margin set in account settings.',
    )
    risk_account_amount_unpaid_limit = fields.Monetary(
        string='Limit Other Account Unpaid Amount',
        help='Set 0 if it is not locked',
    )
    risk_account_amount_unpaid = fields.Monetary(
        compute='_compute_risk_account_amount',
        string='Total Other Account Unpaid Amount',
        help='Residual amount of move lines not reconciled with distinct '
             'account that is set as partner receivable and date maturity '
             'exceeded, considering Due Margin set in account settings.',
    )
    risk_total = fields.Monetary(
        compute='_compute_risk_exception',
        string='Total Risk', help='Sum of total risk included')
    risk_exception = fields.Boolean(
        compute='_compute_risk_exception',
        search='_search_risk_exception',
        string='Risk Exception',
        help='It Indicate if partner risk exceeded')
    credit_policy = fields.Char()
    risk_allow_edit = fields.Boolean(compute='_compute_risk_allow_edit')
    credit_limit = fields.Float(track_visibility='onchange')

    def _compute_risk_allow_edit(self):
        self.update({'risk_allow_edit': self.env.user.has_group(
            'account.group_account_manager')})

    @api.model
    def _get_risk_company_domain(self):
        return [('company_id', '=', self.env.user.company_id.id)]

    def _get_field_risk_model_domain(self, field_name):
        """ Returns a tuple with model name and domain"""
        if field_name == 'risk_invoice_draft':
            domain = self._get_risk_company_domain() + [
                ('type', 'in', ['out_invoice', 'out_refund']),
                ('state', 'in', ['draft', 'proforma', 'proforma2']),
                ('commercial_partner_id', 'in', self.ids),
            ]
            return 'account.invoice', domain
        risk_account_groups = self._risk_account_groups()
        if field_name.endswith('_unpaid'):
            domain = risk_account_groups['unpaid']['domain']
        else:
            domain = risk_account_groups['open']['domain']
        # Usually this method is called in form view (one record in self)
        account_receivable_id = self[:1].property_account_receivable_id.id
        # Partner receivable account determines if amount is in invoice field
        if field_name.startswith('risk_invoice_'):
            domain.append(('account_id', '=', account_receivable_id))
        else:
            domain.append(('account_id', '!=', account_receivable_id))
        domain.append(('partner_id', 'in', self.ids))
        return 'account.move.line', domain

    @api.depends(
        'invoice_ids', 'invoice_ids.state',
        'invoice_ids.amount_total_company_signed',
        'child_ids.invoice_ids', 'child_ids.invoice_ids.state',
        'child_ids.invoice_ids.amount_total_company_signed')
    def _compute_risk_invoice(self):
        self.update({'risk_invoice_draft': 0.0})
        # When p is NewId object instance bool(p.id) is False
        commercial_partners = self.filtered(lambda p: (
            p.customer and p.id and p == p.commercial_partner_id
        ))
        if not commercial_partners:
            return
        model_name, domain = commercial_partners._get_field_risk_model_domain(
            'risk_invoice_draft')
        total_group = self.env[model_name].sudo().read_group(
            domain=domain,
            fields=['partner_id', 'amount_total_company_signed'],
            groupby=['commercial_partner_id'],
            orderby='id',
        )
        for group in total_group:
            self.browse(group["commercial_partner_id"][0], self._prefetch) \
                .risk_invoice_draft = group["amount_total_company_signed"]

    @api.model
    def _risk_account_groups(self):
        max_date = self._max_risk_date_due()
        company_domain = self._get_risk_company_domain()
        return {
            'open': {
                'domain': company_domain + [
                    ('reconciled', '=', False),
                    ('user_type_id.type', '=', 'receivable'),
                    ('date_maturity', '>=', max_date)
                ],
                'fields': ['partner_id', 'account_id', 'amount_residual'],
                'group_by': ['partner_id', 'account_id']
            },
            'unpaid': {
                'domain': company_domain + [
                    ('reconciled', '=', False),
                    ('user_type_id.type', '=', 'receivable'),
                    ('date_maturity', '<', max_date)
                ],
                'fields': ['partner_id', 'account_id', 'amount_residual'],
                'group_by': ['partner_id', 'account_id']
            }
        }

    @api.multi
    @api.depends('move_line_ids.amount_residual',
                 'move_line_ids.date_maturity',
                 'company_id.invoice_unpaid_margin')
    def _compute_risk_account_amount(self):
        self.update({
            'risk_invoice_open': 0.0,
            'risk_invoice_unpaid': 0.0,
            'risk_account_amount': 0.0,
            'risk_account_amount_unpaid': 0.0,
        })
        AccountMoveLine = self.env['account.move.line'].sudo()
        customers = self.filtered(lambda x: x.customer and not x.parent_id)
        if not customers:
            return  # pragma: no cover
        groups = self._risk_account_groups()
        for key, group in groups.items():
            group['read_group'] = AccountMoveLine.read_group(
                group['domain'] + [('partner_id', 'in', customers.ids)],
                group['fields'],
                group['group_by'],
                orderby='id',
                lazy=False,
            )
        for partner in customers:
            partner.update(partner._prepare_risk_account_vals(groups))

    @api.multi
    def _prepare_risk_account_vals(self, groups):
        vals = {
            'risk_invoice_open': 0.0,
            'risk_invoice_unpaid': 0.0,
            'risk_account_amount': 0.0,
            'risk_account_amount_unpaid': 0.0,
        }
        # Partner receivable account determines if amount is in invoice field
        for reg in groups['open']['read_group']:
            if reg['partner_id'][0] != self.id:
                continue
            if self.property_account_receivable_id.id == reg['account_id'][0]:
                vals['risk_invoice_open'] += reg['amount_residual']
            else:
                vals['risk_account_amount'] += reg['amount_residual']
        for reg in groups['unpaid']['read_group']:
            if reg['partner_id'][0] != self.id:
                continue  # pragma: no cover
            if self.property_account_receivable_id.id == reg['account_id'][0]:
                vals['risk_invoice_unpaid'] += reg['amount_residual']
            else:
                vals['risk_account_amount_unpaid'] += reg['amount_residual']
        return vals

    @api.depends(lambda x: x._get_depends_compute_risk_exception())
    def _compute_risk_exception(self):
        risk_field_list = self._risk_field_list()
        for partner in self:
            if not partner.customer:
                partner.risk_exception = False
                continue
            amount = 0.0
            risk_exception = False
            for risk_field in risk_field_list:
                field_value = getattr(partner, risk_field[0], 0.0)
                max_value = getattr(partner, risk_field[1], 0.0)
                if max_value and field_value > max_value:
                    risk_exception = True
                if getattr(partner, risk_field[2], False):
                    amount += field_value
            partner.risk_total = amount
            if partner.credit_limit and amount > partner.credit_limit:
                risk_exception = True
            partner.risk_exception = risk_exception

    @api.model
    def _search_risk_exception(self, operator, value):
        commercial_partners = self.search([
            ('customer', '=', True),
            '|',
            ('is_company', '=', True),
            ('parent_id', '=', False),
        ], order='id')
        risk_partner_ids = commercial_partners.filtered('risk_exception').ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', risk_partner_ids)]
        else:
            return [('id', 'not in', risk_partner_ids)]

    @api.model
    def _max_risk_date_due(self):
        return fields.Date.to_string(datetime.today().date() - relativedelta(
            days=self.env.user.company_id.invoice_unpaid_margin))

    @api.model
    def _risk_field_list(self):
        return [
            ('risk_invoice_draft', 'risk_invoice_draft_limit',
             'risk_invoice_draft_include'),
            ('risk_invoice_open', 'risk_invoice_open_limit',
             'risk_invoice_open_include'),
            ('risk_invoice_unpaid', 'risk_invoice_unpaid_limit',
             'risk_invoice_unpaid_include'),
            ('risk_account_amount', 'risk_account_amount_limit',
             'risk_account_amount_include'),
            ('risk_account_amount_unpaid', 'risk_account_amount_unpaid_limit',
             'risk_account_amount_unpaid_include'),
        ]

    @api.model
    def _get_depends_compute_risk_exception(self):
        res = []
        for x in self._risk_field_list():
            res.extend((x[0], x[1], x[2], 'child_ids.%s' % x[0],
                        'child_ids.%s' % x[1], 'child_ids.%s' % x[2]))
        res.extend(('credit_limit', 'child_ids.credit_limit'))
        return res

    def open_risk_pivot_info(self):
        open_risk_field = self.env.context.get('open_risk_field')
        if not open_risk_field:
            return  # pragma: no cover
        model_name, domain = self._get_field_risk_model_domain(open_risk_field)
        view_name = 'financial_risk_{}_pivot_view'.format(
            model_name.replace('.', '_'))
        view_id = self.env['ir.model.data'].search(
            [('name', '=', view_name), ('model', '=', 'ir.ui.view')],
            limit=1,
        ).res_id
        return {
            'name': _("Financial risk information"),
            'view_type': 'form',
            'view_mode': 'pivot',
            'res_model': model_name,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'domain': domain,
        }
