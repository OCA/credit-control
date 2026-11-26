# Copyright 2026 NICO SOLUTIONS - ENGINEERING & IT, Nils Coenen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command, fields
from odoo.tests.common import TransactionCase
from odoo.tools.misc import format_date


class TestOverdueReminderAction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.product = cls.env["product.product"].create({"name": "Test Product"})
        uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.invoice_model = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": "2025-12-31",
                "line_ids": [
                    Command.create(
                        {
                            "name": "Test line",
                            "partner_id": cls.partner.id,
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "product_id": cls.product.id,
                            "product_uom_id": uom_unit.id,
                        },
                    )
                ],
            }
        )
        cls.reminder_action = cls.env["overdue.reminder.action"].create(
            {
                "reminder_type": "mail",
                "partner_id": cls.partner.id,
                "commercial_partner_id": cls.partner.id,
            }
        )
        cls.reminder_model = cls.env["account.invoice.overdue.reminder"].create(
            {
                "invoice_id": cls.invoice_model.id,
                "action_id": cls.reminder_action.id,
                "counter": 0,
            }
        )

    def test_default_values(self):
        self.assertEqual(self.reminder_action.user_id, self.env.user)
        self.assertEqual(self.reminder_action.reminder_type, "mail")
        self.assertEqual(
            self.reminder_action.date, fields.Date.context_today(self.reminder_action)
        )

    def test_compute_invoice_count(self):
        self.reminder_action._compute_invoice_count()
        self.assertEqual(self.reminder_action.reminder_count, 1)

    def test_compute_display_name(self):
        self.reminder_action._compute_display_name()
        self.assertIn("Test Partner", self.reminder_action.display_name)
        expected_date = format_date(self.env, self.reminder_action.date)
        self.assertIn(expected_date, self.reminder_action.display_name)
