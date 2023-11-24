# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _inverse_oca_credit_limit(self):
        """The credit_limit field already exists in account, we use an inverse to define
        the value without altering the standard operation."""
        global_credit_limit = self.env["ir.property"]._get(
            "credit_limit", "res.partner"
        )
        for item in self:
            item.credit_limit = (
                global_credit_limit
                + item.company_credit_limit
                + item.insurance_credit_limit
            )

    credit_limit = fields.Float(tracking=True)
    company_credit_limit = fields.Float(
        "Company's Credit Limit",
        help="Credit limit granted by the company.",
        tracking=True,
        inverse="_inverse_oca_credit_limit",
    )
    insurance_credit_limit = fields.Float(
        "Insurance's Credit Limit",
        help="Credit limit granted by the insurance company.",
        tracking=True,
        inverse="_inverse_oca_credit_limit",
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
