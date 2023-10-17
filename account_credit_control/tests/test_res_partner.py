# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("post_install", "-at_install")
class TestCreditControlPolicyLevel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))

    def test_check_credit_policy(self):
        """
        Test the constrains on res.partner
        First we try to assign an account and a policy with a wrong policy
        (this policy doesn't contains the account of the partner).
        After that we add the previous account in the policy and
        retry to assign this policy and this account on the partner
        """
        policy = self.env.ref("account_credit_control.credit_control_3_time")
        partner = self.env["res.partner"].create({"name": "Partner 1"})
        account = self.env["account.account"].create(
            {
                "code": "400001",
                "name": "Test",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        partner.property_account_receivable_id = account

        with self.assertRaises(ValidationError):
            partner.write({"credit_policy_id": policy.id})

        policy.write({"account_ids": [(6, 0, [account.id])]})
        partner.property_account_receivable_id = account.id
        partner.credit_policy_id = policy.id
