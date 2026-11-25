# Copyright 2026 NICO SOLUTIONS - ENGINEERING & IT, Nils Coenen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAccountInvoiceOverdueReminder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        cls.invalid_invoice = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Vendor line",
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        cls.reminder_action = cls.env["overdue.reminder.action"].create(
            {
                "commercial_partner_id": cls.partner.id,
                "partner_id": cls.partner.id,
                "date": "2024-01-01",
                "user_id": cls.env.ref("base.user_admin").id,
                "reminder_type": "mail",
            }
        )

    def test_accept_out_invoice(self):
        rec = self.env["account.invoice.overdue.reminder"].create(
            {
                "invoice_id": self.invoice.id,
                "action_id": self.reminder_action.id,
                "counter": 1,
            }
        )
        self.assertTrue(rec.exists())
        self.assertEqual(rec.counter, 1)

    def test_display_name_compute(self):
        rec = self.env["account.invoice.overdue.reminder"].create(
            {
                "invoice_id": self.invoice.id,
                "action_id": self.reminder_action.id,
                "counter": 3,
            }
        )
        expected = f"{self.invoice.name} Reminder n°3"
        self.assertEqual(rec.display_name, expected)

    def test_reject_in_invoice(self):
        with self.assertRaises(ValidationError):
            self.env["account.invoice.overdue.reminder"].create(
                {
                    "invoice_id": self.invalid_invoice.id,
                    "action_id": self.reminder_action.id,
                    "counter": 1,
                }
            )
