# Copyright 2024 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, exceptions, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    insured_with_credit_policy = fields.Boolean(
        string="Insured by a Credit Policy",
        compute="_compute_insured_with_credit_policy",
        store=True,
        readonly=False,
        help="Indicates if the invoice is insured by a credit policy.",
    )
    credit_policy_company_id = fields.Many2one(
        string="Insurance Company",
        comodel_name="credit.policy.company",
        compute="_compute_credit_policy",
        store=True,
        readonly=True,
        ondelete="restrict",
        help="The insurance company that insures the invoices of the partner.",
    )
    credit_policy_state_id = fields.Many2one(
        string="Insurance Policy",
        comodel_name="credit.policy.state",
        compute="_compute_credit_policy",
        store=True,
        readonly=True,
        ondelete="restrict",
        domain="[('insure_invoices', '=', True)]",
        help="The insurance policy that insures the invoices of the partner.",
    )

    @api.depends("partner_id", "move_type")
    def _compute_insured_with_credit_policy(self):
        """Compute the insured_with_credit_policy field when partner changes."""
        self.update(
            {
                "insured_with_credit_policy": False,
                "credit_policy_state_id": False,
                "credit_policy_company_id": False,
            }
        )
        for record in self:
            if record.move_type != "out_invoice":
                continue
            partner = record.partner_id.commercial_partner_id
            if partner.credit_policy_insure_invoices:
                record.insured_with_credit_policy = True
                record.credit_policy_company_id = partner.credit_policy_company_id
                record.credit_policy_state_id = partner.credit_policy_state_id

    @api.depends("insured_with_credit_policy")
    def _compute_credit_policy(self):
        """Compute if the invoice is insured by a credit policy if
        `credit_policy_insure_invoices` field changes."""
        self.update(
            {
                "credit_policy_state_id": False,
                "credit_policy_company_id": False,
            }
        )
        for record in self:
            if record.move_type != "out_invoice":
                continue
            if record.insured_with_credit_policy:
                partner = record.partner_id.commercial_partner_id
                record.credit_policy_company_id = partner.credit_policy_company_id
                record.credit_policy_state_id = partner.credit_policy_state_id

    @api.onchange("insured_with_credit_policy")
    def onchange_insured_with_credit_policy(self):
        """Check if the partner has a credit policy to insure
        invoices and raise an error if not ."""
        partner = self.partner_id.commercial_partner_id
        if not partner or not self.insured_with_credit_policy:
            return
        if not partner.credit_policy_insure_invoices:
            raise exceptions.UserError(
                _(
                    "The partner %s has no credit policy to insure invoices.",
                    partner.display_name,
                )
            )
