# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    finance_charge_rate = fields.Float(
        related="company_id.finance_charge_rate", readonly=False
    )
    finance_charge_grace_days = fields.Integer(
        related="company_id.finance_charge_grace_days", readonly=False
    )
    finance_charge_interval_days = fields.Integer(
        related="company_id.finance_charge_interval_days", readonly=False
    )
    finance_charge_min_amount = fields.Monetary(
        related="company_id.finance_charge_min_amount",
        currency_field="currency_id",
        readonly=False,
    )
    finance_charge_cap_percent = fields.Float(
        related="company_id.finance_charge_cap_percent", readonly=False
    )
    finance_charge_account_id = fields.Many2one(
        related="company_id.finance_charge_account_id",
        readonly=False,
        check_company=True,
    )
    finance_charge_journal_id = fields.Many2one(
        related="company_id.finance_charge_journal_id",
        readonly=False,
        check_company=True,
    )
    finance_charge_product_id = fields.Many2one(
        related="company_id.finance_charge_product_id",
        readonly=False,
        check_company=True,
    )
