# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_history_ids = fields.One2many(
        comodel_name="res.partner.credit.history",
        inverse_name="partner_id",
        string="Credit History",
        copy=False,
    )


class ResPartnerCreditHistory(models.Model):
    _name = "res.partner.credit.history"
    _description = "Res partner credit history"
    _order = "create_date desc"

    partner_id = fields.Many2one(
        comodel_name="res.partner", required=True, index=True, ondelete="cascade"
    )
    note = fields.Char(string="Reason", required=True)
    previous_amount = fields.Float(string="Previous Amount")
    new_amount = fields.Float(string="New Amount")
