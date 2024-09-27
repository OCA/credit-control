# Copyright 2016-2018 Tecnativa - Carlos Dauden
# Copyright 2024 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_unpaid_margin = fields.Integer(
        related="company_id.invoice_unpaid_margin", readonly=False
    )
    allow_overrisk_invoice_validation = fields.Boolean(
        related="company_id.allow_overrisk_invoice_validation", readonly=False
    )
    account_move_confirm_risk_template_id = fields.Many2one(
        readonly=False,
        related="company_id.account_move_confirm_risk_template_id",
    )
