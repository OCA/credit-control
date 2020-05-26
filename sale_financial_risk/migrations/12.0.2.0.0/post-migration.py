# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

import logging
logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    # Recompute after improvements in rounding, currency, invoice status,
    # w/o stock moves, etc.
    logger.info('Recomputing field risk_amount on sale.order.line')
    lines = env['sale.order.line'].search(
        [('state', '=', 'sale'), ('risk_amount', '!=', 0.0)], order='id')
    lines._compute_risk_amount()

    # Remove old stored computed fields db columns
    openupgrade.drop_columns(env.cr, [
        ('res_partner', 'risk_sale_order'),
    ])
