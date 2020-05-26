# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tools import sql
from odoo.addons.sale_financial_risk.hooks import \
    create_commercial_partner_id_column


def migrate(cr, version):
    if not version:
        return
    create_commercial_partner_id_column(cr)
    rename_amt_to_invoice(cr)
    compute_zero_risk_amount(cr)


def rename_amt_to_invoice(cr):
    if (not sql.column_exists(cr, 'sale_order_line', 'risk_amount') and
            sql.column_exists(cr, 'sale_order_line', 'amt_to_invoice')):
        sql.rename_column(
            cr, 'sale_order_line', 'amt_to_invoice', 'risk_amount')


def compute_zero_risk_amount(cr):
    # Set 0 in lines without risk
    cr.execute(
        """
        UPDATE sale_order_line sol
        SET risk_amount = 0.0
        FROM product_product p LEFT JOIN
            product_template pt ON pt.id = p.product_tmpl_id
        WHERE (p.id = sol.product_id) AND (risk_amount <> 0.0) AND
            ((sol.state <> 'sale') OR
             (pt.invoice_policy = 'delivery' AND
              GREATEST(sol.product_uom_qty, sol.qty_delivered) <=
                sol.qty_invoiced) OR
             (pt.invoice_policy <> 'delivery' AND
              sol.product_uom_qty <= sol.qty_invoiced));
        """
    )
