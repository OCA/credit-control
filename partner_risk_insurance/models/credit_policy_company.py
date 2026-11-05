# Copyright 2024 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CreditPolicyCompany(models.Model):
    _name = "credit.policy.company"
    _description = "Company of Credit Policies"

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    partner_id = fields.Many2one(
        string="Company",
        comodel_name="res.partner",
        ondelete="restrict",
        domain="[('is_company', '=', True)]",
    )
