# Copyright 2026 Humanilog GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CreditControlPolicy(models.Model):
    _inherit = "credit.control.policy"

    all_receivable_accounts = fields.Boolean(
        string="Include all receivable accounts",
        help="If set, the policy considers open items on every account of "
        "type Receivable (e.g. individual debtor accounts). New accounts "
        "are included automatically, the account list is ignored.",
    )
    # The account list is only mandatory if the policy is not applied
    # to all receivable accounts (see constraint below).
    account_ids = fields.Many2many(required=False)

    @api.constrains("all_receivable_accounts", "account_ids", "do_nothing")
    def _check_accounts_defined(self):
        for policy in self:
            if (
                not policy.do_nothing
                and not policy.all_receivable_accounts
                and not policy.account_ids
            ):
                raise ValidationError(
                    _(
                        "Policy '%s': select at least one account or enable "
                        "'Include all receivable accounts'."
                    )
                    % policy.name
                )

    def _move_lines_domain(self, credit_control_run):
        domain = super()._move_lines_domain(credit_control_run)
        if not self.all_receivable_accounts:
            return domain
        new_domain = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and leaf[0] == "account_id":
                leaf = ("account_id.internal_type", "=", "receivable")
            new_domain.append(leaf)
        return new_domain

    def check_policy_against_account(self, account):
        """Also accept policies that apply to all receivable accounts."""
        if self.all_receivable_accounts and account.internal_type == "receivable":
            return True
        return super().check_policy_against_account(account)
