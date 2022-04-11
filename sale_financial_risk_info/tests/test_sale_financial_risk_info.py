# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestSaleFinancialRiskInfo(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Partner = self.env["res.partner"]
        self.Product = self.env["product.product"]

        self.product_1 = self.Product.create(
            {"name": "Product test 1", "list_price": 1000.00}
        )
        self.partner_1 = self.Partner.create(
            {
                "name": "partner test rebate 1",
                "ref": "TST-001",
                "risk_invoice_draft_include": True,
            }
        )
        self.default_account_revenue = self.env["account.account"].search(
            [
                ("company_id", "=", self.env.user.company_ids[0].id),
                (
                    "user_type_id",
                    "=",
                    self.env.ref("account.data_account_type_revenue").id,
                ),
            ],
            limit=1,
        )
        self.invoice_partner_1 = self.create_invoice(self.partner_1)

    # Create some invoices for partner
    def create_invoice(self, partner):
        move_form = Form(
            self.env["account.move"].with_context(default_type="out_invoice")
        )
        move_form.ref = "Test Customer Invoice"
        move_form.partner_id = partner
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_1
            line_form.account_id = self.default_account_revenue
        return move_form.save()

    def test_sale_order_risk_info(self):
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_1
        self.assertIn("Unlimited", so_form.risk_info)
        self.partner_1.credit_limit = 2000
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_1
        self.assertNotIn("unlimited", so_form.risk_info)
