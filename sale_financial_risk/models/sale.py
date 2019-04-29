# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        if not self.env.context.get('bypass_risk', False):
            partner = self.partner_id.commercial_partner_id
            exception_msg = ""
            if partner.risk_exception:
                exception_msg = _("Financial risk exceeded.\n")
            elif partner.risk_sale_order_limit and (
                    (partner.risk_sale_order + self.amount_total) >
                    partner.risk_sale_order_limit):
                exception_msg = _(
                    "This sale order exceeds the sales orders risk.\n")
            elif partner.risk_sale_order_include and (
                    (partner.risk_total + self.amount_total) >
                    partner.credit_limit):
                exception_msg = _(
                    "This sale order exceeds the financial risk.\n")
            if exception_msg:
                return self.env['partner.risk.exceeded.wiz'].create({
                    'exception_msg': exception_msg,
                    'partner_id': partner.id,
                    'origin_reference': '%s,%s' % ('sale.order', self.id),
                    'continue_method': 'action_confirm',
                }).action_show()
        return super(SaleOrder, self).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    amt_to_invoice = fields.Monetary(
        string="Amount To Invoice",
        compute='_compute_amount_to_invoice',
        compute_sudo=True,
        store=True
    )

    @api.depends('state',
                 'price_reduce_taxinc',
                 'qty_delivered',
                 'invoice_lines',
                 'invoice_lines.price_total',
                 'invoice_lines.invoice_id',
                 'invoice_lines.invoice_id.state',
                 'invoice_lines.invoice_id.type')
    def _compute_amount_to_invoice(self):
        """ Compute the taxed amount already invoiced from the sale order
            line. This amount is computed as
                SUM(inv_line.price_total) - SUM(ref_line.price_total)
            where
                `inv_line` is a customer invoice line linked to the SO line
                `ref_line` is a customer credit note (refund) line linked to
                    the SO line

            Then, compute amount to invoice as:
                total_sale_line - amount_invoiced
            where
                `amount_invoiced` is taxed amount previously explained
        """
        for line in self.filtered(lambda l: l.state == 'sale'):
            invoice_lines = line.invoice_lines.filtered(
                lambda l: l.invoice_id.state in {'open', 'in_payment', 'paid'})
            amount_invoiced = 0.0
            for inv_line in invoice_lines:
                inv_date = (inv_line.invoice_id.date_invoice
                            or fields.Date.today())
                amount = inv_line.currency_id._convert(
                    inv_line.price_total, line.company_id.currency_id,
                    line.company_id, inv_date)
                if inv_line.invoice_id.type == 'out_invoice':
                    amount_invoiced += amount
                elif inv_line.invoice_id.type == 'out_refund':
                    amount_invoiced -= amount
            if line.product_id.invoice_policy == 'delivery':
                total_sale_line = line.price_reduce_taxinc * line.qty_delivered
            else:
                total_sale_line = line.price_total
            total_sale_line = line.currency_id._convert(
                total_sale_line, line.company_id.currency_id,
                line.company_id, fields.Date.today())
            line.amt_to_invoice = total_sale_line - amount_invoiced
