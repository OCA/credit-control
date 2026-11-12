# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class CreditControlPolicyLevel(models.Model):
    _inherit = "credit.control.policy.level"

    channel = fields.Selection(
        selection_add=[("sms", "SMS")],
        ondelete={"sms": lambda recs: recs.write({"channel": "letter"})},
    )
    sms_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="SMS Template",
        domain=[("model_id.model", "=", "credit.control.communication")],
    )
