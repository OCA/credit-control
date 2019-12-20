# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from datetime import datetime
from dateutil import relativedelta

from odoo import fields
from odoo.tests.common import SavepointCase
from odoo.tools import mute_logger


class TestCreditControlEmailer(SavepointCase):

    @mute_logger("odoo.addons.queue_job.models.base")
    def setUp(self):
        self.env = self.env(
            context=dict(self.env.context, test_queue_job_no_delay=True)
        )
        super(TestCreditControlEmailer, self).setUp()

        journal = self.env['account.invoice']._default_journal()

        account_type_rec = self.env.ref('account.data_account_type_receivable')
        account = self.env['account.account'].create({
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
            'account_ids': [(6, 0, [account.id])],
        })

        # There is a bug with Odoo ...
        # The field "credit_policy_id" is considered as an "old field" and
        # the field property_account_receivable_id like a "new field"
        # The ORM will create the record with old field
        # and update the record with new fields.
        # However constrains are applied after the first creation.
        partner = self.env['res.partner'].create({
            'name': 'Partner',
            'property_account_receivable_id': account.id,
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

    @mute_logger("odoo.addons.queue_job.models.base")
    def test_async_emailer(self):
        """
        Test to send emails asynchronously
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

    @mute_logger("odoo.addons.queue_job.models.base")
    def test_sync_emailer(self):
        """
        Test to send emails synchronously
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
        wiz_emailer = emailer_obj.create({'run_in_jobs': False})
        wiz_emailer.line_ids = control_lines

        # Send email
        wiz_emailer.email_lines()
