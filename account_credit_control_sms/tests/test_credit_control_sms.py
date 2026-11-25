# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from dateutil import relativedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sms.tests.common import SMSCase


@tagged("post_install", "-at_install")
class TestCreditControlSms(AccountTestInvoicingCommon, SMSCase):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.user.groups_id |= cls.env.ref(
            "account_credit_control.group_account_credit_control_manager"
        )
        cls.account = cls.env["account.account"].create(
            {
                "code": "TEST430001",
                "name": "Clients (test)",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "code": "TEST701001",
                "name": "Sales (test)",
                "account_type": "income",
                "reconcile": True,
            }
        )
        cls.product = cls.env["product.product"].create({"name": "Product test"})
        cls.sms_template = cls.env.ref(
            "account_credit_control_sms.sms_template_credit_control_base"
        )
        cls.policy = cls.env["credit.control.policy"].create(
            {
                "name": "SMS policy",
                "account_ids": [(6, 0, cls.account.ids)],
            }
        )
        cls.level = cls.env["credit.control.policy.level"].create(
            {
                "name": "SMS reminder",
                "policy_id": cls.policy.id,
                "level": 1,
                "computation_mode": "net_days",
                "delay_days": 10,
                "channel": "sms",
                "sms_template_id": cls.sms_template.id,
            }
        )
        cls.partner = cls._create_partner("Partner SMS", mobile="+41791234567")

    @classmethod
    def _create_partner(cls, name, mobile=False):
        partner = cls.env["res.partner"].create(
            {
                "name": name,
                "mobile": mobile,
                "country_id": cls.env.ref("base.ch").id,
                "property_account_receivable_id": cls.account.id,
            }
        )
        partner.credit_policy_id = cls.policy.id
        return partner

    def _create_invoice(self, partner):
        date_invoice = datetime.today() - relativedelta.relativedelta(years=1)
        invoice_form = Form(
            self.env["account.move"].with_context(default_move_type="out_invoice")
        )
        invoice_form.invoice_date = date_invoice
        invoice_form.partner_id = partner
        invoice_form.invoice_payment_term_id = self.env.ref(
            "account.account_payment_term_immediate"
        )
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product
            line_form.quantity = 1
            line_form.price_unit = 500
            line_form.account_id = self.income_account
            line_form.tax_ids.clear()
        invoice = invoice_form.save()
        invoice.action_post()
        return invoice

    def _generate_lines(self):
        control_run = self.env["credit.control.run"].create(
            {"date": fields.Date.today(), "policy_ids": [(6, 0, self.policy.ids)]}
        )
        control_run.generate_credit_lines()
        control_run.set_to_ready_lines()
        return control_run

    def test_sms_level_mail_fields_not_required(self):
        self.assertFalse(self.level.mail_fields_required)
        self.assertFalse(self.level.email_template_id)
        # Switching to a base channel requires the mail fields
        with self.assertRaises(ValidationError):
            self.level.channel = "email"

    def test_run_channel_action_sms_sent(self):
        invoice = self._create_invoice(self.partner)
        control_run = self._generate_lines()
        lines = invoice.credit_control_line_ids
        self.assertEqual(lines.channel, "sms")
        self.assertEqual(lines.state, "to_be_sent")
        with self.mockSMSGateway():
            control_run.run_channel_action()
            self.assertEqual(lines.state, "queued")
            comm = lines.communication_id
            self.assertTrue(comm)
            self.assertEqual(len(self._new_sms), 1)
            self.assertEqual(self._new_sms.partner_id, self.partner)
            self.assertEqual(self._new_sms.state, "outgoing")
            self.assertIn(self.partner.name, self._new_sms.body)
            self.assertEqual(
                self._new_sms.mail_message_id.subtype_id,
                self.env.ref("account_credit_control.mt_request"),
            )
            self._new_sms.send()
        self.assertEqual(lines.state, "sent")

    def test_run_channel_action_sms_error(self):
        invoice = self._create_invoice(self.partner)
        control_run = self._generate_lines()
        lines = invoice.credit_control_line_ids
        with self.mockSMSGateway(sim_error="wrong_number_format"):
            control_run.run_channel_action()
            self._new_sms.send()
        self.assertEqual(lines.state, "sms_error")

    def test_fallback_letter_without_phone(self):
        partner = self._create_partner("Partner no phone")
        invoice = self._create_invoice(partner)
        self._generate_lines()
        self.assertEqual(invoice.credit_control_line_ids.channel, "letter")

    def test_action_send_sms(self):
        invoice = self._create_invoice(self.partner)
        self._generate_lines()
        lines = invoice.credit_control_line_ids
        with self.mockSMSGateway():
            action = lines.action_send_sms()
            comms = self.env["credit.control.communication"].search(
                [("id", "in", action["domain"][0][2])]
            )
            self.assertEqual(comms.credit_control_line_ids, lines)
            self.assertEqual(lines.state, "queued")
            self.assertEqual(
                action["domain"], [("id", "in", lines.communication_id.ids)]
            )
            self._new_sms.send()
        self.assertEqual(lines.state, "sent")
        # Nothing left to send
        with self.assertRaises(UserError):
            lines.action_send_sms()

    def test_server_action(self):
        invoice = self._create_invoice(self.partner)
        self._generate_lines()
        lines = invoice.credit_control_line_ids
        server_action = self.env.ref(
            "account_credit_control_sms.action_credit_control_line_send_sms"
        )
        with self.mockSMSGateway():
            server_action.with_context(
                active_model="credit.control.line", active_ids=lines.ids
            ).run()
        self.assertEqual(lines.state, "queued")
