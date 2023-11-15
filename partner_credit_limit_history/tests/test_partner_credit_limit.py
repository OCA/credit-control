# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import common


class TestPartnerCreditLimit(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test partner", "credit_limit": 100.00}
        )

    def test_partner_credit_limit_wizard(self):
        self.assertEqual(len(self.partner.credit_history_ids), 0)
        wizard = self.env["partner.credit.limit.wizard"].create(
            {"partner_id": self.partner.id, "amount": 200, "note": "Reason"}
        )
        wizard.action_confirm()
        self.assertEqual(len(self.partner.credit_history_ids), 1)
        history = self.partner.credit_history_ids
        self.assertEqual(history.previous_amount, 100)
        self.assertEqual(history.new_amount, 200)
        self.assertEqual(history.note, "Reason")
