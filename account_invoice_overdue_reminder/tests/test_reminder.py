#  Copyright 2022 Simone Rubino - TAKOBI
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import SavepointCase, Form
from odoo.tools.date_utils import relativedelta


class TestReminder (SavepointCase):

    @classmethod
    def _create_invoice(cls, partner, products, date, post=True):
        invoice_form = Form(cls.env['account.invoice'])
        invoice_form.partner_id = partner
        invoice_form.date_invoice = date
        for product in products:
            with invoice_form.invoice_line_ids.new() as line:
                line.product_id = product
        invoice = invoice_form.save()
        if post:
            invoice.action_invoice_open()
        return invoice

    def _start_wizard(self, partners):
        wizard_start_model = self.env['overdue.reminder.start'] \
            .with_context(
            default_partner_ids=partners.ids,
        )
        start_wizard_form = Form(wizard_start_model)
        start_wizard_form.up_to_date = True
        start_wizard = start_wizard_form.save()
        start_result = start_wizard.run()
        return start_result

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        customer_form = Form(cls.env['res.partner'])
        customer_form.name = "Test Customer"
        customer_form.customer = True
        cls.customer = customer_form.save()

        product_form = Form(cls.env['product.product'])
        product_form.name = "Test Product"
        product_form.lst_price = 100
        cls.product = product_form.save()

        one_month_ago = datetime.now() - relativedelta(months=1)
        invoice_one_month = cls._create_invoice(
            cls.customer,
            cls.product,
            one_month_ago.date(),
        )
        cls.invoice_one_month = invoice_one_month

    def test_reminder_manual_validate(self):
        """
        The Reminder Notes are mandatory for 'Manual' Reminder Type.
        """
        invoice = self.invoice_one_month
        partners = invoice.partner_id
        start_result = self._start_wizard(partners)

        step_model = start_result.get('res_model')
        step_id = start_result.get('res_id')
        step = self.env[step_model].browse(step_id)

        step_form = Form(step)
        step.reminder_type = 'manual'
        step = step_form.save()
        with self.assertRaises(UserError) as ue:
            step.validate()
        exc_message = ue.exception.args[0]
        self.assertIn('Reminder Notes', exc_message)

    def test_reminder_manual(self):
        """
        The Reminder Notes are propagated
        from the wizard to the Reminder Action.
        """
        invoice = self.invoice_one_month
        partners = invoice.partner_id
        start_result = self._start_wizard(partners)

        step_model = start_result.get('res_model')
        step_id = start_result.get('res_id')
        step = self.env[step_model].browse(step_id)

        reminder_notes = 'Test Reminder Notes'
        step_form = Form(step)
        step.reminder_type = 'manual'
        step.reminder_notes = reminder_notes
        step = step_form.save()
        step.validate()

        reminder_action = invoice.overdue_reminder_ids.action_id
        self.assertEqual(
            reminder_action.reminder_notes,
            reminder_notes,
            "Reminder notes have not been propagated to the action",
        )
