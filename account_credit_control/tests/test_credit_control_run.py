# Copyright 2017 Okia SPRL (https://okia.be)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
from datetime import datetime
from dateutil import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCreditControlRun(TransactionCase):

    def setUp(self):
        super(TestCreditControlRun, self).setUp()

        journal = self.env['account.invoice']._default_journal()

        account_type_rec = self.env.ref('account.data_account_type_receivable')
        self.account = self.env['account.account'].create({
            'code': '400001',
            'name': 'Clients (test)',
            'user_type_id': account_type_rec.id,
            'reconcile': True,
        })

        tag_operation = self.env.ref('account.account_tag_operating')
        account_type_inc = self.env.ref('account.data_account_type_revenue')
        analytic_account = self.env['account.account'].create({
            'code': '701001',
            'name': 'Ventes en Belgique (test)',
            'user_type_id': account_type_inc.id,
            'reconcile': True,
            'tag_ids': [(6, 0, [tag_operation.id])],
        })
        payment_term = self.env.ref('account.account_payment_term_immediate')

        product = self.env['product.product'].create({
            'name': 'Product test',
        })

        self.policy = \
            self.env.ref('account_credit_control.credit_control_3_time')
        self.policy.write({
            'account_ids': [(6, 0, [self.account.id])],
        })

        # There is a bug with Odoo ...
        # The field "credit_policy_id" is considered as an "old field" and
        # the field property_account_receivable_id like a "new field"
        # The ORM will create the record with old field
        # and update the record with new fields.
        # However constrains are applied after the first creation.
        partner = self.env['res.partner'].create({
            'name': 'Partner',
            'property_account_receivable_id': self.account.id,
        })
        partner.credit_policy_id = self.policy.id

        date_invoice = datetime.today() - relativedelta.relativedelta(years=1)
        self.invoice = self.env['account.invoice'].create({
            'partner_id': partner.id,
            'journal_id': journal.id,
            'type': 'out_invoice',
            'payment_term_id': payment_term.id,
            'date_invoice': fields.Datetime.to_string(date_invoice),
            'date_due': fields.Datetime.to_string(date_invoice),
        })

        self.invoice.invoice_line_ids.create({
            'invoice_id': self.invoice.id,
            'product_id': product.id,
            'name': product.name,
            'account_id': analytic_account.id,
            'quantity': 5,
            'price_unit': 100,
        })

        # Validate the invoice
        self.invoice.action_invoice_open()

    def test_check_run_date(self):
        """
        Create a control run older than the last control run
        """
        control_run = self.env['credit.control.run'].create({
            'date': fields.Date.today(),
            'policy_ids': [(6, 0, [self.policy.id])],
        })

        with self.assertRaises(UserError):
            today = datetime.today()
            previous_date = today - relativedelta.relativedelta(days=15)
            previous_date_str = fields.Date.to_string(previous_date)
            control_run._check_run_date(previous_date_str)

    def test_generate_credit_lines(self):
        """
        Test the method generate_credit_lines
        """
        control_run = self.env['credit.control.run'].create({
            'date': fields.Date.today(),
            'policy_ids': [(6, 0, [self.policy.id])],
        })

        control_run.with_context(lang='en_US').generate_credit_lines()

        self.assertEqual(len(self.invoice.credit_control_line_ids), 1)
        self.assertEqual(control_run.state, 'done')

        report_regex = \
            r'<p>Policy "<b>%s</b>" has generated <b>' \
            r'\d+ Credit Control Lines.</b><br></p>' % self.policy.name
        regex_result = re.match(report_regex, control_run.report)
        self.assertIsNotNone(regex_result)

    def test_generate_credit_lines_negative_levels(self):
        """
        Test the method generate_credit_lines with policy with
        negative levels.
        """
        preventive_polity = self.env['credit.control.policy'].create({
            'name': 'Preventive policy',
            'level_ids': [
                (0, 0, {
                    'name': '10 days before',
                    'level': 1,
                    'channel': 'email',
                    'delay_days': -10,
                    'computation_mode': 'net_days',
                    'email_template_id': self.env.ref(
                        "account_credit_control."
                        "email_template_credit_control_base").id,
                    'custom_mail_text': '10 days or less until due date.',
                    'custom_text': '10 days or less until due date.',
                }),
            ],
            'account_ids': [(6, 0, [self.account.id])],
        })
        self.invoice.partner_id.credit_policy_id = preventive_polity.id
        # Create a 'Credit Control Run' and compute credit control lines
        run_date = self.invoice.date_due - relativedelta.relativedelta(days=8)
        control_run = self.env['credit.control.run'].create({
            'date': run_date,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 1)
        self.assertEqual(control_run.state, 'done')
        report_regex = \
            r'<p>Policy "<b>%s</b>" has generated <b>' \
            r'\d+ Credit Control Lines.</b><br></p>' % preventive_polity.name
        regex_result = re.match(report_regex, control_run.report)
        self.assertIsNotNone(regex_result)

    def test_multi_credit_control_run(self):
        """
        Generate several control run
        """

        six_months = datetime.today() - relativedelta.relativedelta(months=6)
        six_months_str = fields.Date.to_string(six_months)
        three_months = datetime.today() - relativedelta.relativedelta(months=2)
        three_months_str = fields.Date.to_string(three_months)

        # First run
        first_control_run = self.env['credit.control.run'].create({
            'date': six_months_str,
            'policy_ids': [(6, 0, [self.policy.id])],
        })
        first_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 1)

        # Second run
        second_control_run = self.env['credit.control.run'].create({
            'date': three_months_str,
            'policy_ids': [(6, 0, [self.policy.id])],
        })
        second_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 2)

        # Last run
        last_control_run = self.env['credit.control.run'].create({
            'date': fields.Date.today(),
            'policy_ids': [(6, 0, [self.policy.id])],
        })
        last_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 3)

    def test_multi_credit_control_run_negative_levels(self):
        """
        Generate several control run with negative levels
        """
        preventive_polity = self.env['credit.control.policy'].create({
            'name': 'Preventive policy',
            'level_ids': [
                (0, 0, {
                    'name': '30 days before',
                    'level': 1,
                    'channel': 'email',
                    'delay_days': -30,
                    'computation_mode': 'net_days',
                    'email_template_id': self.env.ref(
                        "account_credit_control."
                        "email_template_credit_control_base").id,
                    'custom_mail_text': '30 days or less until due date.',
                    'custom_text': '30 days or less until due date.',
                }),
                (0, 0, {
                    'name': '10 days before',
                    'level': 2,
                    'channel': 'email',
                    'delay_days': -10,
                    'computation_mode': 'net_days',
                    'email_template_id': self.env.ref(
                        "account_credit_control."
                        "email_template_credit_control_base").id,
                    'custom_mail_text': '10 days or less until due date.',
                    'custom_text': '10 days or less until due date.',
                }),
            ],
            'account_ids': [(6, 0, [self.account.id])],
        })
        self.invoice.partner_id.credit_policy_id = preventive_polity.id
        # Determine dates
        date_due = self.invoice.date_due
        first = date_due - relativedelta.relativedelta(days=32)
        second = date_due - relativedelta.relativedelta(days=28)
        third = date_due - relativedelta.relativedelta(days=8)
        # First run
        first_control_run = self.env['credit.control.run'].create({
            'date': first,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        first_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 0)
        # Second run
        second_control_run = self.env['credit.control.run'].create({
            'date': second,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        second_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 1)
        second_control_run.set_to_ready_lines()
        # third run
        last_control_run = self.env['credit.control.run'].create({
            'date': third,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        last_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 2)

    def test_multi_credit_control_run_negative_and_positive_levels(self):
        """
        Generate several control run with negative and positive levels
        """
        preventive_polity = self.env['credit.control.policy'].create({
            'name': 'Notify before and after due date',
            'level_ids': [
                (0, 0, {
                    'name': '30 days before',
                    'level': 1,
                    'channel': 'email',
                    'delay_days': -30,
                    'computation_mode': 'net_days',
                    'email_template_id': self.env.ref(
                        "account_credit_control."
                        "email_template_credit_control_base").id,
                    'custom_mail_text': '30 days or less until due date.',
                    'custom_text': '30 days or less until due date.',
                }),
                (0, 0, {
                    'name': '10 days after',
                    'level': 2,
                    'channel': 'email',
                    'delay_days': 10,
                    'computation_mode': 'net_days',
                    'email_template_id': self.env.ref(
                        "account_credit_control."
                        "email_template_credit_control_base").id,
                    'custom_mail_text': '10 days or more after due date.',
                    'custom_text': '10 days  or more after due date.',
                }),
            ],
            'account_ids': [(6, 0, [self.account.id])],
        })
        self.invoice.partner_id.credit_policy_id = preventive_polity.id
        # Determine dates
        date_due = self.invoice.date_due
        first = date_due - relativedelta.relativedelta(days=32)
        second = date_due - relativedelta.relativedelta(days=28)
        third = date_due + relativedelta.relativedelta(days=12)
        # First run
        first_control_run = self.env['credit.control.run'].create({
            'date': first,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        first_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 0)
        # Second run
        second_control_run = self.env['credit.control.run'].create({
            'date': second,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        second_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 1)
        second_control_run.set_to_ready_lines()
        # third run
        last_control_run = self.env['credit.control.run'].create({
            'date': third,
            'policy_ids': [(6, 0, [preventive_polity.id])],
        })
        last_control_run.with_context(lang='en_US').generate_credit_lines()
        self.assertEqual(len(self.invoice.credit_control_line_ids), 2)

    def test_wiz_print_lines(self):
        """
        Test the wizard Credit Control Printer
        """
        control_run = self.env['credit.control.run'].create({
            'date': fields.Date.today(),
            'policy_ids': [(6, 0, [self.policy.id])],
        })

        control_run.with_context(lang='en_US').generate_credit_lines()

        self.assertTrue(len(self.invoice.credit_control_line_ids), 1)
        self.assertEqual(control_run.state, 'done')

        report_regex = \
            r'<p>Policy "<b>%s</b>" has generated <b>' \
            r'\d+ Credit Control Lines.</b><br></p>' % self.policy.name
        regex_result = re.match(report_regex, control_run.report)
        self.assertIsNotNone(regex_result)

        # Mark lines to be send
        control_lines = self.invoice.credit_control_line_ids
        marker = self.env['credit.control.marker'].create({
            'name': 'to_be_sent',
            'line_ids': [(6, 0, control_lines.ids)],
        })
        marker.mark_lines()

        # Create wizard
        emailer_obj = self.env['credit.control.emailer']
        wiz_emailer = emailer_obj.create({})
        wiz_emailer.line_ids = control_lines

        # Send email
        wiz_emailer.email_lines()

    def test_wiz_credit_control_emailer(self):
        """
        Test the wizard credit control emailer
        """
        control_run = self.env['credit.control.run'].create({
            'date': fields.Date.today(),
            'policy_ids': [(6, 0, [self.policy.id])],
        })

        control_run.with_context(lang='en_US').generate_credit_lines()

        self.assertTrue(len(self.invoice.credit_control_line_ids), 1)
        self.assertEqual(control_run.state, 'done')

        report_regex = \
            r'<p>Policy "<b>%s</b>" has generated <b>' \
            r'\d+ Credit Control Lines.</b><br></p>' % self.policy.name
        regex_result = re.match(report_regex, control_run.report)
        self.assertIsNotNone(regex_result)

        # Mark lines to be send
        control_lines = self.invoice.credit_control_line_ids
        marker = self.env['credit.control.marker'].create({
            'name': 'to_be_sent',
            'line_ids': [(6, 0, control_lines.ids)],
        })
        marker.mark_lines()

        # Create wizard
        printer_obj = self.env['credit.control.printer']
        wiz_printer = printer_obj.with_context(
            active_model='credit.control.line',
            active_ids=control_lines.ids
        ).create({})
        wiz_printer.print_lines()
