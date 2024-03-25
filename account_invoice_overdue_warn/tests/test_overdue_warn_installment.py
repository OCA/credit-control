# Copyright 2024 Engenere.one
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime, timedelta

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOverdueWarn(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "country_id": self.env.ref("base.br").id,
                "company_id": self.company.id,
            }
        )
        self.today = datetime.now().date()
        self.revenue_acc = self.env["account.account"].search(
            [
                ("company_id", "=", self.company.id),
                (
                    "user_type_id",
                    "=",
                    self.env.ref("account.data_account_type_revenue").id,
                ),
            ],
            limit=1,
        )

        self.payment_term = self.env["account.payment.term"].create(
            {
                "name": "Immediate payment",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "balance",
                            "days": 0,
                        },
                    ),
                ],
            }
        )

        self.payment_term_installments_a = self.env["account.payment.term"].create(
            {
                "name": "Pay in 3 installments",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 33.33,
                            "days": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 33.33,
                            "days": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "balance",
                            "days": 0,
                        },
                    ),
                ],
            }
        )

        self.payment_term_installments_b = self.env["account.payment.term"].create(
            {
                "name": "Pay in 3 installments",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 33.33,
                            "days": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 33.33,
                            "days": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "balance",
                            "days": 14,
                        },
                    ),
                ],
            }
        )

    def test_out_invoice_draft(self):
        out_invoice_draft = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": self.today - timedelta(days=9),
                "invoice_payment_term_id": self.payment_term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product Test",
                            "price_unit": 500,
                            "quantity": 1,
                            "account_id": self.revenue_acc.id,
                        },
                    )
                ],
            }
        )
        self.assertEqual(
            out_invoice_draft.invoice_date_due,
            out_invoice_draft.line_ids[1].date_maturity,
        )
        self.assertEqual(out_invoice_draft.state, "draft")
        self.assertEqual(self.partner.overdue_invoice_count, 0)
        self.assertEqual(self.partner.overdue_invoice_amount, 0.0)

    def test_confirmed_supplier_invoice(self):
        out_invoice_supplier = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "in_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": self.today - timedelta(days=9),
                "invoice_payment_term_id": self.payment_term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product Test",
                            "price_unit": 500,
                            "quantity": 1,
                            "account_id": self.revenue_acc.id,
                        },
                    )
                ],
            }
        )
        out_invoice_supplier.action_post()
        self.assertEqual(
            out_invoice_supplier.invoice_date_due,
            out_invoice_supplier.line_ids[1].date_maturity,
        )
        self.assertEqual(self.partner.overdue_invoice_count, 0)
        self.assertEqual(self.partner.overdue_invoice_amount, 0.0)

    def test_mixed_case_with_two_invoices(self):

        out_invoice_a = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": self.today - timedelta(days=10),
                "invoice_payment_term_id": self.payment_term_installments_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product Test",
                            "price_unit": 900,
                            "quantity": 1,
                            "account_id": self.revenue_acc.id,
                        },
                    ),
                ],
            }
        )
        out_invoice_a.action_post()

        out_invoice_b = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": self.today - timedelta(days=10),
                "invoice_payment_term_id": self.payment_term_installments_b.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product Test",
                            "price_unit": 900,
                            "quantity": 1,
                            "account_id": self.revenue_acc.id,
                        },
                    ),
                ],
            }
        )
        out_invoice_b.action_post()

        action_data_a = out_invoice_a.action_register_payment()
        wizard_a = Form(
            self.env["account.payment.register"].with_context(action_data_a["context"])
        ).save()
        wizard_a.amount = 450.0
        wizard_a.action_create_payments()

        self.assertEqual(
            out_invoice_b.invoice_date_due,
            out_invoice_b.line_ids[3].date_maturity,
        )
        self.assertEqual(self.partner.overdue_invoice_count, 2)
        self.assertEqual(self.partner.overdue_invoice_amount, 1049.94)

    def test_confirmed_invoice_with_past_date(self):
        out_invoice_past_paid = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": self.today - timedelta(days=5),
                "invoice_payment_term_id": self.payment_term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product Test",
                            "price_unit": 500.0,
                            "quantity": 1,
                            "account_id": self.revenue_acc.id,
                        },
                    )
                ],
            }
        )
        out_invoice_past_paid.action_post()
        action_data = out_invoice_past_paid.action_register_payment()
        wizard = Form(
            self.env["account.payment.register"].with_context(action_data["context"])
        ).save()
        wizard.action_create_payments()
        self.assertEqual(
            out_invoice_past_paid.invoice_date_due,
            out_invoice_past_paid.line_ids[1].date_maturity,
        )
        self.assertEqual(self.partner.overdue_invoice_count, 0)
        self.assertEqual(self.partner.overdue_invoice_amount, 0)

    def test_confirmed_invoice_with_future_date_unpaid(self):
        out_invoice_future = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": self.today + timedelta(days=5),
                "invoice_payment_term_id": self.payment_term.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product Test",
                            "price_unit": 500,
                            "quantity": 1,
                            "account_id": self.revenue_acc.id,
                        },
                    )
                ],
            }
        )
        out_invoice_future.action_post()
        self.assertEqual(
            out_invoice_future.invoice_date_due,
            out_invoice_future.line_ids[1].date_maturity,
        )
        self.assertEqual(self.partner.overdue_invoice_count, 0)
        self.assertEqual(self.partner.overdue_invoice_amount, 0)
