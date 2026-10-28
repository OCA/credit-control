# Copyright 2016-2018 Tecnativa - Carlos Dauden
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
    portal_show_financial_risk = fields.Boolean(
        string="Show credit information in portal",
        config_parameter="account_financial_risk.portal_show_financial_risk",
        help="If enabled, portal users will be able to see their credit information.",
    )
