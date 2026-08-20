# Copyright 2016-2018 Tecnativa - Sergio Teruel
# Copyright 2024 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CreditPolicyState(models.Model):
    _name = "credit.policy.state"
    _description = "State of credit policies"

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    insure_invoices = fields.Boolean(
        help="If checked, the invoices created when the partner "
        "has this state will be marked as insured",
    )
