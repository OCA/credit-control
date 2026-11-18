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
