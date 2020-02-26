# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    risk_sale_order_include = fields.Boolean(
        string='Include Sales Orders', help='Full risk computation')
    risk_sale_order_limit = fields.Monetary(
        string='Limit Sales Orders', help='Set 0 if it is not locked')
    risk_sale_order = fields.Monetary(
        compute='_compute_risk_sale_order', store=True,
        compute_sudo=True,
        string='Total Sales Orders Not Invoiced',
        help='Total not invoiced of sales orders in Sale Order state')

    @api.multi
    @api.depends('sale_order_ids.order_line.amt_invoiced',
                 'child_ids.sale_order_ids.order_line.amt_invoiced')
    def _compute_risk_sale_order(self):
        customers = self.filtered('customer')
        partners = customers | customers.mapped('child_ids')
        orders_group = self.env['sale.order.line'].read_group(
            [('state', '=', 'sale'), ('order_partner_id', 'in', partners.ids)],
            ['order_partner_id', 'price_total',
             'amt_to_invoice', 'amt_invoiced'],
            ['order_partner_id'])
        for partner in customers:
            partner_ids = (partner | partner.child_ids).ids
            # Take in account max of ordered qty and delivered qty
            partner.risk_sale_order = sum(
                max(x['price_total'], x['amt_to_invoice']) - x['amt_invoiced']
                for x in orders_group if x['order_partner_id'][0] in
                partner_ids)

    @api.model
    def _risk_field_list(self):
        res = super(ResPartner, self)._risk_field_list()
        res.append(('risk_sale_order', 'risk_sale_order_limit',
                    'risk_sale_order_include'))
        return res
