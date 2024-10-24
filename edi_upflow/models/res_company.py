# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    upflow_backend_id = fields.Many2one(
        "edi.backend",
        string="Upflow backend",
        domain="[('backend_type_id.code', '=', 'upflow')]",
    )
