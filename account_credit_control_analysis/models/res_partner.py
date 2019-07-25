# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    credit_control_analysis_ids = fields.One2many(
        "credit.control.analysis", "partner_id", string="Credit Control Levels"
    )
