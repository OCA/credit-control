# Copyright 2016-2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase


class TestPartnerFinancialRisk(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPartnerFinancialRisk, cls).setUpClass()
        cls.env.user.groups_id |= cls.env.ref(
            "account_financial_risk.group_account_financial_risk_manager"
        )
        type_revenue = cls.env.ref("account.data_account_type_revenue")
        type_receivable = cls.env.ref("account.data_account_type_receivable")
        tax_group_taxes = cls.env.ref("account.tax_group_taxes")
        main_company = cls.env.ref("base.main_company")
        cls.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            [cls.env.ref("base.USD").id, main_company.id],
        )
        cls.account_sale = cls.env["account.account"].create(
            {
                "name": "Sale",
                "code": "XX_700",
                "user_type_id": type_revenue.id,
                "reconcile": True,
            }
        )
        cls.account_customer = cls.env["account.account"].create(
            {
                "name": "Customer",
                "code": "XX_430",
                "user_type_id": type_receivable.id,
                "reconcile": True,
            }
        )
        cls.other_account_customer = cls.env["account.account"].create(
            {
                "name": "Other Account Customer",
                "code": "XX_431",
                "user_type_id": type_receivable.id,
                "reconcile": True,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Partner test",
                "customer_rank": 1,
                "property_account_receivable_id": cls.account_customer.id,
                "company_id": cls.account_customer.company_id.id,
            }
        )
        cls.invoice_address = cls.env["res.partner"].create(
            {
                "name": "Partner test invoice",
                "parent_id": cls.partner.id,
                "type": "invoice",
            }
        )
        cls.journal_sale = cls.env["account.journal"].create(
            {
                "name": "Test journal for sale",
                "type": "sale",
                "code": "TSALE",
                "company_id": cls.env.company.id,
            }
        )
        cls.tax = cls.env["account.tax"].create(
            {
                "name": "Tax for sale 10%",
                "type_tax_use": "sale",
                "tax_group_id": tax_group_taxes.id,
                "amount_type": "percent",
                "amount": 10.0,
            }
        )
        cls.invoice = (
            cls.env["account.move"]
            .with_context(default_move_type="out_invoice")
            .create(
                {
                    "partner_id": cls.partner.id,
                    "journal_id": cls.journal_sale.id,
                    "invoice_payment_term_id": False,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Test product",
                                "account_id": cls.account_sale.id,
                                "price_unit": 50,
                                "quantity": 10,
                                "tax_ids": [(6, 0, [cls.tax.id])],
                            },
                        )
                    ],
                }
            )
        )
        cls.env.user.lang = False

    def test_invoices(self):
        self.partner.risk_invoice_draft_include = True
        self.assertAlmostEqual(self.partner.risk_invoice_draft, 550.0)
        self.assertAlmostEqual(self.partner.risk_total, 550.0)
        self.invoice._post()
        self.assertAlmostEqual(self.partner.risk_invoice_draft, 0.0)
        line = self.invoice.line_ids.filtered(lambda x: x.debit != 0.0)
        line.date_maturity = "2017-01-01"
        self.partner.risk_invoice_unpaid_include = True
        self.assertAlmostEqual(self.partner.risk_total, 550.0)
        self.partner.credit_limit = 100.0
        self.assertTrue(self.partner.risk_exception)
        self.partner.credit_limit = 1100.0
        self.assertFalse(self.partner.risk_exception)
        self.partner.risk_invoice_unpaid_limit = 499.0
        self.assertTrue(self.partner.risk_exception)
        except_partners = self.partner.search([("risk_exception", "=", True)])
        self.assertIn(self.partner, except_partners)
        invoice2 = self.invoice.copy({"partner_id": self.invoice_address.id})
        self.assertAlmostEqual(self.partner.risk_invoice_draft, 550.0)
        self.assertAlmostEqual(self.partner.risk_invoice_unpaid, 550.0)
        wiz_dic = invoice2.action_post()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(wiz.exception_msg, "Financial risk exceeded.\n")
        self.partner.risk_invoice_unpaid_limit = 0.0
        self.assertFalse(self.partner.risk_exception)
        unrisk_partners = self.partner.search([("risk_exception", "=", False)])
        self.assertIn(self.partner, unrisk_partners)
        self.partner.risk_invoice_open_limit = 300.0
        invoice2.invoice_date_due = fields.Date.today()
        wiz_dic = invoice2.action_post()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(
            wiz.exception_msg, "This invoice exceeds the open invoices risk.\n"
        )
        self.partner.risk_invoice_open_limit = 0.0
        self.partner.risk_invoice_draft_include = False
        self.partner.risk_invoice_open_include = True
        self.partner.credit_limit = 900.0
        wiz_dic = invoice2.action_post()
        wiz = self.env[wiz_dic["res_model"]].browse(wiz_dic["res_id"])
        self.assertEqual(
            wiz.exception_msg, "This invoice exceeds the financial risk.\n"
        )
        self.assertAlmostEqual(self.partner.risk_invoice_open, 0.0)
        wiz.button_continue()
        # HACK: Force the maturity date for not having an error here
        invoice2.line_ids.write({"date_maturity": fields.Date.today()})
        self.assertAlmostEqual(self.partner.risk_invoice_open, 550.0)
        self.assertTrue(self.partner.risk_allow_edit)

    def test_other_account_amount(self):
        self.move = (
            self.env["account.move"]
            .with_context(default_move_type="entry")
            .create(
                {
                    "journal_id": self.journal_sale.id,
                    "date": fields.Date.today(),
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Debit line",
                                "partner_id": self.partner.id,
                                "account_id": self.other_account_customer.id,
                                "debit": 100,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": "Credit line",
                                "partner_id": self.partner.id,
                                "account_id": self.account_sale.id,
                                "credit": 100,
                            },
                        ),
                    ],
                }
            )
        )
        self.move.action_post()
        self.assertAlmostEqual(self.partner.risk_account_amount, 100.0)
        line = self.move.line_ids.filtered(lambda x: x.debit != 0.0)
        line.date_maturity = "2017-01-01"
        self.assertAlmostEqual(self.partner.risk_account_amount, 0.0)
        self.assertAlmostEqual(self.partner.risk_account_amount_unpaid, 100.0)
        line.date_maturity = fields.Date.today() - relativedelta(days=2)
        self.assertAlmostEqual(self.partner.risk_account_amount, 0.0)
        self.assertAlmostEqual(self.partner.risk_account_amount_unpaid, 100.0)
        line.company_id.invoice_unpaid_margin = 3
        self.assertAlmostEqual(self.partner.risk_account_amount, 100.0)
        self.assertAlmostEqual(self.partner.risk_account_amount_unpaid, 0.0)
        # Test pop vals write
        line.company_id.invoice_unpaid_margin = 3

    def test_recompute_newid(self):
        """Computing risk shouldn't fail if record is a NewId."""
        new = self.env["res.partner"].new({})
        new._compute_risk_account_amount()

    def test_batch_invoice_confirm(self):
        self.invoice.action_post()
        line = self.invoice.line_ids.filtered(lambda x: x.debit != 0.0)
        line.date_maturity = "2017-01-01"
        self.partner.risk_invoice_unpaid_include = True
        self.partner.credit_limit = 100.0
        invoice2 = self.invoice.copy({"partner_id": self.invoice_address.id})
        validate_wiz = (
            self.env["validate.account.move"]
            .with_context(active_model="account.move", active_ids=invoice2.ids)
            .create({})
        )
        with self.assertRaises(ValidationError):
            invoice2.action_post()
            validate_wiz.validate_move()
        self.assertEqual(invoice2.state, "draft")

    def test_open_risk_pivot_info(self):
        action = self.partner.with_context(
            open_risk_field="risk_invoice_draft"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])

        action = self.partner.with_context(
            open_risk_field="risk_invoice_open"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])

        action = self.partner.with_context(
            open_risk_field="risk_invoice_unpaid"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])

        action = self.partner.with_context(
            open_risk_field="risk_account_amount"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])

        action = self.partner.with_context(
            open_risk_field="risk_account_amount_unpaid"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])

    def test_invoice_risk_draft_same_currency(self):
        self.partner.risk_invoice_draft_include = True
        self.invoice.currency_id = self.env.ref("base.USD")
        self.partner.credit_limit = 100.0
        self.assertGreater(self.partner.risk_total, self.partner.credit_limit)
        self.assertTrue(
            self.partner.risk_total, self.invoice.risk_amount_total_currency
        )
        self.assertTrue(
            self.partner.risk_amount_exceeded,
            self.partner.risk_total - self.partner.credit_limit,
        )

    def test_invoice_risk_draft_different_currency(self):
        self.partner.risk_invoice_draft_include = True
        self.invoice.currency_id = self.env.ref("base.EUR")
        self.partner.credit_limit = 100.0
        self.assertGreater(self.partner.risk_total, self.partner.credit_limit)
        self.assertTrue(
            self.partner.risk_total, self.invoice.risk_amount_total_currency
        )
        self.assertTrue(
            self.partner.risk_amount_exceeded,
            self.partner.risk_total - self.partner.credit_limit,
        )
