# Copyright 2024 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    include_risk_sale_order_done = fields.Boolean(
        "Include locked sale orders into risk calculation",
        config_parameter="sale_financial_risk.include_risk_sale_order_done",
    )
    sale_order_confirm_risk_template_id = fields.Many2one(
        readonly=False,
        related="company_id.sale_order_confirm_risk_template_id",
    )
