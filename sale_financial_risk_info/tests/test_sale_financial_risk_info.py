# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase, tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("-at_install", "post_install")
class TestSaleFinancialRiskInfo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        if not cls.env.company.chart_template_id:
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)
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
        cls.invoice_partner_1 = cls.create_invoice(cls.partner_1)

    # Create some invoices for partner
    @classmethod
    def create_invoice(cls, partner):
        simple_invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "ref": "Test Customer Invoice",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_1.id,
                            "quantity": 1,
                        },
                    ),
                ],
            }
        )
        return simple_invoice

    def test_sale_order_risk_info(self):
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_1
        self.assertIn("Unlimited", so_form.risk_info)
        self.partner_1.credit_limit = 2000
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_1
        self.assertNotIn("unlimited", so_form.risk_info)
