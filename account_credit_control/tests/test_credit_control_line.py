# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCreditControlLine(TransactionCase):
    def test_auto_process(self):
        account = self.env["account.account"].create(
            {
                "code": "400001",
                "name": "Customers (test)",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )

        move = self.env["account.move"].create(
            {
                "name": "Test move",
                "date": datetime.today(),
                "state": "draft",
            }
        )

        move_line = self.env["account.move.line"].create(
            {
                "account_id": account.id,
                "move_id": move.id,
            }
        )

        policy = self.env.ref("account_credit_control.credit_control_3_time")
        policy.write(
            {
                "account_ids": [(6, 0, [account.id])],
                "auto_process_lower_levels": True,
            }
        )
        policy_level_1 = self.env.ref("account_credit_control.3_time_1")
        policy_level_1.delay_days = 1

        policy_level_2 = self.env.ref("account_credit_control.3_time_2")
        policy_level_2.delay_days = 1

        policy_level_3 = self.env.ref("account_credit_control.3_time_3")
        policy_level_3.delay_days = 1

        partner = self.env["res.partner"].create(
            {
                "name": "Partner",
                "property_account_receivable_id": account.id,
            }
        )
        partner.credit_policy_id = policy.id

        ccl_1 = self.env["credit.control.line"].create(
            {
                "date": datetime.today(),
                "date_due": datetime.today(),
                "state": "draft",
                "partner_id": partner.id,
                "account_id": account.id,
                "policy_level_id": policy_level_1.id,
                "channel": "email",
                "amount_due": 100,
                "balance_due": 100,
                "move_line_id": move_line.id,
            }
        )

        self.assertEqual(ccl_1.auto_process, "highest_level")

        ccl_2 = self.env["credit.control.line"].create(
            {
                "date": datetime.today(),
                "date_due": datetime.today(),
                "state": "draft",
                "partner_id": partner.id,
                "account_id": account.id,
                "policy_level_id": policy_level_2.id,
                "channel": "email",
                "amount_due": 100,
                "balance_due": 100,
                "move_line_id": move_line.id,
            }
        )

        self.assertEqual(ccl_1.auto_process, "low_level")
        self.assertEqual(ccl_2.auto_process, "highest_level")
        self.assertTrue(ccl_1 in ccl_2._get_lower_related_lines())
        ccl_1.write({"policy_level_id": policy_level_3.id})

        self.assertEqual(ccl_1.auto_process, "highest_level")
        self.assertEqual(ccl_2.auto_process, "low_level")
        self.assertTrue(ccl_2 in ccl_1._get_lower_related_lines())

        ccl_1.unlink()

        self.assertEqual(ccl_2.auto_process, "highest_level")

        policy.write({"auto_process_lower_levels": False})

        ccl_3 = self.env["credit.control.line"].create(
            {
                "date": datetime.today(),
                "date_due": datetime.today(),
                "state": "sent",
                "partner_id": partner.id,
                "account_id": account.id,
                "policy_level_id": policy_level_2.id,
                "channel": "email",
                "amount_due": 100,
                "balance_due": 100,
                "move_line_id": move_line.id,
            }
        )

        self.assertEqual(ccl_3.auto_process, "no_auto_process")
        self.assertEqual(ccl_3, ccl_3._get_related_lines())
