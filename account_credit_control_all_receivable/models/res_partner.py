# Copyright 2026 Humanilog GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_policy_id = fields.Many2one(
        domain="['|', ('account_ids', 'in', property_account_receivable_id), "
        "('all_receivable_accounts', '=', True)]",
    )
