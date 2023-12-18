import time
from unittest import TestCase


class AccountingCommonCase(TestCase):
    """Provide utilities to test accounting

    Those utility shouldn't not assume what's installed or not
    in the database to make determinist unit test whatever
    installed data
    """

    @classmethod
    def _setup_accounting(cls):
        main_company = cls.env.ref("base.main_company")
        assert (
            main_company.chart_template_id
            and cls.env["account.journal"].search_count([]) > 0
        ), "This test require an account chart to be installed"
        cls.pay_terms_multiple = cls.env["account.payment.term"].create(
            {
                "name": "30% Advance End of Following Month",
                "note": "Payment terms: 30% Advance End of Following Month",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value": "percent",
                            "value_amount": 30.0,
                            "sequence": 400,
                            "days": 0,
                            "option": "day_after_invoice_date",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value": "balance",
                            "value_amount": 0.0,
                            "sequence": 500,
                            "days": 31,
                            "option": "day_following_month",
                        },
                    ),
                ],
            }
        )

    @classmethod
    def _create_invoice(
        cls,
        move_type="out_invoice",
        unit_price=50,
        currency_id=None,
        partner_id=None,
        date_invoice=None,
        payment_term_id=False,
        auto_validate=False,
        vat_ids=None,
    ):
        """Code overwrite from
        odoo.addons.account.tests.common.TestAccountReconciliationCommon._create_invoice
        with following supper:

        * Allow to set VAT
        """
        if not vat_ids:
            vat_ids = (
                cls.env["account.tax"]
                .search(
                    [
                        ("type_tax_use", "=", "sale"),
                        ("amount", "!=", 0),
                        ("company_id", "=", cls.env.company.id),
                    ],
                    limit=1,
                )
                .ids
            )
        date_invoice = date_invoice or time.strftime("%Y") + "-07-01"

        invoice_vals = {
            "move_type": move_type,
            "partner_id": partner_id or cls.partner,
            "invoice_date": date_invoice,
            "date": date_invoice,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": "product with unit price %s" % unit_price,
                        "quantity": 1,
                        "price_unit": unit_price,
                        "tax_ids": [(6, 0, vat_ids)],
                    },
                )
            ],
        }

        if payment_term_id:
            invoice_vals["invoice_payment_term_id"] = payment_term_id

        if currency_id:
            invoice_vals["currency_id"] = currency_id

        invoice = (
            cls.env["account.move"]
            .with_context(default_move_type=move_type)
            .create(invoice_vals)
        )
        if auto_validate:
            invoice.action_post()
        return invoice

    @classmethod
    def _payment_params(
        cls,
        account_move,
        bank_journal=None,
        method=None,
        payment_date=None,
        amount=None,
        currency=None,
    ):
        if not bank_journal:
            bank_journal = cls.env["account.journal"].search(
                [
                    ("type", "=", "bank"),
                    ("company_id", "=", cls.env.company.id),
                ],
                limit=1,
            )
        if not method:
            method = cls.env.ref("account.account_payment_method_manual_in")
        if not payment_date:
            payment_date = account_move.invoice_date_due
        if not amount:
            amount = account_move.amount_residual
        if not currency:
            currency = account_move.currency_id
        return bank_journal, method, payment_date, amount, currency

    @classmethod
    def _make_credit_transfer_payment_reconciled(
        cls,
        invoice,
        bank_journal=None,
        payment_date=None,
        amount=None,
        reconcile_param=None,
        partner=None,
    ):
        """payment registered by from bank statement reconciliation

        :param partner: False value means not set while None means get partner from invoice
        """
        (bank_journal, _method, payment_date, amount, _currency,) = cls._payment_params(
            invoice,
            bank_journal=bank_journal,
            method=None,
            payment_date=payment_date,
            amount=amount,
            currency=None,
        )
        if not reconcile_param:
            reconcile_param = []
        # make difference between partner is False and partner is None
        if partner is None:
            partner = invoice.partner_id
        bank_stmt = cls.env["account.bank.statement"].create(
            {
                "journal_id": bank_journal.id,
                "date": payment_date,
                "name": "payment" + invoice.name,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "payment_ref": "payment",
                            "partner_id": partner.id if partner else False,
                            "amount": amount,
                            # "amount_currency": amount,
                            # "foreign_currency_id": currency.id,
                        },
                    )
                ],
            }
        )
        bank_stmt.button_post()

        bank_stmt.line_ids[0].reconcile(reconcile_param)
        return bank_stmt.line_ids[0].move_id

    @classmethod
    def _register_manual_payment_reconciled(
        cls,
        account_move,
        payment_type="inbound",
        bank_journal=None,
        method=None,
        payment_date=None,
        amount=None,
        currency=None,
    ):
        bank_journal, method, payment_date, amount, currency = cls._payment_params(
            account_move,
            bank_journal=bank_journal,
            method=method,
            payment_date=payment_date,
            amount=amount,
            currency=currency,
        )
        payment_wiz = cls.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=[account_move.id]
        )
        return (
            payment_wiz.create(
                {
                    "payment_type": payment_type,
                    "amount": amount,
                    "payment_method_id": method.id,
                    "payment_date": payment_date,
                    "journal_id": bank_journal.id,
                    "currency_id": currency.id,
                    # "partner_type": "customer",
                    "partner_id": account_move.partner_id.id,
                }
            )
            ._create_payments()
            .move_id
        )
