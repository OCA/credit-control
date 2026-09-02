# Copyright 2026 NICO SOLUTIONS - ENGINEERING & IT, Nils Coenen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command, fields
from odoo.tests.common import TransactionCase


class TestAccountMove(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.company = cls.env.company
        cls.overdue_invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date_due": fields.Date.subtract(fields.Date.today(), days=5),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line overdue",
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
                "company_id": cls.company.id,
            }
        )
        cls.overdue_invoice.action_post()
        cls.overdue_invoice.payment_state = "not_paid"
        cls.not_due_invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date_due": fields.Date.add(fields.Date.today(), days=5),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line not due",
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
                "company_id": cls.company.id,
            }
        )
        cls.not_due_invoice.action_post()
        cls.not_due_invoice.payment_state = "not_paid"

        cls.reminder_action = cls.env["overdue.reminder.action"].create(
            {
                "commercial_partner_id": cls.partner.id,
                "partner_id": cls.partner.id,
                "date": fields.Date.today(),
                "user_id": cls.env.ref("base.user_admin").id,
                "reminder_type": "mail",
            }
        )

    def test_overdue_computation(self):
        self.assertTrue(self.overdue_invoice.overdue, "Invoice should be overdue")
        self.assertFalse(self.not_due_invoice.overdue, "Invoice should not be overdue")

    def test_overdue_reminder_counter_initial(self):
        self.assertEqual(self.overdue_invoice.overdue_reminder_counter, 0)
        self.assertFalse(self.overdue_invoice.overdue_reminder_last_date)

    def test_overdue_remind_sent_logic(self):
        company = self.env.company
        company.overdue_reminder_min_interval_days = 3
        self.assertFalse(self.overdue_invoice.overdue_remind_sent)
        self.env["account.invoice.overdue.reminder"].create(
            {
                "invoice_id": self.overdue_invoice.id,
                "action_id": self.reminder_action.id,
                "counter": 1,
                "action_date": fields.Date.subtract(fields.Date.today(), days=1),
            }
        )
        self.overdue_invoice._compute_overdue_reminder_sent()
        self.assertTrue(self.overdue_invoice.overdue_remind_sent)

    def test_compute_overdue_reminder_multiple(self):
        self.env["account.invoice.overdue.reminder"].create(
            {
                "invoice_id": self.overdue_invoice.id,
                "action_id": self.reminder_action.id,
                "counter": 1,
                "action_date": fields.Date.subtract(fields.Date.today(), days=5),
            }
        )
        self.env["account.invoice.overdue.reminder"].create(
            {
                "invoice_id": self.overdue_invoice.id,
                "action_id": self.reminder_action.id,
                "counter": 3,
                "action_date": fields.Date.subtract(fields.Date.today(), days=1),
            }
        )
        self.overdue_invoice._compute_overdue_reminder()
        reminder = self.env["account.invoice.overdue.reminder"].search(
            [("invoice_id", "=", self.overdue_invoice.id)],
            order="action_date desc, id desc",
            limit=1,
        )
        self.assertEqual(
            self.overdue_invoice.overdue_reminder_last_date, reminder.action_date
        )
        self.assertEqual(
            self.overdue_invoice.overdue_reminder_counter, reminder.counter
        )

    def test_no_overdue_reminder_flag(self):
        self.overdue_invoice.no_overdue_reminder = True
        self.assertTrue(
            self.overdue_invoice.no_overdue_reminder,
            "Invoice should have no_overdue_reminder=True",
        )
        self.overdue_invoice._compute_overdue()
        self.assertTrue(
            self.overdue_invoice.overdue,
            "Overdue may still be True, we are only testing the flag here",
        )
