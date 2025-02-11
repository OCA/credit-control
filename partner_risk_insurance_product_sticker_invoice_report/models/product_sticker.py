# Copyright 2025 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields, models


class ProductSticker(models.Model):
    _inherit = "product.sticker"

    credit_policy_company_id = fields.Many2one(
        comodel_name="credit.policy.company",
        string="Credit Policy Company",
        help="Display this Sticker only for the selected Credit Policy Company.",
        ondelete="set null",
    )
