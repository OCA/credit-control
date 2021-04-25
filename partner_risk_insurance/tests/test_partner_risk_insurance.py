# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import SavepointCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderLineInput(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test",
                "company_credit_limit": 100.00,
                "insurance_credit_limit": 50.00,
            }
        )

    def test_credit_limit(self):
        self.assertEqual(self.partner.credit_limit, 150.00)
