# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestSaleFinancialRiskInfo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.Partner = cls.env["res.partner"]
        cls.Product = cls.env["product.product"]

        cls.product_1 = cls.Product.create(
            {"name": "Product test 1", "list_price": 1000.00}
        )
        cls.partner_1 = cls.Partner.create(
            {
                "name": "partner test rebate 1",
                "ref": "TST-001",
                "risk_invoice_draft_include": True,
            }
        )
        cls.default_account_revenue = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.env.company.id),
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_revenue").id,
                ),
            ],
            limit=1,
        )
        cls.invoice_partner_1 = cls.create_invoice(cls.partner_1)

    # Create some invoices for partner
    @classmethod
    def create_invoice(cls, partner):
        move_form = Form(
            cls.env["account.move"].with_context(default_type="out_invoice")
        )
        move_form.ref = "Test Customer Invoice"
        move_form.partner_id = partner
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product_1
            line_form.account_id = cls.default_account_revenue
        return move_form.save()

    def test_sale_order_risk_info(self):
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_1
        self.assertIn("Unlimited", so_form.risk_info)
        self.partner_1.credit_limit = 2000
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_1
        self.assertNotIn("unlimited", so_form.risk_info)
