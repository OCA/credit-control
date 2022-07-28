# Copyright 2022 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.sale_payment_sheet.tests.test_sale_payment_sheet import (
    TestSaleInvoicePayment,
)


class TestSalePaymentSheetFinancialRisk(TestSaleInvoicePayment):
    def test_payment_wizard_risk(self):
        self.test_payment_wizard()
        self.assertEqual(self.partner.risk_sale_payment_sheet, -150.00)
        self.assertFalse(self.partner.risk_sale_payment_sheet_info)
        self.partner.risk_sale_payment_sheet_include = True
        self.assertIn("150", self.partner.risk_sale_payment_sheet_info)
