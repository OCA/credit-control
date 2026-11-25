# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestOverdueReminder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        invoice_date = fields.Date.context_today(cls.env.user) - relativedelta(days=60)
        cls.invoices = cls.init_invoice(
            "out_invoice",
            partner=cls.partner_a,
            invoice_date=invoice_date,
            amounts=[100],
        ) + cls.init_invoice(
            "out_invoice",
            partner=cls.partner_b,
            invoice_date=invoice_date,
            amounts=[200],
        )
        cls.invoices.action_post()

    def test_mass_validate_phone_reminders_with_activity(self):
        start = self.env["overdue.reminder.start"].create(
            {
                "interface": "mass",
                "partner_ids": [(6, 0, (self.partner_a + self.partner_b).ids)],
            }
        )
        start.run()
        steps = self.env["overdue.reminder.step"].search(
            [("user_id", "=", self.env.user.id)]
        )
        self.assertEqual(len(steps), 2)
        steps.write(
            {
                "reminder_type": "phone",
                "create_activity": True,
                "activity_summary": "Call back",
                "activity_deadline": fields.Date.context_today(self.env.user),
                "activity_user_id": self.env.user.id,
            }
        )
        self.env["overdue.reminder.mass.update"].with_context(
            active_model="overdue.reminder.step", active_ids=steps.ids
        ).create({"update_action": "validate"}).run()
        self.assertEqual(steps.mapped("state"), ["done", "done"])
        activities = self.env["mail.activity"].search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "in", (self.partner_a + self.partner_b).ids),
                ("summary", "=", "Call back"),
            ]
        )
        self.assertEqual(
            set(activities.mapped("res_id")), set((self.partner_a + self.partner_b).ids)
        )
