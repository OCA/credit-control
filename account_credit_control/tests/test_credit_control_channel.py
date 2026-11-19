# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .test_credit_control_run import TestCreditControlRunCase


@tagged("post_install", "-at_install")
class TestCreditControlChannel(TestCreditControlRunCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.invoice.partner_id
        cls.partner.email = "partner@example.com"
        cls.env.company.email = "company@example.com"
        # otherwise the report action opens the document layout wizard
        cls.env.company.external_report_layout_id = cls.env.ref(
            "web.external_layout_standard"
        )
        # send the emails directly when account_credit_control_queue_job
        # is installed
        cls.env = cls.env(context=dict(cls.env.context, queue_job__no_delay=True))
        cls.mc_policy = cls.env["credit.control.policy"].create(
            {
                "name": "Multi-channel policy",
                "account_ids": [(6, 0, cls.policy.account_ids.ids)],
            }
        )
        cls.mc_level = cls.env["credit.control.policy.level"].create(
            {
                "name": "Reminder by letter and email",
                "policy_id": cls.mc_policy.id,
                "level": 1,
                "computation_mode": "net_days",
                "delay_days": 0,
                "email_template_id": cls.env.ref(
                    "account_credit_control.email_template_credit_control_base"
                ).id,
                "custom_text": "Please pay",
                "custom_mail_text": "<p>Please pay</p>",
                "use_channel_letter": True,
                "use_channel_email": True,
            }
        )
        cls.partner.credit_policy_id = cls.mc_policy

    def _create_run(self):
        return self.env["credit.control.run"].create(
            {
                "date": fields.Date.today(),
                "policy_ids": [(6, 0, self.mc_policy.ids)],
            }
        )

    def _generate_ready_lines(self):
        control_run = self._create_run()
        control_run.generate_credit_lines()
        control_run.set_to_ready_lines()
        return control_run

    def _get_communication_mails(self, communications):
        return self.env["mail.mail"].search(
            [
                ("model", "=", "credit.control.communication"),
                ("res_id", "in", communications.ids),
            ]
        )

    def test_level_requires_a_channel(self):
        with self.assertRaises(ValidationError):
            self.mc_level.write(
                {"use_channel_letter": False, "use_channel_email": False}
            )

    def test_line_copies_level_channels(self):
        control_run = self._create_run()
        control_run.generate_credit_lines()
        line = self.invoice.credit_control_line_ids
        self.assertEqual(len(line), 1)
        self.assertTrue(line.use_channel_letter)
        self.assertTrue(line.use_channel_email)
        self.assertFalse(line.use_channel_phone)

    def test_line_email_fallback_to_letter(self):
        self.mc_level.use_channel_letter = False
        self.partner.email = False
        control_run = self._create_run()
        control_run.generate_credit_lines()
        line = self.invoice.credit_control_line_ids
        self.assertTrue(line.use_channel_letter)
        self.assertFalse(line.use_channel_email)

    def test_run_channel_action_multi_channel(self):
        """One line on 2 channels: one communication, one letter, one email."""
        control_run = self._generate_ready_lines()
        line = control_run.line_ids
        self.assertEqual(len(line), 1)

        action = control_run.run_channel_action()

        communication = line.communication_id
        self.assertEqual(len(communication), 1)
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(
            action["report_name"],
            "account_credit_control.report_credit_control_summary",
        )
        self.assertEqual(action["context"]["active_ids"], communication.ids)
        mails = self._get_communication_mails(communication)
        self.assertEqual(len(mails), 1)
        self.assertEqual(line.state_channel_letter, "sent")
        self.assertEqual(line.state_channel_email, "queued")
        self.assertEqual(line.state, "queued")
        mails.send()
        self.assertEqual(line.state_channel_email, "sent")
        self.assertEqual(line.state, "sent")

    def test_run_channel_action_email_error_keeps_letter_result(self):
        control_run = self._generate_ready_lines()
        line = control_run.line_ids
        control_run.run_channel_action()
        mails = self._get_communication_mails(line.communication_id)
        mails.write({"email_to": False, "recipient_ids": [(5, 0, 0)]})
        mails.send()
        self.assertEqual(line.state_channel_letter, "sent")
        self.assertEqual(line.state_channel_email, "error")
        self.assertEqual(line.state, "email_error")

    def test_run_channel_action_after_emailer(self):
        """The email sent by the wizard is not sent again by the run,
        and its result is still reported on the line."""
        control_run = self._generate_ready_lines()
        line = control_run.line_ids
        self.env["credit.control.emailer"].create(
            {"line_ids": [(6, 0, line.ids)]}
        ).email_lines()
        communication = line.communication_id
        # the letter is not sent yet
        self.assertEqual(line.state, "to_be_sent")

        control_run.run_channel_action()

        self.assertEqual(line.communication_id, communication)
        mails = self._get_communication_mails(communication)
        self.assertEqual(len(mails), 1)
        self.assertEqual(line.state, "queued")
        mails.send()
        self.assertEqual(line.state, "sent")

    def test_run_channel_action_letter_only(self):
        self.mc_level.use_channel_email = False
        control_run = self._generate_ready_lines()
        action = control_run.run_channel_action()
        line = control_run.line_ids
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(line.state, "sent")
        self.assertFalse(self._get_communication_mails(line.communication_id))

    def test_run_channel_action_phone_only(self):
        """Phone is manual: nothing is sent, the line stays to do."""
        self.mc_level.write(
            {
                "use_channel_letter": False,
                "use_channel_email": False,
                "use_channel_phone": True,
            }
        )
        control_run = self._generate_ready_lines()
        action = control_run.run_channel_action()
        line = control_run.line_ids
        self.assertFalse(action)
        self.assertEqual(line.state, "to_be_sent")
        self.assertFalse(line.communication_id)

    def test_communication_grouped_by_channels(self):
        """Lines of the same partner and level, with different channels
        (changed manually in draft), are not in the same communication."""
        invoice_2 = self.invoice.copy(
            {"invoice_date": self.invoice.invoice_date, "invoice_date_due": False}
        )
        invoice_2.invoice_date_due = self.invoice.invoice_date_due
        invoice_2.action_post()
        control_run = self._create_run()
        control_run.generate_credit_lines()
        lines = control_run.line_ids
        self.assertEqual(len(lines), 2)
        lines[0].use_channel_letter = False
        control_run.set_to_ready_lines()

        control_run.run_channel_action()

        self.assertEqual(len(lines.communication_id), 2)
        self.assertNotEqual(lines[0].communication_id, lines[1].communication_id)
        mails = self._get_communication_mails(lines.communication_id)
        self.assertEqual(len(mails), 2)

    def test_emailer_wizard_sends_email_channel_only(self):
        control_run = self._generate_ready_lines()
        line = control_run.line_ids
        wizard = self.env["credit.control.emailer"].create(
            {"line_ids": [(6, 0, line.ids)]}
        )
        wizard.email_lines()
        self.assertEqual(line.state_channel_email, "queued")
        self.assertFalse(line.state_channel_letter)
        # the letter is not sent yet
        self.assertEqual(line.state, "to_be_sent")
        self.assertEqual(len(self._get_communication_mails(line.communication_id)), 1)
