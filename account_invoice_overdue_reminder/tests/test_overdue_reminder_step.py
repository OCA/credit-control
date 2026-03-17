# Copyright 2026 NICO SOLUTIONS - ENGINEERING & IT, Nils Coenen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest.mock import Mock, patch

from odoo import Command, fields
from odoo.exceptions import UserError

from odoo.addons.account_invoice_overdue_reminder.wizard import (
    overdue_reminder_wizard as wizard,
)
from odoo.addons.base.tests.common import BaseCommon


class TestOverdueReminderStep(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Customer",
                "email": "test@example.com",
            }
        )
        cls.user = cls.env.user
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "commercial_partner_id": cls.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_date_due": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test Line",
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    )
                ],
            }
        )
        cls.invoice.action_post()
        cls.step = cls.env["overdue.reminder.step"].create(
            {
                "partner_id": cls.partner.id,
                "commercial_partner_id": cls.partner.id,
                "user_id": cls.user.id,
                "invoice_ids": [Command.set(cls.invoice.ids)],
                "reminder_type": "mail",
                "company_id": cls.company.id,
            }
        )

    def test_compute_counter_and_mail(self):
        self.step._compute_counter_and_mail()
        self.assertGreaterEqual(self.step.counter, 1)
        self.assertTrue(self.step.mail_subject)
        self.assertTrue(self.step.mail_body)

    def test_reminder_type_change(self):
        self.step.reminder_type_change()
        self.assertFalse(self.step.result_id)
        self.assertFalse(self.step.result_notes)
        self.assertFalse(self.step.create_activity)
        self.step.reminder_type = "phone"
        self.step.reminder_type_change()
        self.assertEqual(self.step.reminder_type, "phone")

    def test_skip(self):
        self.step.skip()
        self.assertEqual(self.step.state, "skipped")

    def test_total_residual(self):
        totals = dict(self.step.total_residual())
        self.assertIn(self.invoice.currency_id, totals)
        self.assertEqual(totals[self.invoice.currency_id], self.invoice.amount_residual)

    def test_validate_mail_and_generate_mail_vals(self):
        """
        This test verifies that mail values can be generated correctly from
        an overdue reminder step. External dependencies like template rendering
        are mocked to isolate the test from actual QWeb templates or email sending.
        """
        self.step.mail_subject = "Test Subject"
        self.step.mail_body = "<p>Test Body</p>"
        self.assertTrue(self.step.validate_mail())
        with patch.object(
            type(self.step),
            "_get_overdue_invoice_reminder_template",
            return_value="module.template_xmlid",
        ):
            with patch.object(self.env, "ref") as mock_ref:
                mock_template = mock_ref.return_value
                mock_template._generate_template.return_value = {
                    self.step.id: {"email_from": "from@test.com"}
                }
                vals = self.step.generate_mail_vals()
                self.assertIn("mail_id", vals)

    def test_validate_phone(self):
        self.step.reminder_type = "phone"
        vals = self.step.validate_phone()
        self.assertIn("result_id", vals)
        self.assertIn("result_notes", vals)

    def test_validate_post_raises(self):
        self.step.reminder_type = "post"
        self.step.letter_printed = False
        with self.assertRaises(UserError):
            self.step.validate_post()

    def test_prepare_mail_activity_raises(self):
        self.step.activity_user_id = False
        with self.assertRaises(UserError):
            self.step._prepare_mail_activity()
        self.step.activity_user_id = self.user
        self.step.activity_deadline = False
        with self.assertRaises(UserError):
            self.step._prepare_mail_activity()

    def test_check_warnings_raises(self):
        self.step.company_id = self.env["res.company"].create({"name": "Other"})
        with self.assertRaises(UserError):
            self.step.check_warnings()
        self.step.company_id = self.company

    def test_validate_no_invoices(self):
        self.step.invoice_ids = [(5, 0, 0)]
        with self.assertRaises(UserError):
            self.step.validate()

    def test_get_report_base_filename(self):
        fname = self.step._get_report_base_filename()
        self.assertIn("overdue_letter", fname)

    def test_prepare_overdue_reminder_action(self):
        """
        This test validates that _prepare_overdue_reminder_action sets the
        expected values and triggers a message_post.
        We mock MailThread.message_post to avoid actually sending an email,
        and to allow verifying that the method was called.
        """
        vals = {"reminder_ids": [], "mail_id": 1}
        with patch(
            "odoo.addons.mail.models.mail_thread.MailThread.message_post"
        ) as mock_post:
            self.step._prepare_overdue_reminder_action(vals)
            self.assertIn("user_id", vals)
            self.assertEqual(vals["user_id"], self.step.user_id.id)
            self.assertTrue(mock_post.called)

    def test_print_letter_and_print_invoices(self):
        """
        This test verifies that printing invoices and overdue reminder letters
        triggers the expected report actions.
        - check_warnings is mocked to skip any validation logic.
        - report_action is mocked for both invoices and letters to avoid
          actually generating reports and to allow verifying the call and return value.
        """
        with patch.object(
            wizard.OverdueReminderStep, "check_warnings", return_value=None
        ):
            report_account_invoices = self.env.ref("account.account_invoices")
            with patch.object(
                type(report_account_invoices),
                "report_action",
                return_value="report_action_called",
            ):
                res = self.step.print_invoices()
                self.assertEqual(res, "report_action_called")

            report_letter = self.env.ref(
                "account_invoice_overdue_reminder.overdue_reminder_step_report"
            )
            with patch.object(
                type(report_letter),
                "report_action",
                return_value="letter_report_action",
            ):
                res_letter = self.step.print_letter()
                self.assertEqual(res_letter, "letter_report_action")

    def test_validate_successful_mail_and_validate_method(self):
        """
        This test validates the full mail reminder flow while mocking
        external dependencies such as template rendering, email sending
        and UI navigation actions.
        """
        self.step.mail_subject = "Subject"
        self.step.mail_body = "<p>Body</p>"
        mock_template = Mock()
        mock_template._generate_template.return_value = {
            self.step.id: {"email_from": "from@test.com"}
        }
        with patch.object(
            type(self.step),
            "_get_overdue_invoice_reminder_template",
            return_value="module.template_xmlid",
        ), patch.object(self.env, "ref", return_value=mock_template), patch(
            "odoo.addons.mail.models.mail_mail.MailMail.send", return_value=True
        ), patch.object(
            type(self.step), "_get_attachment_ids", return_value=[]
        ), patch.object(
            type(self.step),
            "goto_list_view",
            return_value={"type": "ir.actions.act_window"},
        ):
            action = self.step.validate()
            self.assertEqual(self.step.state, "done")
            self.assertEqual(action["type"], "ir.actions.act_window")
            actions = self.env["overdue.reminder.action"].search(
                [("partner_id", "=", self.partner.id)], limit=1
            )
            self.assertTrue(actions.mail_id)
            self.assertEqual(
                self.env["mail.mail"].search_count([("subject", "=", "Subject")]), 1
            )
            self.assertEqual(actions.mail_id.subject, "Subject")
            self.assertIn("Body", actions.mail_id.body_html)
