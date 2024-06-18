# Copyright 2023 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from unittest.mock import ANY, patch

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged("-at_install", "post_install")
class TestRiskSalePayment(AccountPaymentCommon, SaleCommon, PaymentHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
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
        with patch(
            "odoo.addons.payment.controllers.portal.PaymentPortal"
            "._compute_show_tokenize_input_mapping"
        ) as patched:
            tx_context = self._get_portal_pay_context(**route_values)
            patched.assert_called_once_with(ANY, sale_order_id=ANY)
        tx_route_values = {
            "provider_id": self.provider.id,
            "payment_method_id": self.payment_method_id,
            "token_id": None,
            "amount": tx_context["amount"],
            "flow": "direct",
            "tokenization_requested": False,
            "landing_route": tx_context["landing_route"],
            "access_token": tx_context["access_token"],
        }
        with mute_logger("odoo.addons.payment.models.payment_transaction"):
            processing_values = self._get_processing_values(
                tx_route=tx_context["transaction_route"], **tx_route_values
            )
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
