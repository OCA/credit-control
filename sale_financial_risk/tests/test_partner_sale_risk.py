# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import TransactionCase

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


class TestPartnerSaleRisk(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.env.user.groups_id |= cls.env.ref(
            "account_financial_risk.group_account_financial_risk_manager"
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Partner test", "customer_rank": 1}
        )
        cls.product = cls.env.ref("product.product_product_2")
        cls.product.invoice_policy = "order"
        cls.product_pricelist = cls.env["product.pricelist"].create(
            {"name": "pricelist for sale_financial_risk test"}
        )
        cls.main_currency = cls.env.company.currency_id
        cls.EUR = cls.env.ref("base.EUR")
        cls.USD = cls.env.ref("base.USD")
        cls.sale_order = cls.create_sale_order(cls.main_currency, cls.env.company)
        cls.env.user.lang = "en_US"

    @classmethod
    def create_sale_order(cls, currency, company):
        return cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "pricelist_id": cls.product_pricelist.id,
                "currency_id": currency.id,
                "company_id": company.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product.name,
                            "product_id": cls.product.id,
                            "product_uom_qty": 1,
                            "product_uom": cls.product.uom_id.id,
                            "price_unit": 100.0,
                            "company_id": company.id,
                        },
                    )
                ],
            }
        )

    def test_sale_order(self):
        self.sale_order.action_confirm()
        self.assertAlmostEqual(self.partner.risk_sale_order, 115.0)
        self.assertFalse(self.partner.risk_exception)
        self.partner.risk_sale_order_limit = 99.0
        self.partner.risk_sale_order_include = True
        self.assertTrue(self.partner.risk_exception)
        sale_order2 = self.sale_order.copy()
        wiz_dic = sale_order2.action_confirm()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(wiz.exception_msg, "Financial risk exceeded.\n")
        self.partner.risk_sale_order_limit = 150.0
        wiz_dic = sale_order2.action_confirm()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(
            wiz.exception_msg, "This sale order exceeds the sales orders risk.\n"
        )
        self.partner.risk_sale_order_limit = 0.0
        self.partner.risk_sale_order_include = True
        self.partner.credit_limit = 100.0
        wiz_dic = sale_order2.action_confirm()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(wiz.exception_msg, "Financial risk exceeded.\n")
        self.assertTrue(self.partner.risk_allow_edit)
        wiz.button_continue()
        self.assertAlmostEqual(self.partner.risk_sale_order, 230.0)

    def test_sale_order_auto_done(self):
        self.env["ir.config_parameter"].create(
            {"key": "sale.auto_done_setting", "value": "True"}
        )
        self.env["ir.config_parameter"].create(
            {
                "key": "sale_financial_risk.include_risk_sale_order_done",
                "value": "True",
            }
        )
        self.sale_order.action_confirm()
        self.partner.risk_sale_order_include = True
        self.assertAlmostEqual(self.partner.risk_sale_order, 115.0)
        self.assertFalse(self.partner.risk_exception)
        self.partner.risk_sale_order_limit = 99.0
        self.assertTrue(self.partner.risk_exception)
        sale_order2 = self.sale_order.copy()
        wiz_dic = sale_order2.action_confirm()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(wiz.exception_msg, "Financial risk exceeded.\n")
        self.partner.risk_sale_order_limit = 150.0
        wiz_dic = sale_order2.action_confirm()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(
            wiz.exception_msg, "This sale order exceeds the sales orders risk.\n"
        )
        self.partner.risk_sale_order_limit = 0.0
        self.partner.risk_sale_order_include = True
        self.partner.credit_limit = 100.0
        wiz_dic = sale_order2.action_confirm()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(wiz.exception_msg, "Financial risk exceeded.\n")
        self.assertTrue(self.partner.risk_allow_edit)
        wiz.button_continue()
        self.assertAlmostEqual(self.partner.risk_sale_order, 230.0)

    def test_compute_risk_amount(self):
        self.sale_order.action_confirm()
        # Now the amount to be invoiced must 115
        self.assertEqual(self.partner.risk_sale_order, 115.0)
        self.assertFalse(self.partner.risk_exception)
        # If we set a risk_sale_order_limit to 99, risk_exception must be True
        self.partner.risk_sale_order_limit = 99.0
        self.partner.risk_sale_order_include = True
        self.assertTrue(self.partner.risk_exception)
        # If we create and validate an invoice from the sale order then the
        # amount to be invoiced must be 0 and risk_exception must be False
        inv_wiz = (
            self.env["sale.advance.payment.inv"]
            .with_context(**{"active_ids": [self.sale_order.id]})
            .create({})
        )
        inv_wiz.create_invoices()
        self.assertAlmostEqual(self.partner.risk_invoice_draft, 115.0)
        self.assertAlmostEqual(self.partner.risk_sale_order, 0)
        invoice = self.sale_order.invoice_ids
        invoice.with_context(bypass_risk=True).action_post()
        self.assertAlmostEqual(self.partner.risk_sale_order, 0)
        self.assertAlmostEqual(self.partner.risk_invoice_draft, 0.0)
        self.assertAlmostEqual(self.partner.risk_invoice_open, 115.0)
        self.assertFalse(self.partner.risk_exception)
        # After that, if we create and validate a Credit Note from the invoice
        # then the amount to be invoiced must be 100 again
        # and risk_exception must be True
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        ref_wiz_obj = self.env["account.move.reversal"].with_context(
            active_model="account.move", active_ids=[invoice.id]
        )
        ref_wiz = ref_wiz_obj.create({"reason": "testing", "journal_id": journal.id})
        res = ref_wiz.reverse_moves()
        self.assertAlmostEqual(self.partner.risk_invoice_draft, -115.0)
        self.assertAlmostEqual(self.partner.risk_sale_order, 115)
        # The way to re-invoice a sale order is creating a refund with
        # modify option and cancel or remove draft invoice
        modify_invoice = invoice.browse(res["res_id"])
        modify_invoice.unlink()
        self.assertAlmostEqual(self.partner.risk_sale_order, 0.0)
        line = self.sale_order.order_line[:1]
        line.product_uom_qty = 0.0
        self.assertAlmostEqual(line.risk_amount, 0.0)
        self.assertAlmostEqual(self.partner.risk_sale_order, 0.0)

    def test_open_risk_pivot_info(self):
        action = self.partner.with_context(
            open_risk_field="risk_sale_order"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "sale.order.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])

    def test_manual_currency_risk_not_exceeded(self):
        if self.env.company.currency_id == self.EUR:
            self.product_pricelist.currency_id = self.USD
            currency = self.USD
        else:
            self.product_pricelist.currency_id = self.EUR
            currency = self.EUR
        self.partner.write(
            {
                "risk_sale_order_limit": 99,
                "credit_limit": 99,
                "risk_sale_order_include": True,
                "credit_currency": "manual",
                "manual_credit_currency_id": self.main_currency.id,
            }
        )
        self.env["res.currency.rate"].create(
            {
                "currency_id": self.main_currency.id,
                "name": fields.Date.today(),
                "rate": 0.5,
                "company_id": self.env.company.id,
            }
        )
        sale_order = self.create_sale_order(currency=currency, company=self.env.company)
        result = sale_order.action_confirm()

        # Limit not exceeded
        self.assertEqual(result, True)

    def test_manual_currency_risk_exceeded(self):
        if self.env.company.currency_id == self.EUR:
            self.product_pricelist.currency_id = self.USD
            currency = self.USD
        else:
            self.product_pricelist.currency_id = self.EUR
            currency = self.EUR
        self.partner.write(
            {
                "risk_sale_order_limit": 99,
                "credit_limit": 99,
                "risk_sale_order_include": True,
                "credit_currency": "manual",
                "manual_credit_currency_id": self.main_currency.id,
            }
        )
        self.env["res.currency.rate"].create(
            {
                "currency_id": self.main_currency.id,
                "name": fields.Date.today(),
                "rate": 2.0,
                "company_id": self.env.company.id,
            }
        )
        sale_order = self.create_sale_order(currency=currency, company=self.env.company)
        result = sale_order.action_confirm()

        # Limit exceeded
        self.assertNotEqual(result, True)
        self.assertEqual(result["res_model"], "partner.risk.exceeded.wiz")
