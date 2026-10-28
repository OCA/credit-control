# Copyright 2026 NICO SOLUTIONS - ENGINEERING & IT, Nils Coenen
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command, fields
from odoo.exceptions import UserError

from odoo.addons.base.tests.common import BaseCommon


class TestOverdueRemindMassUpdate(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
            }
        )
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_date_due": fields.Date.today(),
            }
        )
        cls.step = cls.env["overdue.reminder.step"].create(
            {
                "partner_id": cls.partner.id,
                "commercial_partner_id": cls.partner.id,
                "user_id": cls.user_admin.id,
                "invoice_ids": [Command.set(cls.invoice.ids)],
                "reminder_type": "mail",
            }
        )

    def _create_wizard(self, update_action, reminder_type=None):
        return self.env["overdue.reminder.mass.update"].create(
            {
                "update_action": update_action,
                "reminder_type": reminder_type,
            }
        )

    def test_run_validate(self):
        wizard_rec = self._create_wizard("validate")
        wizard_rec.with_context(
            active_model="overdue.reminder.step", active_ids=[self.step.id]
        ).run()
        self.assertEqual(self.step.state, "done")

    def test_run_skip(self):
        wizard_rec = self._create_wizard("skip")
        wizard_rec.with_context(
            active_model="overdue.reminder.step", active_ids=[self.step.id]
        ).run()
        self.assertEqual(self.step.state, "skipped")

    def test_run_reminder_type_change(self):
        wizard = self.env["overdue.reminder.mass.update"].create(
            {
                "update_action": "reminder_type",
                "reminder_type": "phone",
            }
        )
        wizard.with_context(
            active_model="overdue.reminder.step", active_ids=[self.step.id]
        ).run()
        self.assertEqual(self.step.reminder_type, "phone")

    def test_run_reminder_type_missing(self):
        wizard = self._create_wizard("reminder_type")
        with self.assertRaises(UserError):
            wizard.with_context(
                active_model="overdue.reminder.step", active_ids=[self.step.id]
            ).run()
