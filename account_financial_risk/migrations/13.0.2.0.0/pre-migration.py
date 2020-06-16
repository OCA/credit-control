# Copyright 2020 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.addons.account_financial_risk.hooks import pre_init_hook


def migrate(cr, version):
    pre_init_hook(cr)
