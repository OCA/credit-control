# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon

from ..hooks import post_init_hook, uninstall_hook


class TestSaleFinancialRiskInvoicedAlone(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Partner test", "customer_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 115.0,
                "taxes_id": [],
                "invoice_policy": "order",
            }
        )
        cls.discount_product = cls.env["product.product"].create(
            {"name": "Discount", "type": "service", "taxes_id": []}
        )
        cls.env.company.sale_discount_product_id = cls.discount_product
        cls.discount_vals = {
            "product_id": cls.discount_product.id,
            "product_uom_qty": 1,
            "price_unit": -15.0,
            "tax_id": False,
        }
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 115.0,
                            "tax_id": False,
                        },
                    ),
                    (0, 0, cls.discount_vals),
                ],
            }
        )
        cls.sale_order.action_confirm()
        cls.product_line = cls.sale_order.order_line.filtered(
            lambda line: line.product_id == cls.product
        )
        cls.discount_line = cls.sale_order.order_line - cls.product_line

    def test_line_not_invoiced_alone(self):
        """A line that is only invoiced with other lines, as a delivery or a
        discount, has no risk when the rest of the order has none."""
        self.assertAlmostEqual(self.partner.risk_sale_order, 100.0)
        # The customer finally does not want the product
        self.product_line.product_uom_qty = 0.0
        self.assertAlmostEqual(self.discount_line.risk_amount, 0.0)
        self.assertAlmostEqual(self.partner.risk_sale_order, 0.0)
        # The customer wants it again
        self.product_line.product_uom_qty = 1.0
        self.assertAlmostEqual(self.discount_line.risk_amount, -15.0)
        self.assertAlmostEqual(self.partner.risk_sale_order, 100.0)

    def test_order_with_only_lines_not_invoiced_alone(self):
        """An order with only such lines is invoiced, so it has risk."""
        order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "order_line": [(0, 0, self.discount_vals)]}
        )
        order.action_confirm()
        self.assertAlmostEqual(order.order_line.risk_amount, -15.0)

    def test_hooks(self):
        """Uninstalling gives back the risk of the lines this module left
        without it, and installing removes it again."""
        self.product_line.product_uom_qty = 0.0
        self.assertAlmostEqual(self.discount_line.risk_amount, 0.0)
        uninstall_hook(self.env)
        self.assertAlmostEqual(self.discount_line.risk_amount, -15.0)
        post_init_hook(self.env)
        self.assertAlmostEqual(self.discount_line.risk_amount, 0.0)
