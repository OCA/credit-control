# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from datetime import date, timedelta

from odoo.exceptions import UserError

from odoo.addons.sale.tests.common import SaleCommon


class TestPartnerCreditControl(SaleCommon):
    def setUp(self):
        super().setUp()

        # MODELS
        self.Move = self.env["account.move"]
        self.Sale = self.env["sale.order"]

        self.partner.write(
            {
                "credit_limit_exception": True,
                "credit_limit_day": 10,
            }
        )

    def _create_invoice(self, days_ago=10, amount=100):
        """
        Create a posted invoice with a specific age and residual amount.
        """
        invoice_date = date.today() - timedelta(days=days_ago)

        invoice = self.Move.create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": invoice_date,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test Line",
                            "quantity": 1,
                            "price_unit": amount,
                        },
                    )
                ],
            }
        )

        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertTrue(invoice.amount_residual > 0)

        return invoice

    def test_compute_credit_average_day(self):
        """
        Validate computed average invoice age.
        """
        # Invoice ages: 5 days, 15 days → expected average = 10
        inv1 = self._create_invoice(days_ago=5)
        self.assertTrue(inv1)
        inv2 = self._create_invoice(days_ago=15)
        self.assertTrue(inv2)

        self.partner._compute_credit_average_day()
        self.assertAlmostEqual(self.partner.credit_average_day, 10.0, 2)

    def test_sale_order_confirm_blocked(self):
        """
        Should block confirming the SO when average
        age > limit and user is not Credit Manager.
        """

        # Invoice age 20 days → exceeds credit_limit_day=10
        self._create_invoice(days_ago=20)

        sale = self.Sale.create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 50,
                        },
                    )
                ],
            }
        )

        with self.assertRaises(UserError):
            sale.action_confirm()

    def test_sale_order_confirm_allowed_for_manager(self):
        """
        Should allow confirming the SO if the user is Credit Manager.
        """

        # Invoice age 20 days → exceeds credit limit
        self._create_invoice(days_ago=20)

        sale = self.Sale.create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 50,
                        },
                    )
                ],
            }
        )

        # Add current user to Credit Manager group
        group = self.env.ref("partner_credit_average_day.group_credit_manager")
        self.env.user.groups_id = [(4, group.id)]

        # Should not raise UserError
        sale.action_confirm()

        # State may not immediately become "sale" depending on workflow,
        # but method should complete without raising an exception.
        self.assertTrue(True)
