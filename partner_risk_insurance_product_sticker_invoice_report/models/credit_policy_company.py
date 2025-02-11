# Copyright 2025 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields, models


class CreditPolicyCompany(models.Model):
    _name = "credit.policy.company"
    _inherit = ["credit.policy.company", "product.sticker.mixin"]

    sticker_ids = fields.One2many(
        inverse_name="credit_policy_company_id",
    )
