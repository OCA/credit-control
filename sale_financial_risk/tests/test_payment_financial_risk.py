# Copyright 2023 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestRiskSalePayment(AccountPaymentCommon, PaymentHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        payment_method_record = cls.env["payment.method"].browse(cls.payment_method_id)
        payment_method_record.active = True  # Ahora esto funciona
        cls.provider.write(
            {
                "state": "test",
                "is_published": True,
                "available_currency_ids": [Command.set([cls.currency.id])],
                "available_country_ids": [Command.clear()],
                "payment_method_ids": [Command.set([cls.payment_method_id])],
                "allow_tokenization": True,
            }
        )

        _logger.debug(
            "Configured provider: %s (Published: %s, Methods: %s, Tokenize: %s)",
            cls.provider.name,
            cls.provider.is_published,
            cls.provider.payment_method_ids.mapped("name"),
            cls.provider.allow_tokenization,  # Log añadido
        )
        cls.account_receivable = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_receivable"),
                ("company_ids", "in", [cls.env.company.id]),
            ],
            limit=1,
        )
        if not cls.account_receivable:
            cls.account_receivable = cls.env["account.account"].create(
                {
                    "name": "Test Receivable (Payment)",
                    "code": "TESTPYREC",
                    "account_type": "asset_receivable",
                    "reconcile": True,
                    "company_ids": [cls.env.company.id],
                }
            )
        cls.account_income = cls.env["account.account"].search(
            [
                ("account_type", "=", "income"),
                ("company_ids", "in", [cls.env.company.id]),
            ],
            limit=1,
        )
        if not cls.account_income:
            cls.account_income = cls.env["account.account"].create(
                {
                    "name": "Test Income (Payment)",
                    "code": "TESTPYINC",
                    "account_type": "income",
                    "company_ids": [cls.env.company.id],
                }
            )
        cls.partner = cls.portal_partner
        cls.partner.property_account_receivable_id = cls.account_receivable.id
        cls.partner.risk_sale_order_limit = 1
        cls.partner.risk_sale_order_include = True
        cls.pricelist = cls.env["product.pricelist"].search(
            [("currency_id", "=", cls.currency.id)], limit=1
        )
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create(
                {
                    "name": f"Test Pricelist {cls.currency.name}",
                    "currency_id": cls.currency.id,
                }
            )
        cls.sale_product = cls.env["product.product"].create(
            {
                "sale_ok": True,
                "name": "Test Product",
                "property_account_income_id": cls.account_income.id,
            }
        )
        cls.order = (
            cls.env["sale.order"]
            .sudo()
            .create(
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
        )
        cls.order.partner_invoice_id.property_account_receivable_id = (
            cls.account_receivable.id
        )
        cls.partner = cls.order.partner_invoice_id

    def test_payment_risk_bypass(self):
        """When the order confirmation come from a payment authorization the risk
        is bypassed. This is a trimmed version of sale/tests/test_11_so_payment_link
        to easily test that case"""
        # Force risk exception to whatever amount
        self.assertFalse(self.partner.risk_exception)
        _logger.debug("Creating risk exception for partner %s", self.partner)
        self.amount = self.order.amount_total
        _logger.debug("Order amount_total is %s", self.amount)
        route_values = self._prepare_pay_values()
        _logger.debug("Payment route values are %s", route_values)
        route_values["sale_order_id"] = self.order.id
        _logger.debug("Payment route values with SO are %s", route_values)
        with patch(
            "odoo.addons.payment.controllers.portal.PaymentPortal"
            "._compute_show_tokenize_input_mapping"
        ) as patched:
            _logger.debug("Patching PaymentPortal._compute_show_tokenize_input_mapping")
            tx_context = self._get_portal_pay_context(**route_values)
            _logger.debug("Payment portal context is %s", tx_context)
            patched.assert_called_once()
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
        tx_sudo._post_process()
        self.assertEqual(self.order.state, "sale")
        self.assertTrue(tx_sudo.payment_id)
        self.assertEqual(tx_sudo.payment_id.state, "in_process")
        # The order gets confirmed despite the risk exception
        self.assertTrue(self.partner.risk_exception)
