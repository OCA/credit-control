# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo.tools import sql

logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    The objective of this hook is to speed up the installation
    of the module on an existing Odoo instance.
    """
    create_risk_partner_id_column(cr)


def create_risk_partner_id_column(cr):
    if not sql.column_exists(cr, "sale_order_line", "risk_partner_id"):
        sql.create_column(cr, "sale_order_line", "risk_partner_id", "int4")

    logger.info("Computing field risk_partner_id on sale.order.line")
    cr.execute(
        """
        UPDATE sale_order_line sol
        SET risk_partner_id = p.commercial_partner_id
        FROM sale_order so LEFT JOIN
            res_partner p ON p.id = so.partner_invoice_id
        WHERE so.id = sol.order_id and
            sol.risk_partner_id IS DISTINCT FROM p.commercial_partner_id;
        """
    )
