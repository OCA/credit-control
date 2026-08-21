# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import call, patch

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_credit_control.tests.test_credit_control_run import (
    TestCreditControlRunCase,
)


@tagged("post_install", "-at_install")
class TestCreditControlNotification(TestCreditControlRunCase):
    def test_user_notification_on_run_channel(self):
        """
        Test that running the channel action triggers a bus notification.
        """
        self.invoice.partner_id.email = "test@test.com"
        control_run = self.env["credit.control.run"].create(
            {"date": fields.Date.today(), "policy_ids": [(6, 0, [self.policy.id])]}
        )
        control_run.generate_credit_lines()
        control_lines = self.invoice.credit_control_line_ids
        control_lines.write({"state": "to_be_sent"})

        with patch(
            "odoo.addons.bus.models.bus.BusBus._sendone",
        ) as mock_sendone:
            control_run.run_channel_action()

            # The process now correctly triggers two notifications:
            # 1. From queue_job_batch when the batch is created.
            # 2. From our custom module to confirm the jobs are enqueued.
            # We will now assert that our specific notification is present.

            expected_notification_call = call(
                self.env.user.partner_id,
                "simple_notification",
                {
                    "type": "info",
                    "title": self.env._("Jobs enqueued"),
                    "message": self.env._("The emails will be sent in the background"),
                },
            )

            # Check that our expected call is in the list of actual calls.
            self.assertIn(expected_notification_call, mock_sendone.call_args_list)
