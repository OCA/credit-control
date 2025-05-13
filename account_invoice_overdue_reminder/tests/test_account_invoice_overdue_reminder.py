# Copyright 2025 Onestein (<https://www.onestein.nl>)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)


from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, freeze_time, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@freeze_time("2025-05-13")
@tagged("post_install", "-at_install")
class TestAccountInvoiceOverdueReminder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["overdue.reminder.start"].search([]).unlink()

    def create_overdue_reminder(self, vals):
        return self.env["overdue.reminder.start"].create(vals)

    def create_invoice(self, date):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": date,
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "price_unit": 500,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def test_overdue_reminder_start_form(self):
        overdue_reminder_start_form = Form(self.env["overdue.reminder.start"])
        overdue_reminder_start_form.start_days = -10
        overdue_reminder_start = overdue_reminder_start_form.save()
        with self.assertRaisesRegex(
            UserError, self.env._("The trigger delay cannot be negative.")
        ):
            overdue_reminder_start.run()
        overdue_reminder_start_form = Form(self.env["overdue.reminder.start"])
        overdue_reminder_start_form.min_interval_days = 0
        overdue_reminder_start = overdue_reminder_start_form.save()
        with self.assertRaisesRegex(
            UserError,
            self.env._(
                "The minimum delay since last reminder must be strictly positive."
            ),
        ):
            overdue_reminder_start.run()
        overdue_reminder_start_form = Form(self.env["overdue.reminder.start"])
        overdue_reminder_start = overdue_reminder_start_form.save()
        with self.assertRaisesRegex(
            UserError, self.env._("There are no overdue reminders.")
        ):
            overdue_reminder_start.run()
        self.create_invoice("2025-05-12")
        overdue_reminder_start_form = Form(self.env["overdue.reminder.start"])
        overdue_reminder_start_form.partner_policy = "last_invoice"
        overdue_reminder_start = overdue_reminder_start_form.save()
        action = overdue_reminder_start.run()
        overdue_step_reminder_rec = self.env["overdue.reminder.step"].browse(
            action["res_id"]
        )
        self.assertTrue(overdue_step_reminder_rec.partner_id)
        overdue_reminder_start_form = Form(self.env["overdue.reminder.start"])
        overdue_reminder_start_form.partner_policy = "invoice_contact"
        overdue_reminder_start = overdue_reminder_start_form.save()
        action = overdue_reminder_start.run()
        overdue_step_reminder_rec = self.env["overdue.reminder.step"].browse(
            action["res_id"]
        )
        self.assertTrue(overdue_step_reminder_rec.partner_id)
        self.partner_a.no_overdue_reminder = True
        overdue_reminder_start_form = Form(self.env["overdue.reminder.start"])
        overdue_reminder_start_form.partner_ids.add(self.partner_a)
        overdue_reminder_start_form.user_ids.add(self.env.user)
        overdue_reminder_start = overdue_reminder_start_form.save()
        with self.assertRaisesRegex(
            UserError, self.env._("There are no overdue reminders.")
        ):
            overdue_reminder_start.run()

    def test_overdue_reminder_skip(self):
        invoice = self.create_invoice("2025-05-12")
        self.assertTrue(invoice.overdue)
        action = self.create_overdue_reminder({}).run()
        self.assertEqual(
            action["xml_id"],
            "account_invoice_overdue_reminder.overdue_reminder_step_onebyone_action",
        )
        overdue_step_reminder_rec = self.env["overdue.reminder.step"].browse(
            action["res_id"]
        )
        overdue_step_reminder_rec.skip()
        self.assertEqual(overdue_step_reminder_rec.state, "skipped")

    def test_overdue_step_reminder_validate_mail(self):
        invoice = self.create_invoice("2025-05-12")
        self.assertTrue(invoice.overdue)
        action = self.create_overdue_reminder({}).run()
        self.assertEqual(
            action["xml_id"],
            "account_invoice_overdue_reminder.overdue_reminder_step_onebyone_action",
        )
        overdue_step_reminder_rec = self.env["overdue.reminder.step"].browse(
            action["res_id"]
        )
        with self.assertRaisesRegex(UserError, self.env._("E-mail missing on partner")):
            overdue_step_reminder_rec.validate()
        self.partner_a.email = "test@gmail.com"
        mail_subject = overdue_step_reminder_rec.mail_subject
        overdue_step_reminder_rec.mail_subject = False
        with self.assertRaisesRegex(UserError, self.env._("Mail subject is empty.")):
            overdue_step_reminder_rec.validate()
        overdue_step_reminder_rec.mail_subject = mail_subject
        mail_body = overdue_step_reminder_rec.mail_body
        overdue_step_reminder_rec.mail_body = False
        with self.assertRaisesRegex(UserError, self.env._("Mail body is empty.")):
            overdue_step_reminder_rec.validate()
        overdue_step_reminder_rec.mail_body = mail_body
        overdue_step_reminder_rec.validate()
        self.assertTrue(invoice.overdue_reminder_last_date)
        with self.assertRaisesRegex(
            UserError, self.env._("There are no overdue reminders.")
        ):
            self.create_overdue_reminder({}).run()

    def test_overdue_step_reminder_validate_phone(self):
        invoice = self.create_invoice("2025-05-12")
        self.assertTrue(invoice.overdue)
        action = self.create_overdue_reminder({}).run()
        self.assertEqual(
            action["xml_id"],
            "account_invoice_overdue_reminder.overdue_reminder_step_onebyone_action",
        )
        overdue_step_reminder_rec = self.env["overdue.reminder.step"].browse(
            action["res_id"]
        )
        invoice_ids = overdue_step_reminder_rec.invoice_ids
        overdue_step_reminder_rec.invoice_ids = False
        with self.assertRaisesRegex(
            UserError, self.env._("There are no invoices to remind for customer")
        ):
            overdue_step_reminder_rec.validate()
        overdue_step_reminder_rec.invoice_ids = invoice_ids
        overdue_step_reminder_rec.reminder_type = "phone"
        overdue_step_reminder_rec.create_activity = True
        activity_user_id = overdue_step_reminder_rec.activity_user_id
        overdue_step_reminder_rec.activity_user_id = False
        with self.assertRaisesRegex(UserError, self.env._("you must assign someone")):
            overdue_step_reminder_rec.validate()
        overdue_step_reminder_rec.activity_user_id = activity_user_id
        with self.assertRaisesRegex(UserError, self.env._("the deadline is missing")):
            overdue_step_reminder_rec.validate()
        overdue_step_reminder_rec.activity_deadline = fields.Date.today()
        overdue_step_reminder_rec.validate()
        overdue_reminder_action = self.env["overdue.reminder.action"].search([])
        self.assertTrue(len(overdue_reminder_action))
        self.assertTrue(overdue_reminder_action.reminder_count)

    def test_overdue_step_reminder_validate_letter(self):
        invoice = self.create_invoice("2025-05-12")
        self.assertTrue(invoice.overdue)
        action = self.create_overdue_reminder({}).run()
        self.assertEqual(
            action["xml_id"],
            "account_invoice_overdue_reminder.overdue_reminder_step_onebyone_action",
        )
        overdue_step_reminder_rec = self.env["overdue.reminder.step"].browse(
            action["res_id"]
        )
        overdue_step_reminder_rec.reminder_type = "post"
        overdue_step_reminder_rec.reminder_type_change()
        with self.assertRaisesRegex(
            UserError, self.env._("Remind letter hasn't been printed")
        ):
            overdue_step_reminder_rec.validate()
        overdue_step_reminder_rec.print_invoices()
        overdue_step_reminder_rec.print_letter()
        overdue_step_reminder_rec.validate()
