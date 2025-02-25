# Copyright 2025 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    allow_overrisk_sale_confirmation = fields.Boolean(
        string="Allow sale order confirmation over the risk",
        help="If is set always allow the confirmation of sale orders.",
    )
