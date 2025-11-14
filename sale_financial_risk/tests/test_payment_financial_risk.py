# Copyright 2023 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestRiskSalePayment(AccountPaymentCommon, PaymentHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Account = cls.env["account.account"]
        cls.Pricelist = cls.env["product.pricelist"]
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
        cls.account_receivable = cls.Account.search(
            [
                ("account_type", "=", "asset_receivable"),
                ("company_ids", "in", [cls.env.company.id]),
            ],
            limit=1,
        )
        if not cls.account_receivable:
            cls.account_receivable = cls.Account.create(
                {
                    "name": "Test Receivable (Payment)",
                    "code": "TESTPYREC",
                    "account_type": "asset_receivable",
                    "reconcile": True,
                    "company_ids": [cls.env.company.id],
                }
            )
        cls.account_income = cls.Account.search(
            [
                ("account_type", "=", "income"),
                ("company_ids", "in", [cls.env.company.id]),
            ],
            limit=1,
        )
        if not cls.account_income:
            cls.account_income = cls.Account.create(
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
        cls.pricelist = cls.Pricelist.search(
            [("currency_id", "=", cls.currency.id)], limit=1
        )
        if not cls.pricelist:
            cls.pricelist = cls.Pricelist.create(
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
        """Bypass risk when confirming sale order from payment transaction"""
        self.amount = self.order.amount_total
        tx_pending = self._create_transaction(
            flow="direct",
            sale_order_ids=[self.order.id],
            state="pending",
            reference="Test Transaction Draft 1",
        )
        self.assertEqual(self.order.state, "draft")
        tx_pending._set_done()
        tx_pending._post_process()
        self.assertEqual(self.order.state, "sale")
        # The order gets confirmed despite the risk exception
        self.assertTrue(self.partner.risk_exception)
