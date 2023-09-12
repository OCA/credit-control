# Copyright 2023 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged("-at_install", "post_install")
class TestRiskSalePayment(PaymentCommon, PaymentHttpCommon):
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
        cls.partner.risk_sale_order_limit = 1
        cls.partner.risk_sale_order_include = True
        cls.pricelist = cls.env["product.pricelist"].search(
            [("currency_id", "=", cls.currency.id)], limit=1
        )
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create(
                {
                    "name": "Test Pricelist (%s)" % (cls.currency.name),
                    "currency_id": cls.currency.id,
                }
            )
        cls.sale_product = cls.env["product.product"].create(
            {
                "sale_ok": True,
                "name": "Test Product",
            }
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "pricelist_id": cls.pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.sale_product.id,
                            "product_uom_qty": 5,
                            "price_unit": 20,
                        }
                    )
                ],
            }
        )
        cls.partner = cls.order.partner_invoice_id

    def test_payment_risk_bypass(self):
        """When the order confirmation come from a payment authorization the risk
        is bypassed. This is a trimmed version of sale/tests/test_11_so_payment_link
        to easily test that case"""
        # Force risk exception to whatever amount
        self.assertFalse(self.partner.risk_exception)
        self.amount = self.order.amount_total
        route_values = self._prepare_pay_values()
        route_values["sale_order_id"] = self.order.id
        tx_context = self.get_tx_checkout_context(**route_values)
        route_values.update(
            {
                "flow": "direct",
                "payment_option_id": self.acquirer.id,
                "tokenization_requested": False,
                "validation_route": False,
                "reference_prefix": None,  # Force empty prefix to fallback on SO reference
                "landing_route": tx_context["landing_route"],
                "amount": tx_context["amount"],
                "currency_id": tx_context["currency_id"],
            }
        )
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values["reference"])
        # Check validation of transaction correctly confirms the SO
        self.assertEqual(self.order.state, "draft")
        tx_sudo._set_done()
        tx_sudo._finalize_post_processing()
        self.assertEqual(self.order.state, "sale")
        self.assertTrue(tx_sudo.payment_id)
        self.assertEqual(tx_sudo.payment_id.state, "posted")
        # The order gets confirmed despite the risk exception
        self.assertTrue(self.partner.risk_exception)
