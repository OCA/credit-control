# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# from odoo.tools import sql
from odoo.addons.sale_financial_risk.hooks import \
    create_commercial_partner_id_column


def migrate(cr, version):
    if not version:
        return
    create_commercial_partner_id_column(cr)
