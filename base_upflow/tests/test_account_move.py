from odoo.tests.common import SavepointCase
from odoo.tools import mute_logger

from .common import AccountingCommonCase


class TestAccountMove(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test partner", "email": "email@example.co"}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test journal", "type": "sale", "code": "TEST"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test product", "type": "service"}
        )
        cls.account_user_type = cls.env["account.account.type"].create(
            {
                "name": "Test account type",
                "type": "receivable",
                "internal_group": "asset",
            }
        )
        cls.account = cls.env["account.account"].create(
            {
                "name": "Test account",
                "code": "TEST",
                "user_type_id": cls.account_user_type.id,
                "reconcile": True,
            }
        )
        cls.entry_move = cls.env["account.move"].create(
            {
                "journal_id": cls.journal.id,
                "move_type": "entry",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account.id,
                            "partner_id": cls.partner.id,
                            "name": "Test entry",
                            "debit": 0,
                            "credit": 0,
                        },
                    )
                ],
            }
        )
        cls.account_move = cls.env["account.move"].create(
            {
                "journal_id": cls.journal.id,
                "partner_id": cls.partner.id,
                "move_type": "out_invoice",
            }
        )

    def test_compute_upflow_commercial_partner_id_entry(self):
        self.assertEqual(
            self.entry_move.upflow_commercial_partner_id,
            self.partner.commercial_partner_id,
        )

    def test_compute_upflow_commercial_partner_id_invoice(self):
        self.assertEqual(
            self.account_move.upflow_commercial_partner_id,
            self.partner.commercial_partner_id,
        )


class TestAccountMoveUpflowType(SavepointCase, AccountingCommonCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_accounting()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "My customer company",
                "is_company": True,
                "vat": "FR23334175221",
                "street": "Street 1",
                "street2": "and more",
                "zip": "45500",
                "city": "Customer city",
            }
        )
        cls.invoice = cls._create_invoice()
        cls.refund = cls._create_invoice(move_type="out_refund")
        cls.purchase_invoice = cls._create_invoice(move_type="in_invoice")
        cls.payment_bnk_stmt = cls._make_credit_transfer_payment_reconciled(cls.invoice)

    def test_compute_upflow_type_draft(self):
        self.assertEqual(self.invoice.upflow_type, "none")
        self.assertEqual(self.refund.upflow_type, "none")
        self.assertEqual(self.purchase_invoice.upflow_type, "none")

    def test_compute_upflow_type_invoices(self):
        self.invoice.action_post()
        self.assertEqual(self.invoice.upflow_type, "invoices")

    def test_compute_upflow_type_credit_notes(self):
        self.refund.action_post()
        self.assertEqual(self.refund.upflow_type, "creditNotes")

    def test_payment_by_bank_statment(self):
        self.assertEqual(self.payment_bnk_stmt.upflow_type, "payments")

    def test_customer_payment_from_bank_statement(self):
        self.refund.action_post()
        payment_bnk_stmt = self._make_credit_transfer_payment_reconciled(
            self.refund,
            amount=-self.refund.amount_residual,
            reconcile_param=[
                {
                    "id": self.refund.line_ids.filtered(
                        lambda line: line.account_internal_type
                        in ("receivable", "payable")
                    ).id
                }
            ],
        )
        self.assertEqual(payment_bnk_stmt.upflow_type, "refunds")

    def test_customer_payment_manual_payment(self):
        self.refund.action_post()
        move = self._register_manual_payment_reconciled(self.refund)
        self.assertEqual(move.upflow_type, "refunds")

    def test_bank_statment_not_reconciled(self):
        # at that time we don't know yet if payment entry is related to
        # payment refunds or paid purchase invoice

        (
            bank_journal,
            _method,
            payment_date,
            amount,
            _currency,
        ) = self._payment_params(
            self.invoice,
        )
        bank_stmt = self.env["account.bank.statement"].create(
            {
                "journal_id": bank_journal.id,
                "date": payment_date,
                "name": "payment",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "payment_ref": "payment",
                            "partner_id": self.partner.id,
                            "amount": -amount,
                        },
                    )
                ],
            }
        )
        bank_stmt.button_post()
        self.assertEqual(bank_stmt.line_ids[0].move_id.upflow_type, "none")

    def test_no_receivable_lines(self):
        self.purchase_invoice.action_post()
        self.assertEqual(self.purchase_invoice.upflow_type, "none")

    @mute_logger("odoo.addons.base_upflow.models.account_move")
    def test_receivables_null(self):

        account_user_type = self.env["account.account.type"].create(
            {
                "name": "Test account type",
                "type": "receivable",
                "internal_group": "asset",
            }
        )
        account = self.env["account.account"].create(
            {
                "name": "Test account",
                "code": "TEST",
                "user_type_id": account_user_type.id,
                "reconcile": True,
            }
        )
        entry_move = self.env["account.move"].create(
            {
                "journal_id": self.invoice.journal_id.id,
                "move_type": "entry",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": account.id,
                            "partner_id": self.partner.id,
                            "name": "Test entry",
                            "debit": 0,
                            "credit": 0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": account.id,
                            "partner_id": self.partner.id,
                            "name": "Test entry",
                            "debit": 0,
                            "credit": 0,
                        },
                    ),
                ],
            }
        )
        entry_move.action_post()
        self.assertEquals(entry_move.upflow_type, "none")
