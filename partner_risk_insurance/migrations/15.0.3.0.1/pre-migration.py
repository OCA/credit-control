# Copyright 2024 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# pylint: disable=W7950
from odoo.addons.partner_risk_insurance.hooks import pre_init_hook


def migrate(cr, version):
    """Create account move columns to performance upgrade on large databases"""
    pre_init_hook(cr)
