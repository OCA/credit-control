# Copyright 2026 NICO SOLUTIONS - ENGINEERING & IT, Nils Coenen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestOverdueReminderStart(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Customer",
                "customer_rank": 1,
            }
        )
        cls.user = cls.env.user
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "commercial_partner_id": cls.partner.id,
                "invoice_date": fields.Date.subtract(fields.Date.today(), days=30),
                "invoice_date_due": fields.Date.subtract(fields.Date.today(), days=15),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test Line",
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        cls.invoice.action_post()
        cls.wizard = cls.env["overdue.reminder.start"].create(
            {
                "start_days": 5,
                "min_interval_days": 5,
                "company_id": cls.company.id,
                "partner_policy": "invoice_contact",
                "interface": "onebyone",
            }
        )

    def test_default_get(self):
        values = self.wizard.default_get(
            ["start_days", "min_interval_days", "partner_policy", "payment_ids"]
        )
        self.assertIn("start_days", values)
        self.assertIn("payment_ids", values)

    def test_prepare_base_domain(self):
        domain = self.wizard._prepare_base_domain()
        self.assertIn(("company_id", "=", self.company.id), domain)
        self.assertIn(("state", "=", "posted"), domain)

    def test_run_interface_onebyone_and_mass(self):
        """
        Test the run method for both 'onebyone' and 'mass' interfaces,
        ensuring both the 'if vals:' and interface branches are covered.
        """
        self.invoice.write(
            {
                "invoice_date_due": fields.Date.subtract(fields.Date.today(), days=10),
                "payment_state": "not_paid",
                "amount_residual": self.invoice.amount_total,
            }
        )
        self.wizard.start_days = 0
        self.wizard.min_interval_days = 1
        self.wizard.partner_ids = self.partner

        self.wizard.interface = "onebyone"
        action_one = self.wizard.run()
        self.assertIn("res_id", action_one)
        self.assertIsInstance(action_one["res_id"], int)
        steps = self.env["overdue.reminder.step"].search(
            [
                ("commercial_partner_id", "=", self.partner.id),
            ]
        )
        self.assertGreater(len(steps), 0)
        self.wizard.interface = "mass"
        action_mass = self.wizard.run()
        self.assertEqual(action_mass["type"], "ir.actions.act_window")
        self.assertEqual(action_mass["res_model"], "overdue.reminder.step")

    def test_prepare_remind_trigger_domain(self):
        base = self.wizard._prepare_base_domain()
        domain = self.wizard._prepare_remind_trigger_domain(base)
        self.assertTrue(any(d[0] == "invoice_date_due" for d in domain))

    def test_run_negative_start_days(self):
        self.wizard.start_days = -1
        with self.assertRaises(UserError):
            self.wizard.run()

    def test_run_invalid_min_interval(self):
        self.wizard.start_days = 1
        self.wizard.min_interval_days = 0
        with self.assertRaises(UserError):
            self.wizard.run()

    def test_run_no_overdue_reminders(self):
        self.wizard.start_days = 0
        no_invoice_partner = self.env["res.partner"].create(
            {
                "name": "No Invoice Partner",
                "customer_rank": 1,
            }
        )
        self.wizard.partner_ids = no_invoice_partner
        with self.assertRaises(UserError):
            self.wizard.run()

        steps = self.env["overdue.reminder.step"].search(
            [
                ("commercial_partner_id", "=", no_invoice_partner.id),
            ]
        )
        self.assertEqual(len(steps), 0)

    def test_run_creates_reminder_step(self):
        self.invoice.write(
            {
                "invoice_date_due": fields.Date.subtract(fields.Date.today(), days=10),
                "payment_state": "not_paid",
                "amount_residual": self.invoice.amount_total,
            }
        )
        self.wizard.start_days = 5
        self.wizard.min_interval_days = 1
        self.wizard.partner_ids = self.partner
        action = self.wizard.run()
        self.assertTrue(action)
        steps = self.env["overdue.reminder.step"].search(
            [
                ("commercial_partner_id", "=", self.partner.id),
            ]
        )
        self.assertGreater(len(steps), 0)
