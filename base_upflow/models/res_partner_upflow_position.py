# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class PartnerUpflowPosition(models.Model):
    _name = "res.partner.upflow.position"
    _description = "Upflow Partner Position"

    name = fields.Char(string="Position", required=True, translate=True)
    code = fields.Char(string="Upflow Code", required=True)
