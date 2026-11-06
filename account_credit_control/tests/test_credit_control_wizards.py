# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_credit_control_run import TestCreditControlRunCase


@tagged("post_install", "-at_install")
class TestCreditControlWizards(TestCreditControlRunCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        control_run = cls.env["credit.control.run"].create(
            {"date": "2025-11-13", "policy_ids": [(6, 0, [cls.policy.id])]}
        )
        control_run.generate_credit_lines()
        cls.credit_lines = cls.invoice.credit_control_line_ids

    def test_policy_changer_wizard(self):
        """Test the credit control policy changer wizard."""
        vendor_bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env["res.partner"]
                .create({"name": "Test Vendor"})
                .id,
                "invoice_date": "2025-11-01",
            }
        )
        with self.assertRaises(UserError):
            self.env["credit.control.policy.changer"].with_context(
                active_ids=vendor_bill.ids
            ).create({})

        # Create a new policy to switch to
        new_policy = self.env.ref("account_credit_control.credit_control_2_time")
        new_policy.account_ids = self.invoice.partner_id.property_account_receivable_id
        new_level = self.env.ref("account_credit_control.2_time_1")

        self.assertEqual(len(self.credit_lines), 1)
        original_line = self.credit_lines[0]

        wizard = (
            self.env["credit.control.policy.changer"]
            .with_context(active_ids=self.invoice.ids)
            .create(
                {"new_policy_id": new_policy.id, "new_policy_level_id": new_level.id}
            )
        )

        # Check default move lines
        self.assertEqual(
            wizard.move_line_ids.move_id,
            self.invoice,
            "The wizard should default to the move lines of the active invoice.",
        )

        # Execute the change
        action = wizard.set_new_policy()

        # Verify the old line is overridden
        self.assertTrue(
            original_line.manually_overridden,
            "The original credit line should be marked as manually overridden.",
        )

        # Verify a new line is created with the new policy
        new_credit_line = self.invoice.credit_control_line_ids.filtered(
            lambda r: not r.manually_overridden
        )
        self.assertEqual(len(new_credit_line), 1)
        self.assertEqual(new_credit_line.policy_id, new_policy)
        self.assertEqual(new_credit_line.policy_level_id, new_level)

        # Verify the invoice's policy is updated
        self.assertEqual(self.invoice.credit_policy_id, new_policy)

        # Verify the action returned
        self.assertEqual(action["res_model"], "credit.control.line")
        self.assertIn(new_credit_line.id, action["domain"][0][2])

    def test_marker_wizard(self):
        """Test the credit control marker wizard."""
        self.assertTrue(self.credit_lines)
        self.credit_lines.write({"state": "draft"})

        # Test marking as 'to_be_sent'
        marker_todo = (
            self.env["credit.control.marker"]
            .with_context(
                active_model="credit.control.line", active_ids=self.credit_lines.ids
            )
            .create({"name": "to_be_sent"})
        )
        marker_todo.mark_lines()
        self.assertEqual(
            self.credit_lines.state,
            "to_be_sent",
            "Lines should be marked as 'To Do'.",
        )

        # Test marking as 'ignored'
        marker_ignore = (
            self.env["credit.control.marker"]
            .with_context(
                active_model="credit.control.line", active_ids=self.credit_lines.ids
            )
            .create({"name": "ignored"})
        )
        marker_ignore.mark_lines()
        self.assertEqual(
            self.credit_lines.state,
            "ignored",
            "Lines should be marked as 'Ignored'.",
        )

        # Test UserError when no lines are selected
        with self.assertRaises(UserError, msg="No credit control lines selected."):
            self.env["credit.control.marker"].create({"name": "draft"}).mark_lines()

        # Test UserError when all lines are already 'sent'
        self.credit_lines.write({"state": "sent"})
        with self.assertRaises(
            UserError, msg="All the selected lines are already done."
        ):
            marker_done = (
                self.env["credit.control.marker"]
                .with_context(
                    active_model="credit.control.line", active_ids=self.credit_lines.ids
                )
                .create({"name": "to_be_sent"})
            )
            marker_done.mark_lines()

    def test_printer_wizard(self):
        """Test the credit control printer wizard."""
        self.assertTrue(self.credit_lines)
        self.credit_lines.write({"state": "to_be_sent", "channel": "letter"})

        # Test printing and marking as sent
        printer_wizard = (
            self.env["credit.control.printer"]
            .with_context(
                active_model="credit.control.line", active_ids=self.credit_lines.ids
            )
            .create({"mark_as_sent": True})
        )
        action = printer_wizard.print_lines()

        self.assertEqual(
            self.credit_lines.state, "sent", "Lines should be marked as 'Done'."
        )
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(
            action["report_name"],
            "account_credit_control.report_credit_control_summary",
        )

        # Test printing without marking as sent
        self.credit_lines.write({"state": "to_be_sent"})
        printer_wizard_no_mark = (
            self.env["credit.control.printer"]
            .with_context(
                active_model="credit.control.line", active_ids=self.credit_lines.ids
            )
            .create({"mark_as_sent": False})
        )
        printer_wizard_no_mark.print_lines()
        self.assertEqual(
            self.credit_lines.state,
            "to_be_sent",
            "Lines state should not have changed.",
        )

    def test_emailer_wizard_errors(self):
        """Test error cases for the emailer wizard."""
        with self.assertRaises(UserError, msg="No credit control lines selected."):
            self.env["credit.control.emailer"].create({}).email_lines()
