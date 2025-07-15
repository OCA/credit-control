# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CreditControlPolicy(models.Model):
    _inherit = "credit.control.policy"
    aggregate_levels = fields.Boolean(
        string="Aggregate levels",
        help="When an action is performed on a credit control line generated "
        "by this policy, lower level lines for the same partner and policy "
        "will also be processed.",
    )
