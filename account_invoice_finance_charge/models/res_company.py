# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    finance_charge_rate = fields.Float(
        string="Finance Charge Annual Rate (%)",
        digits=(16, 4),
        help="Simple annual rate, charged by the day on the unpaid balance. "
        "Check the limits that apply where your customers are located.",
    )
    finance_charge_grace_days = fields.Integer(
        help="Days after the due date before interest starts to accrue.",
    )
    finance_charge_interval_days = fields.Integer(
        string="Days Between Finance Charges",
        default=30,
        help="An invoice that was already charged is not offered again "
        "until this many days have passed.",
    )
    finance_charge_min_amount = fields.Monetary(
        string="Minimum Finance Charge",
        currency_field="currency_id",
        help="A calculated charge below this amount is raised to it. "
        "Zero means no minimum.",
    )
    finance_charge_cap_percent = fields.Float(
        string="Finance Charge Cap (%)",
        digits=(16, 4),
        help="Maximum total finance charges on one invoice, as a percentage "
        "of the invoice total. Zero means no cap.",
    )
    finance_charge_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Finance Charge Income Account",
    )
    finance_charge_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Finance Charge Journal",
        help="Leave empty to use the default customer invoice journal.",
    )
    finance_charge_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Finance Charge Product",
        help="Optional. Set one if a tax engine needs a product on every "
        "invoice line. Finance charge lines are still created without tax.",
    )

    @api.constrains(
        "finance_charge_rate",
        "finance_charge_grace_days",
        "finance_charge_interval_days",
        "finance_charge_min_amount",
        "finance_charge_cap_percent",
    )
    def _check_finance_charge_settings(self):
        for company in self:
            if (
                company.finance_charge_rate < 0
                or company.finance_charge_grace_days < 0
                or company.finance_charge_interval_days < 0
                or company.finance_charge_min_amount < 0
                or company.finance_charge_cap_percent < 0
            ):
                raise ValidationError(
                    self.env._("Finance charge settings cannot be negative.")
                )
            if (
                company.finance_charge_interval_days < 1
                or company.finance_charge_interval_days > 3650
                or company.finance_charge_grace_days > 3650
            ):
                raise ValidationError(
                    self.env._(
                        "Days between finance charges must be 1 to 3650, "
                        "and grace days cannot be more than 3650."
                    )
                )
