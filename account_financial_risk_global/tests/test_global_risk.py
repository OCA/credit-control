# Copyright 2026 Graeme Gellatly
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields

from odoo.addons.base.tests.common import BaseCommon


class TestGlobalRisk(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref(
            "account_financial_risk.group_account_financial_risk_manager"
        )
        cls.company_a = cls.company
        cls.company_b = cls.env["res.company"].create(
            {
                "name": "Company B",
                "currency_id": cls.company_a.currency_id.id,
            }
        )
        cls.env.user.company_ids |= cls.company_b

        cls.account_sale_a = cls.env["account.account"].create(
            {
                "name": "Sale A",
                "code": "GR700A",
                "account_type": "income_other",
                "company_ids": [Command.set([cls.company_a.id])],
            }
        )
        cls.account_recv_a = cls.env["account.account"].create(
            {
                "name": "Receivable A",
                "code": "GR430A",
                "account_type": "asset_receivable",
                "reconcile": True,
                "company_ids": [Command.set([cls.company_a.id])],
            }
        )
        cls.journal_a = cls.env["account.journal"].create(
            {
                "name": "Sales A",
                "type": "sale",
                "code": "GRA",
                "company_id": cls.company_a.id,
            }
        )
        cls.account_sale_b = (
            cls.env["account.account"]
            .with_company(cls.company_b)
            .create(
                {
                    "name": "Sale B",
                    "code": "GR700B",
                    "account_type": "income_other",
                    "company_ids": [Command.set([cls.company_b.id])],
                }
            )
        )
        cls.account_recv_b = (
            cls.env["account.account"]
            .with_company(cls.company_b)
            .create(
                {
                    "name": "Receivable B",
                    "code": "GR430B",
                    "account_type": "asset_receivable",
                    "reconcile": True,
                    "company_ids": [Command.set([cls.company_b.id])],
                }
            )
        )
        cls.journal_b = (
            cls.env["account.journal"]
            .with_company(cls.company_b)
            .create(
                {
                    "name": "Sales B",
                    "type": "sale",
                    "code": "GRB",
                    "company_id": cls.company_b.id,
                }
            )
        )

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Global Risk Partner",
                "customer_rank": 1,
                "property_account_receivable_id": cls.account_recv_a.id,
            }
        )

        cls.invoice_a = (
            cls.env["account.move"]
            .with_context(default_move_type="out_invoice")
            .create(
                {
                    "partner_id": cls.partner.id,
                    "journal_id": cls.journal_a.id,
                    "invoice_payment_term_id": False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Product A",
                                "account_id": cls.account_sale_a.id,
                                "price_unit": 600,
                                "quantity": 1,
                            }
                        )
                    ],
                }
            )
        )

        cls.invoice_b = (
            cls.env["account.move"]
            .with_company(cls.company_b)
            .with_context(default_move_type="out_invoice")
            .create(
                {
                    "partner_id": cls.partner.id,
                    "journal_id": cls.journal_b.id,
                    "invoice_payment_term_id": False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Product B",
                                "account_id": cls.account_sale_b.id,
                                "price_unit": 600,
                                "quantity": 1,
                            }
                        )
                    ],
                }
            )
        )

    def test_risk_domain_is_global(self):
        """_get_risk_company_domain should return a truthy-for-all domain."""
        domain = self.partner._get_risk_company_domain()
        self.assertTrue(domain.is_true())

    def test_risk_totals_span_companies(self):
        """Draft invoices in two companies should both count toward risk."""
        self.partner.risk_invoice_draft_include = True
        self.partner.invalidate_recordset()
        self.assertAlmostEqual(self.partner.risk_invoice_draft, 1200.0)
        self.assertAlmostEqual(self.partner.risk_total, 1200.0)

    def test_exception_triggered_globally(self):
        """Credit limit exceeded only when both companies' amounts are combined."""
        self.partner.risk_invoice_draft_include = True
        self.partner.credit_limit = 1000.0
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.risk_exception)
        self.assertAlmostEqual(self.partner.risk_amount_exceeded, 200.0)

    def test_no_exception_within_limit(self):
        """No exception when global total stays within credit limit."""
        self.partner.risk_invoice_draft_include = True
        self.partner.credit_limit = 1500.0
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.risk_exception)

    def test_posted_invoices_span_companies(self):
        """Posted invoices across companies should count in risk total."""
        self.invoice_a.action_post()
        self.invoice_b.action_post()
        self.invoice_a.line_ids.filtered("debit").write(
            {"date_maturity": fields.Date.today()}
        )
        self.invoice_b.line_ids.filtered("debit").write(
            {"date_maturity": fields.Date.today()}
        )
        self.partner.risk_invoice_open_include = True
        self.partner.risk_account_amount_include = True
        self.partner.invalidate_recordset()
        self.assertAlmostEqual(self.partner.risk_invoice_open, 600.0)
        self.assertAlmostEqual(self.partner.risk_account_amount, 600.0)
        self.partner.credit_limit = 1000.0
        self.assertTrue(self.partner.risk_exception)

    def test_single_company_user_still_sees_global_risk(self):
        """A user with access to only one company should still see full risk."""
        self.partner.risk_invoice_draft_include = True
        self.partner.credit_limit = 1000.0
        user_a = self.env.user.copy(
            {
                "login": "user_a_only",
                "company_id": self.company_a.id,
                "company_ids": [Command.set([self.company_a.id])],
            }
        )
        user_a.group_ids |= self.env.ref(
            "account_financial_risk.group_account_financial_risk_manager"
        )
        partner_as_a = self.partner.with_user(user_a)
        partner_as_a.invalidate_recordset()
        self.assertAlmostEqual(partner_as_a.risk_invoice_draft, 1200.0)
        self.assertTrue(partner_as_a.risk_exception)
