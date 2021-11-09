# Copyright 2017-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form, common


class TestPartnerPaymentReturnRisk(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPartnerPaymentReturnRisk, cls).setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test Sales Journal", "code": "tVEN", "type": "sale"}
        )
        cls.account_type = cls.env["account.account.type"].create(
            {"name": "Test", "type": "receivable", "internal_group": "asset"}
        )
        cls.account = cls.env["account.account"].create(
            {
                "name": "Test account",
                "code": "TEST",
                "user_type_id": cls.account_type.id,
                "reconcile": True,
            }
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {"name": "Test Bank Journal", "code": "BANK", "type": "bank"}
        )
        cls.account_income = cls.env["account.account"].create(
            {
                "name": "Test income account",
                "code": "INCOME",
                "user_type_id": cls.env["account.account.type"]
                .create(
                    {"name": "Test income", "type": "other", "internal_group": "income"}
                )
                .id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test"})
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "journal_id": cls.journal.id,
                "company_id": cls.env.user.company_id.id,
                "currency_id": cls.env.user.company_id.currency_id.id,
                "partner_id": cls.partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account_income.id,
                            "name": "Test line",
                            "price_unit": 50,
                            "quantity": 10,
                        },
                    )
                ],
            }
        )
        cls.reason = cls.env["payment.return.reason"].create(
            {"code": "RTEST", "name": "Reason Test"}
        )
        cls.invoice.action_post()
        cls.receivable_line = cls.invoice.line_ids.filtered(
            lambda x: x.account_id.internal_type == "receivable"
        )
        # Create payment from invoice
        cls.payment_register_model = cls.env["account.payment.register"]
        payment_register = Form(
            cls.payment_register_model.with_context(
                active_model="account.move", active_ids=cls.invoice.ids
            )
        )
        cls.payment = payment_register.save()._create_payments()

        cls.payment_move = cls.payment.move_id

        cls.payment_line = cls.payment.move_id.line_ids.filtered(
            lambda x: x.account_id.internal_type == "receivable"
        )
        # Create payment return
        cls.payment_return = cls.env["payment.return"].create(
            {
                "journal_id": cls.bank_journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.partner.id,
                            "move_line_ids": [(6, 0, cls.payment_line.ids)],
                            "amount": cls.payment_line.credit,
                        },
                    )
                ],
            }
        )

    def test_payment_return_risk(self):
        self.assertAlmostEqual(self.partner.risk_payment_return, 0.0)
        self.payment_return.action_confirm()
        self.assertAlmostEqual(self.partner.risk_payment_return, 500.0)
        self.payment_return.action_cancel()
        self.assertAlmostEqual(self.partner.risk_payment_return, 0.0)

    def test_open_risk_pivot_info(self):
        action = self.partner.with_context(
            open_risk_field="risk_payment_return"
        ).open_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertTrue(action["view_id"])
        self.assertTrue(action["domain"])
