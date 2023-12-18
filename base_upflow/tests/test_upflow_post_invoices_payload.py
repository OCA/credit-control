# Copyright 2022 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json
import os
from uuid import uuid4

from jsonschema import validate

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase, tagged

from .common import AccountingCommonCase

SCHEMA_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    "json_schema",
)


@tagged("post_install", "-at_install")
class UpflowAccountMovePayloadTest(SavepointCase, AccountingCommonCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_accounting()
        cls.customer_company = cls.env["res.partner"].create(
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
        cls.contact = cls.env["res.partner"].create(
            {
                "name": "Jack Flag",
                "parent_id": cls.customer_company.id,
                "phone": "+33238365503",
                "mobile": "+33604060810",
                "email": "jack.flag@customer-company.com",
                "upflow_position_id": cls.env.ref(
                    "base_upflow.upflow_res_partner_upflow_position_accounting"
                ).id,
            }
        )
        cls.customer_company2 = cls.env["res.partner"].create(
            {
                "name": "My customer company2",
                "is_company": True,
                "vat": "FR23334175221",
                "street": "Street 1",
                "street2": "and more",
                "zip": "45500",
                "city": "Customer city",
            }
        )
        cls.contact_without_name = cls.env["res.partner"].create(
            {
                "name": False,
                "type": "other",  # name is mandatory for type "contact"
                "parent_id": cls.customer_company2.id,
                "email": "noname@customer-company.com",
            }
        )
        cls.customer_company3 = cls.env["res.partner"].create(
            {
                "name": "My customer company3",
                "is_company": True,
                "vat": "FR23334175221",
                "street": "Street 1",
                "street2": "and more",
                "zip": "45500",
                "city": "Customer city",
            }
        )
        cls.contact_with_spacename = cls.env["res.partner"].create(
            {
                "name": " ",
                "type": "other",  # name is mandatory for type "contact"
                "parent_id": cls.customer_company3.id,
                "email": "spacename@customer-company.com",
            }
        )
        cls.invoice = cls._create_invoice(
            date_invoice="2022-01-01",
            partner_id=cls.contact.id,
            payment_term_id=cls.pay_terms_multiple.id,
            auto_validate=True,
        )
        cls.refund = cls._create_invoice(
            date_invoice="2022-01-01",
            partner_id=cls.contact.id,
            move_type="out_refund",
            auto_validate=True,
        )
        cls.refund_payment_move = cls._register_manual_payment_reconciled(cls.refund)

    def assertValidUpflowPayload(self, schema_file_name, content):
        validate(
            schema=json.loads(
                open(f"{SCHEMA_DIRECTORY}/{schema_file_name}.json").read()
            ),
            instance=content,
        )

    def test_upflow_uuid_not_duplicate(self):
        self.invoice.upflow_uuid = str(uuid4())
        invoice2 = self.invoice.copy()
        self.assertFalse(invoice2.upflow_uuid)
        self.assertNotEqual(self.invoice.upflow_uuid, invoice2.upflow_uuid)

    def test_upflow_direct_url_not_duplicate(self):
        self.invoice.upflow_direct_url = "/invoice/1234"
        invoice2 = self.invoice.copy()
        self.assertFalse(invoice2.upflow_direct_url)
        self.assertNotEqual(self.invoice.upflow_direct_url, invoice2.upflow_direct_url)

    def test_post_invocies_pdf_format(self):
        self.assertValidUpflowPayload(
            "post-pdf",
            self.invoice.get_upflow_api_pdf_payload(),
        )

    def test_post_invocies_format(self):
        self.assertValidUpflowPayload(
            "post-invoices",
            self.invoice.get_upflow_api_post_invoice_payload(),
        )

    def test_post_invoice_payload_add_upflow_id_if_present(self):
        uuid = str(uuid4())
        self.invoice.upflow_uuid = uuid
        payload = self.invoice.get_upflow_api_post_invoice_payload()
        self.assertEqual(payload["id"], uuid)

    def test_get_upflow_api_post_invoices_payload_content(self):
        content = self.invoice.get_upflow_api_post_invoice_payload()
        self.assertEqual(content["customId"], self.invoice.name)
        self.assertEqual(content["externalId"], str(self.invoice.id))
        self.assertEqual(content["issuedAt"], "2022-01-01")
        self.assertEqual(content["dueDate"], "2022-02-28")
        self.assertEqual(content["name"], self.invoice.name)
        self.assertEqual(content["currency"], self.invoice.currency_id.name)
        self.assertNotEqual(content["grossAmount"], content["netAmount"])
        self.assertAlmostEqual(
            content["grossAmount"],
            self.invoice.amount_total * 1 / self.invoice.currency_id.rounding,
        )
        self.assertAlmostEqual(
            content["netAmount"],
            self.invoice.amount_untaxed * 1 / self.invoice.currency_id.rounding,
        )
        self.assertEqual(
            content["customer"]["externalId"],
            str(self.customer_company.id),
        )

    def test_get_upflow_api_post_customers_payload_format(self):
        self.assertValidUpflowPayload(
            "post-customers",
            self.customer_company.get_upflow_api_post_customers_payload(),
        )

    def test_get_upflow_api_post_customers_without_vat_payload_format(self):
        self.customer_company.vat = False
        self.assertValidUpflowPayload(
            "post-customers",
            self.customer_company.get_upflow_api_post_customers_payload(),
        )

    def test_post_customers_payload_only_contact_with_email_are_send(self):
        self.env["res.partner"].create(
            {
                "name": "Someone else without email",
                "parent_id": self.customer_company.id,
                "phone": "+33238365503",
                "mobile": "+33604060810",
                "email": False,
            }
        )
        payload = self.customer_company.get_upflow_api_post_customers_payload()
        self.assertEqual(len(payload["contacts"]), 1)
        self.assertEqual(payload["contacts"][0]["firstName"], self.contact.name)

    def test_post_contact_phone_field_not_define(self):
        self.contact.mobile = False
        payload = self.contact.get_upflow_api_post_contacts_payload()
        self.assertEqual(payload["phone"], "")

    def test_post_customers_streets_field_not_define(self):
        # the address field is required by upflow but here we want
        # to make sure if one is missing it's not replaced by `False` text
        self.customer_company.street = False
        self.customer_company.street2 = False
        payload = self.customer_company.get_upflow_api_post_customers_payload()
        self.assertEqual(payload["address"]["address"], "")

    def test_post_customers_payload_add_upflow_id_if_present(self):
        uuid = str(uuid4())
        self.customer_company.commercial_partner_id.upflow_uuid = uuid
        payload = self.customer_company.get_upflow_api_post_customers_payload()
        self.assertEqual(payload["id"], uuid)

    def test_get_upflow_api_post_customers_payload_content(self):
        content = self.customer_company.get_upflow_api_post_customers_payload()
        self.assertEqual(content["name"], "My customer company")
        self.assertEqual(content["vatNumber"], "FR23334175221")
        self.assertEqual(content["externalId"], str(self.customer_company.id))
        self.assertEqual(content["address"]["address"], "Street 1 and more")
        self.assertEqual(content["address"]["zipcode"], "45500")
        self.assertEqual(content["address"]["city"], "Customer city")
        self.assertEqual(content["address"]["state"], "")
        self.assertEqual(content["address"]["country"], "")

    def test_get_upflow_api_post_contacts_payload_format(self):
        self.assertValidUpflowPayload(
            "post-contacts",
            self.contact.get_upflow_api_post_contacts_payload(),
        )

    def test_post_contacts_payload_add_upflow_id_if_present(self):
        customer_uuid = str(uuid4())
        contact_uuid = str(uuid4())
        self.customer_company.upflow_uuid = customer_uuid
        self.contact.upflow_uuid = contact_uuid
        payload = self.contact.get_upflow_api_post_contacts_payload()
        self.assertEqual(payload["id"], contact_uuid)
        payload = self.contact.get_upflow_api_post_customers_payload()
        self.assertEqual(payload["id"], customer_uuid)

    def test_get_upflow_api_post_contacts_payload_content(self):
        content = self.contact.get_upflow_api_post_contacts_payload()
        self.assertEqual(content["firstName"], "Jack Flag")
        # self.assertEqual(content["lastName"], "")
        self.assertEqual(content["phone"], "+33604060810")
        self.assertEqual(content["email"], "jack.flag@customer-company.com")
        self.assertEqual(content["position"], "ACCOUNTING")
        self.assertEqual(content["externalId"], str(self.contact.id))
        # self.assertEqual(content["isMain"], True)

    def test_get_upflow_api_post_contacts_no_name_payload_content(self):
        content = self.contact_without_name.get_upflow_api_post_contacts_payload()
        self.assertEqual(content["firstName"], "")

    def test_get_upflow_api_post_contacts_space_name_payload_content(self):
        content = self.contact_with_spacename.get_upflow_api_post_contacts_payload()
        self.assertEqual(content["firstName"], " ")

    def test_get_upflow_api_post_contacts_payload_without_position(self):
        self.contact.upflow_position_id = False
        content = self.contact.get_upflow_api_post_contacts_payload()
        self.assertEqual("position" in content, False)

    def test_get_upflow_api_post_customers_payload_same_on_contact(self):
        self.assertEqual(
            self.customer_company.get_upflow_api_post_customers_payload(),
            self.contact.get_upflow_api_post_customers_payload(),
        )

    def test_get_upflow_api_post_credit_notes_payload_format(self):
        """refund in odoo <=> credit notes in upflow.io"""
        self.assertValidUpflowPayload(
            "post-credit_notes",
            self.refund.get_upflow_api_post_credit_note_payload(),
        )

    def test_post_credit_notes_pdf_format(self):
        self.assertValidUpflowPayload(
            "post-pdf",
            self.invoice.get_upflow_api_pdf_payload(),
        )

    def test_post_credit_note_payload_add_upflow_id_if_present(self):
        uuid = str(uuid4())
        self.refund.upflow_uuid = uuid
        payload = self.refund.get_upflow_api_post_credit_note_payload()
        self.assertEqual(payload["id"], uuid)

    def test_get_upflow_api_post_credit_notes_payload_content(self):
        """refund in odoo <=> credit notes in upflow.io"""
        content = self.refund.get_upflow_api_post_credit_note_payload()
        self.assertEqual(content["customId"], self.refund.name)
        self.assertEqual(content["externalId"], str(self.refund.id))
        self.assertEqual(content["issuedAt"], "2022-01-01")
        self.assertEqual(content["dueDate"], "2022-01-01")
        self.assertEqual(content["name"], self.refund.name)
        self.assertEqual(content["currency"], self.refund.currency_id.name)
        self.assertNotEqual(content["grossAmount"], content["netAmount"])
        self.assertAlmostEqual(
            content["grossAmount"],
            self.refund.amount_total * 1 / self.refund.currency_id.rounding,
        )
        self.assertAlmostEqual(
            content["netAmount"],
            self.refund.amount_untaxed * 1 / self.refund.currency_id.rounding,
        )
        self.assertEqual(
            content["customer"]["externalId"],
            str(self.customer_company.id),
        )

    def test_get_invoice_pdf_payload_not_an_invoice(self):
        invoice_payment_move = self._register_manual_payment_reconciled(self.invoice)
        with self.assertRaisesRegex(UserError, "expected out_invoice"):
            invoice_payment_move.get_upflow_api_pdf_payload()

    def test_format_upflow_amount(self):
        currency_euro = self.env.ref("base.EUR")
        currency_dynar = self.env.ref("base.LYD")
        self.invoice.currency_id = currency_dynar
        self.assertEqual(self.invoice._format_upflow_amount(12.258), 12258)
        self.assertEqual(
            self.invoice._format_upflow_amount(12.258, currency=currency_euro), 1226
        )
        self.invoice.currency_id = currency_euro
        self.assertEqual(self.invoice._format_upflow_amount(12.258), 1226)
        self.assertEqual(
            self.invoice._format_upflow_amount(12.258, currency=currency_dynar), 12258
        )

    def test_get_upflow_api_post_payments_payload_format(self):
        invoice_payment_move = self._register_manual_payment_reconciled(self.invoice)
        self.assertValidUpflowPayload(
            "post-payments",
            invoice_payment_move.get_upflow_api_post_payment_payload(),
        )
        invoice_payment_move.journal_id.upflow_bank_account_uuid = "abcd"
        self.assertValidUpflowPayload(
            "post-payments",
            invoice_payment_move.get_upflow_api_post_payment_payload(),
        )

    def test_post_payment_payload_add_upflow_id_if_present(self):
        invoice_payment_move = self._register_manual_payment_reconciled(self.invoice)
        uuid = str(uuid4())
        invoice_payment_move.upflow_uuid = uuid
        payload = invoice_payment_move.get_upflow_api_post_payment_payload()
        self.assertEqual(payload["id"], uuid)

    def test_get_upflow_api_post_payments_payload(self):
        """customer invoice payement (received from customer)"""
        invoice_payment_move = self._register_manual_payment_reconciled(self.invoice)
        content = invoice_payment_move.get_upflow_api_post_payment_payload()
        self.assertEqual(content["currency"], self.refund.currency_id.name)
        self.assertAlmostEqual(
            content["amount"],
            self.refund.amount_total * 1 / self.refund.currency_id.rounding,
        )
        self.assertEqual(content["externalId"], str(invoice_payment_move.id))
        self.assertEqual(content["validatedAt"], "2022-02-28")

        self.assertEqual(
            content["customer"]["externalId"],
            str(self.customer_company.id),
        )

    def test_get_upflow_api_post_payments_payload_without_payment(self):
        """customer invoice payement (received from customer)"""
        invoice_payment_move = self._make_credit_transfer_payment_reconciled(
            self.invoice
        )

        self.assertValidUpflowPayload(
            "post-payments",
            invoice_payment_move.get_upflow_api_post_payment_payload(),
        )

        content = invoice_payment_move.get_upflow_api_post_payment_payload()
        self.assertEqual(content["currency"], self.refund.currency_id.name)
        self.assertAlmostEqual(
            content["amount"],
            self.refund.amount_total * 1 / self.refund.currency_id.rounding,
        )
        self.assertEqual(content["externalId"], str(invoice_payment_move.id))
        self.assertEqual(content["validatedAt"], "2022-02-28")

        self.assertEqual(
            content["customer"]["externalId"],
            str(self.customer_company.id),
        )

    def test_get_upflow_api_post_refunds_payload_format(self):
        self.assertValidUpflowPayload(
            "post-refunds",
            self.refund_payment_move.get_upflow_api_post_refund_payload(),
        )
        self.refund_payment_move.journal_id.upflow_bank_account_uuid = "abcd"
        self.assertValidUpflowPayload(
            "post-payments",
            self.refund_payment_move.get_upflow_api_post_refund_payload(),
        )

    def test_post_refund_payload_add_upflow_id_if_present(self):
        uuid = str(uuid4())
        self.refund_payment_move.upflow_uuid = uuid
        payload = self.refund_payment_move.get_upflow_api_post_refund_payload()
        self.assertEqual(payload["id"], uuid)

    def test_get_upflow_api_post_refunds_payload(self):
        """customer refund payement (send to customer)"""
        content = self.refund_payment_move.get_upflow_api_post_refund_payload()
        self.assertEqual(content["currency"], self.refund.currency_id.name)
        self.assertAlmostEqual(
            content["amount"],
            self.refund.amount_total * 1 / self.refund.currency_id.rounding,
        )
        self.assertEqual(content["externalId"], str(self.refund_payment_move.id))
        self.assertEqual(content["validatedAt"], "2022-01-01")

        self.assertEqual(
            content["customer"]["externalId"],
            str(self.customer_company.id),
        )

    def test_get_upflow_api_post_reconcile_payload_multi_link(self):
        """customer invoice 600€ reconciled with 3 kind :

        * customer payment 100€ (Using GUI manual interface or batch payment)
        * customer refund 300€
        * customer payment from bank statement 200€
          (in such case there are no account.payment generated)
        """
        vat_ids = (
            self.env["account.tax"]
            .search(
                [
                    ("type_tax_use", "=", "sale"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
            .ids
        )
        invoice = self._create_invoice(
            unit_price=600, vat_ids=vat_ids, partner_id=self.contact, auto_validate=True
        )
        total_due_amount = invoice.amount_residual
        invoice.upflow_uuid = str(uuid4())
        manual_payment_move = self._register_manual_payment_reconciled(
            invoice, amount=100
        )
        manual_payment_move.upflow_uuid = str(uuid4())
        self.assertAlmostEqual(invoice.amount_residual, total_due_amount - 100)
        refund = self._create_invoice(
            move_type="out_refund",
            unit_price=300,
            vat_ids=vat_ids,
            partner_id=self.contact,
            auto_validate=True,
        )
        refund.upflow_uuid = str(uuid4())
        (invoice.line_ids | refund.line_ids).filtered(
            lambda line: line.account_id.reconcile
        ).reconcile()
        direct_transfer_amount = total_due_amount - 100 - refund.amount_total
        self.assertAlmostEqual(invoice.amount_residual, direct_transfer_amount)
        direct_transfer_move = self._make_credit_transfer_payment_reconciled(
            invoice,
            amount=direct_transfer_amount,
            reconcile_param=[
                {
                    "id": invoice.line_ids.filtered(
                        lambda line: line.account_internal_type
                        in ("receivable", "payable")
                    ).id
                }
            ],
        )
        direct_transfer_move.upflow_uuid = str(uuid4())
        self.assertEqual(invoice.amount_residual, 0)
        full_reconcile = invoice.mapped("line_ids.full_reconcile_id")
        self.maxDiff = None

        def convert_to_cent(euro_amount):
            return int(euro_amount * 100)

        expected_payloads = [
            {
                "invoices": [
                    {
                        "id": invoice.upflow_uuid,
                        "externalId": str(invoice.id),
                        "customId": invoice.name,
                        "amountLinked": convert_to_cent(100),
                    },
                ],
                "payments": [
                    {
                        "id": manual_payment_move.upflow_uuid,
                        "externalId": str(manual_payment_move.id),
                        "amountLinked": convert_to_cent(100),
                    },
                ],
                "creditNotes": [],
                "refunds": [],
            },
            {
                "invoices": [
                    {
                        "id": invoice.upflow_uuid,
                        "externalId": str(invoice.id),
                        "customId": invoice.name,
                        "amountLinked": convert_to_cent(refund.amount_total),
                    },
                ],
                "payments": [],
                "creditNotes": [
                    {
                        "id": refund.upflow_uuid,
                        "externalId": str(refund.id),
                        "customId": refund.name,
                        "amountLinked": convert_to_cent(refund.amount_total),
                    }
                ],
                "refunds": [],
            },
            {
                "invoices": [
                    {
                        "id": invoice.upflow_uuid,
                        "externalId": str(invoice.id),
                        "customId": invoice.name,
                        "amountLinked": convert_to_cent(direct_transfer_amount),
                    },
                ],
                "payments": [
                    {
                        "id": direct_transfer_move.upflow_uuid,
                        "externalId": str(direct_transfer_move.id),
                        "amountLinked": convert_to_cent(direct_transfer_amount),
                    },
                ],
                "creditNotes": [],
                "refunds": [],
            },
        ]

        for partial_reconcile, expected_payload in zip(
            full_reconcile.partial_reconcile_ids, expected_payloads
        ):
            reconcile_content = (
                partial_reconcile.get_upflow_api_post_reconcile_payload()
            )
            self.assertValidUpflowPayload(
                "post-reconcile",
                reconcile_content,
            )

            expected_payload["externalId"] = "partial-" + str(partial_reconcile.id)
            self.assertEqual(reconcile_content, expected_payload)

    def test_get_upflow_api_post_reconcile_refund_payload(self):
        """customer refund reconciled refund payment"""

        vat_ids = (
            self.env["account.tax"]
            .search(
                [
                    ("type_tax_use", "=", "sale"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
            .ids
        )
        refund = self._create_invoice(
            move_type="out_refund",
            unit_price=150,
            vat_ids=vat_ids,
            partner_id=self.contact,
            auto_validate=True,
        )

        manual_payment_move = self._register_manual_payment_reconciled(
            refund, amount=refund.amount_total
        )
        full_reconcile = refund.mapped("line_ids.full_reconcile_id")
        reconcile_content = (
            full_reconcile.partial_reconcile_ids.get_upflow_api_post_reconcile_payload()
        )
        self.assertValidUpflowPayload(
            "post-reconcile",
            reconcile_content,
        )

        expected = {
            "externalId": "partial-" + str(full_reconcile.partial_reconcile_ids.id),
            "invoices": [],
            "payments": [],
            "creditNotes": [
                {
                    # "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": str(refund.id),
                    "customId": refund.name,
                    "amountLinked": int(refund.amount_total * 100),
                }
            ],
            "refunds": [
                {
                    # "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": str(manual_payment_move.id),
                    "amountLinked": int(refund.amount_total * 100),
                },
            ],
        }
        self.maxDiff = None
        self.assertEqual(reconcile_content, expected)

    def test_get_upflow_api_post_contacts_payload_without_main_id(self):
        self.customer_company.main_contact_id = False
        content = self.contact.get_upflow_api_post_contacts_payload()
        self.assertEqual(content.get("isMain"), False)

    def test_get_upflow_api_post_contacts_payload_with_main_id(self):
        self.customer_company.main_contact_id = self.contact.id
        content = self.contact.get_upflow_api_post_contacts_payload()
        self.assertEqual(content.get("isMain"), True)
