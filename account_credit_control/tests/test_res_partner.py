# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestCreditControlPolicyLevel(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Partner 1"})
        cls.account = cls.env["account.account"].create(
            {
                "code": "400001",
                "name": "Test",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.partner.property_account_receivable_id = cls.account

    def test_check_credit_policy(self):
        """
        Test the constrains on res.partner
        First we try to assign an account and a policy with a wrong policy
        (this policy doesn't contains the account of the partner).
        After that we add the previous account in the policy and
        retry to assign this policy and this account on the partner
        """
        policy = self.env.ref("account_credit_control.credit_control_3_time")
        with self.assertRaises(ValidationError):
            self.partner.write({"credit_policy_id": policy.id})

        policy.write({"account_ids": [(6, 0, [self.account.id])]})
        self.partner.property_account_receivable_id = self.account.id
        self.partner.credit_policy_id = policy.id

    def test_search_credit_policy(self):
        """
        Test the search of the credit policy
        First we try to search a policy without account
        After that we add the account in the policy and
        retry to search the policy
        """
        Policy = self.env["credit.control.policy"].with_context(
            account_receivable_partner_id=self.partner.id
        )
        policy = self.env.ref("account_credit_control.credit_control_3_time")
        self.assertFalse(policy.account_ids)
        domain = [("display_name", "=", "3 time policy")]
        policy_find = Policy.search(domain)
        self.assertFalse(policy_find)
        # Add the account to the policy
        policy.write({"account_ids": [(6, 0, [self.account.id])]})
        policy_find = Policy.search(domain)
        self.assertEqual(len(policy_find), 1)
        self.assertEqual(policy_find, policy)
