# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools import sql

import logging
logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    The objective of this hook is to speed up the installation
    of the module on an existing Odoo instance.
    """
    create_commercial_partner_id_column(cr)


def create_commercial_partner_id_column(cr):
    if not sql.column_exists(cr, 'sale_order_line', 'commercial_partner_id'):
        sql.create_column(
            cr, 'sale_order_line', 'commercial_partner_id', 'int4')

    logger.info('Computing field commercial_partner_id on sale.order.line')
    cr.execute(
        """
        UPDATE sale_order_line sol
        SET commercial_partner_id = p.commercial_partner_id
        FROM res_partner p
        WHERE  p.id = sol.order_partner_id and
                sol.commercial_partner_id IS DISTINCT FROM p.commercial_partner_id;
        """
    )
