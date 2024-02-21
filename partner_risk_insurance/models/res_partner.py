# Copyright 2016-2018 Tecnativa - Sergio Teruel
# Copyright 2024 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_limit = fields.Float(tracking=True)
    company_credit_limit = fields.Float(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute="_compute_company_credit_limit",
        help=(
            "Calculated as the Total minus Insured credit limits, reflecting "
            "the credit limit the company is willing to offer to the client, "
            "excluding the insured portion."
        ),
    )
    insurance_credit_limit = fields.Float(
        "Insured credit limit",
        groups="account.group_account_invoice,account.group_account_readonly",
        help=(
            "The portion of credit that is covered by insurance, set by the user. "
            "It represents the amount of credit that an insurance policy guarantees."
        ),
        tracking=True,
    )
    risk_insurance_coverage_percent = fields.Float(
        "Insurance coverage (%)",
        groups="account.group_account_invoice,account.group_account_readonly",
        help="Percentage of the credit that is covered by the insurance.",
    )
    risk_insurance_requested = fields.Boolean(
        "Insurance Requested",
        help="Mark this field if an insurance was "
        "requested for the credit of this partner.",
    )
    risk_insurance_grant_date = fields.Date(
        "Insurance Grant Date",
        help="Date when the insurance was granted by the insurance company.",
    )
    risk_insurance_code = fields.Char(
        "Insurance Code",
        help="Code assigned to this partner by the risk insurance company.",
    )
    risk_insurance_code_2 = fields.Char(
        "Insurance Code 2",
        help="Secondary code assigned to this "
        "partner by the risk insurance "
        "company.",
    )
    credit_policy_state_id = fields.Many2one(
        string="Policy State",
        comodel_name="credit.policy.state",
        ondelete="restrict",
    )
    credit_policy_insure_invoices = fields.Boolean(
        string="Insure Invoices",
        related="credit_policy_state_id.insure_invoices",
        store=False,
    )
    credit_policy_company_id = fields.Many2one(
        string="Credit Policy Company",
        comodel_name="credit.policy.company",
        ondelete="restrict",
    )

    @api.depends("credit_limit", "insurance_credit_limit")
    def _compute_company_credit_limit(self):
        for partner in self:
            partner.company_credit_limit = max(
                0, (partner.credit_limit - partner.insurance_credit_limit)
            )

    @api.onchange("insurance_credit_limit")
    def _onchange_insurance_credit_limit_update_total_limit(self):
        """Set the total limit to the insurance limit if it is greater."""
        if self.insurance_credit_limit > self.credit_limit:
            self.credit_limit = self.insurance_credit_limit

    @api.onchange("use_partner_credit_limit")
    def _onchange_use_partner_credit_limit(self):
        """Run inverse before saving the form.

        This reflects live the intended usage in UI.
        """
        self._inverse_use_partner_credit_limit()
