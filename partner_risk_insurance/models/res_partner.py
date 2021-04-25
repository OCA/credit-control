# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends("company_credit_limit", "insurance_credit_limit")
    def _compute_credit_limit(self):
        for partner in self:
            partner.credit_limit = (
                partner.company_credit_limit + partner.insurance_credit_limit
            )

    credit_limit = fields.Float(
        "Credit Limit", store=True, compute="_compute_credit_limit"
    )
    company_credit_limit = fields.Float(
        "Company's Credit Limit",
        help="Credit limit granted by the company.",
        tracking=True,
    )
    insurance_credit_limit = fields.Float(
        "Insurance's Credit Limit",
        help="Credit limit granted by the insurance company.",
        tracking=True,
    )
    risk_insurance_coverage_percent = fields.Float(
        "Insurance's Credit Coverage",
        help="Percentage of the credit covered " "by the insurance.",
    )
    risk_insurance_requested = fields.Boolean(
        "Insurance Requested",
        help="Mark this field if an insurance was "
        "requested for the credit of this partner.",
    )
    risk_insurance_grant_date = fields.Date(
        "Insurance Grant Date",
        help="Date when the insurance was " "granted by the insurance company.",
    )
    risk_insurance_code = fields.Char(
        "Insurance Code",
        help="Code assigned to this partner by " "the risk insurance company.",
    )
    risk_insurance_code_2 = fields.Char(
        "Insurance Code 2",
        help="Secondary code assigned to this "
        "partner by the risk insurance "
        "company.",
    )
    credit_policy_state_id = fields.Many2one(
        string="Policy State", comodel_name="credit.policy.state", ondelete="restrict"
    )
