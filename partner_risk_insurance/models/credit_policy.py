# Copyright 2016-2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CreditPolicyState(models.Model):
    _name = "credit.policy.state"
    _description = "State of credit policies"

    name = fields.Char(required=True)
