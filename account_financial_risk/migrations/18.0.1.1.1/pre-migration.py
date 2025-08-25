# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import SUPERUSER_ID, api

from odoo.addons.account_financial_risk.hooks import pre_init_hook


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    pre_init_hook(env)
