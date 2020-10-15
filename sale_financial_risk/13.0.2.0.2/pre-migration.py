# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.addons.sale_financial_risk.hooks import pre_init_hook


def migrate(cr, version):
    pre_init_hook(cr)
