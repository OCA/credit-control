import json
from collections import defaultdict
from unittest import mock
from uuid import uuid4

import responses

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.component.core import Component
from odoo.addons.edi_upflow.components.edi_output_check_upflow_post_customers import (
    _logger as check_upflow_post_customer_logger,
)
from odoo.addons.queue_job.exception import RetryableJobError
from odoo.addons.queue_job.tests.common import trap_jobs

from .common import EDIUpflowCommonCase, EDIUpflowCommonCaseRunningJob


@tagged("post_install", "-at_install")
class TestEDIUpflowHeader(EDIUpflowCommonCase):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=False)

    @responses.activate
    def test_upflow_auth_type_and_generated_header(self):
        record = self.backend.create_record(
            "upflow_post_invoice",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        record.write({"edi_exchange_state": "output_pending"})
        record._set_file_content("TEST %d" % record.id)

        url = self.upflow_ws.url.format(endpoint="v1/invoices")
        expected_key = "UPFLOW API KEY TEST"
        expected_secret = "UPFLOW API KEY SECRET"
        self.upflow_ws.write(
            {
                "auth_type": "upflow",
                "upflow_api_key": expected_key,
                "upflow_api_secret": expected_secret,
            }
        )
        response_result = "{}"
        responses.add(responses.POST, url, body=response_result)
        record.action_exchange_send()
        headers = responses.calls[0].request.headers
        self.assertEqual(headers["X-Api-Key"], expected_key)
        self.assertEqual(headers["X-Api-Secret"], expected_secret)


@tagged("post_install", "-at_install")
class TestEDIUpflowBaseClasses(EDIUpflowCommonCase):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.exchange_type = cls.env["edi.exchange.type"].create(
            {
                "name": "Test post something",
                "code": "upflow_post_something",
                "backend_id": cls.env.ref("edi_upflow.upflow_edi_backend").id,
                "backend_type_id": cls.env.ref("edi_upflow.upflow_edi_backend_type").id,
                "direction": "output",
                "exchange_file_auto_generate": False,
                "advanced_settings_edit": """
                components:
                    send:
                        usage: webservice.send
                        webservice:
                            method: post
                            kwargs:
                            url_params:
                                endpoint: v1/something
            """,
            }
        )
        cls.env["edi.exchange.type.rule"].create(
            {
                "name": "Default Test post something rule",
                "model_id": cls.env.ref("account.model_account_move").id,
                "type_id": cls.exchange_type.id,
                "kind": "form_btn",
            }
        )
        cls.invoice = cls._create_invoice(auto_validate=False)

    def test_generate_not_implemented(self):
        class EdiOutputGenerateUpflowPostSomething(Component):
            _name = "edi.output.generate.upflow_post_something"
            _inherit = "base.upflow.edi.output.generate"
            _exchange_type = "upflow_post_something"

        EdiOutputGenerateUpflowPostSomething._build_component(self.comp_registry)
        self.comp_registry._cache.clear()

        record = self.backend.create_record(
            "upflow_post_something",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        with self.assertRaisesRegex(
            NotImplementedError,
            r"You should implement generate method "
            r"to create the payload or fix the exchange type. "
            r"\(Received exchange type code: upflow_post_something\)",
        ):
            self.backend.exchange_generate(record)

    def test_check_not_implemented(self):
        class EdiOutputCheckUpflowPostSomething(Component):
            _name = "edi.output.check.upflow_post_something"
            _inherit = "base.upflow.edi.output.check"
            _exchange_type = "upflow_post_something"

        EdiOutputCheckUpflowPostSomething._build_component(self.comp_registry)
        self.comp_registry._cache.clear()

        record = self.backend.create_record(
            "upflow_post_something",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        self.backend._exchange_output_check_state(record)
        self.assertEqual(
            record.edi_exchange_state,
            "output_sent_and_error",
        )
        self.assertTrue(
            "NotImplementedError" in record.exchange_error,
            f"NotImplementedError not found in current exchange error: {record.exchange_error}",
        )
        self.assertTrue(
            "on this exchange type (code: upflow_post_something)"
            in record.exchange_error,
            f"current exchange error: {record.exchange_error}",
        )

    def test_upflow_check_check_ws_response_status_code_raises(self):
        class EdiOutputCheckUpflowPostSomething(Component):
            _name = "edi.output.check.upflow_post_something"
            _inherit = "base.upflow.edi.output.check"
            _exchange_type = "upflow_post_something"

            def _check_and_process(self):
                self._upflow_check_and_process()

        EdiOutputCheckUpflowPostSomething._build_component(self.comp_registry)
        self.comp_registry._cache.clear()

        record = self.backend.create_record(
            "upflow_post_something",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        record.ws_response_status_code = 199
        response = json.dumps("TEST")
        record._set_file_content(response, field_name="ws_response_content")
        self.backend._exchange_output_check_state(record)

        self.assertEqual(
            record.edi_exchange_state,
            "output_sent_and_error",
        )
        self.assertTrue(
            "ValidationError" in record.exchange_error,
            f"ValidationError not found in current exchange error {record.exchange_error}",
        )
        self.assertTrue(
            "Not a valid HTTP error (expected 2xx, received 199)"
            in record.exchange_error,
            f"Received exchange error: {record.exchange_error}",
        )
        self.assertTrue(
            f"the payload ({response})" in record.exchange_error,
            f"Received exchange error: {record.exchange_error}",
        )
        record.edi_exchange_state = "output_sent"
        record.ws_response_status_code = 300
        self.backend._exchange_output_check_state(record)
        self.assertEqual(
            record.edi_exchange_state,
            "output_sent_and_error",
        )
        self.assertTrue(
            "ValidationError" in record.exchange_error,
            f"ValidationError not found in current exchange error {record.exchange_error}",
        )
        self.assertTrue(
            "Not a valid HTTP error (expected 2xx, received 300)"
            in record.exchange_error,
            f"Received exchange error: {record.exchange_error}",
        )
        self.assertTrue(
            f"the payload ({response})" in record.exchange_error,
            f"Received exchange error: {record.exchange_error}",
        )

    def test_upflow_check_check_ws_response_missing_id(self):
        class EdiOutputCheckUpflowPostSomething(Component):
            _name = "edi.output.check.upflow_post_something"
            _inherit = "base.upflow.edi.output.check"
            _exchange_type = "upflow_post_something"

            def _check_and_process(self):
                self._upflow_check_and_process()

        EdiOutputCheckUpflowPostSomething._build_component(self.comp_registry)
        self.comp_registry._cache.clear()
        record = self.backend.create_record(
            "upflow_post_something",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )

        record._set_file_content(json.dumps({}), field_name="ws_response_content")
        record.ws_response_status_code = 200

        self.backend._exchange_output_check_state(record)
        self.assertEqual(
            record.edi_exchange_state,
            "output_sent_and_error",
        )
        self.assertTrue(
            "KeyError" in record.exchange_error,
            f"KeyError not found in current exchange error: {record.exchange_error}",
        )
        self.assertTrue(
            "id" in record.exchange_error,
            f"id not found in current exchange error: {record.exchange_error}",
        )

    def test_upflow_check_check_ws_response_no_payload(self):
        class EdiOutputCheckUpflowPostSomething(Component):
            _name = "edi.output.check.upflow_post_something"
            _inherit = "base.upflow.edi.output.check"
            _exchange_type = "upflow_post_something"

            def _check_and_process(self):
                self._upflow_check_and_process()

        EdiOutputCheckUpflowPostSomething._build_component(self.comp_registry)
        self.comp_registry._cache.clear()
        record = self.backend.create_record(
            "upflow_post_something",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )

        record.ws_response_status_code = 200

        self.backend._exchange_output_check_state(record)
        self.assertEqual(
            record.edi_exchange_state,
            "output_sent_and_error",
        )
        self.assertTrue(
            "KeyError" in record.exchange_error,
            f"KeyError not found in current exchange error: {record.exchange_error}",
        )
        self.assertTrue(
            "id" in record.exchange_error,
            f"id not found in current exchange error: {record.exchange_error}",
        )


@tagged("post_install", "-at_install")
class TestFlows(EDIUpflowCommonCaseRunningJob):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()

        type_current_liability = cls.env.ref(
            "account.data_account_type_current_liabilities"
        )
        cls.final_output_vat_acct = cls.env["account.account"].create(
            {
                "name": "final vat account",
                "code": "FINAL-20",
                "reconcile": True,
                "user_type_id": type_current_liability.id,
            }
        )
        cls.transition_vat_acct = cls.env["account.account"].create(
            {
                "name": "waiting vat account",
                "code": "WAIT-20",
                "reconcile": True,
                "user_type_id": type_current_liability.id,
            }
        )
        cls.tax_group_vat = cls.env["account.tax.group"].create({"name": "VAT"})

        cls.vat_on_payment = cls.env["account.tax"].create(
            {
                "name": "Test 20% on payment",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 20.00,
                "tax_exigibility": "on_payment",
                "tax_group_id": cls.tax_group_vat.id,
                "cash_basis_transition_account_id": cls.transition_vat_acct.id,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100.0, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100.0,
                            "repartition_type": "tax",
                            "account_id": cls.final_output_vat_acct.id,
                        },
                    ),
                ],
            }
        )
        cls.invoice = cls._create_invoice(
            auto_validate=False, vat_ids=cls.vat_on_payment.ids
        )
        cls.refund = cls._create_invoice(
            move_type="out_refund", auto_validate=False, vat_ids=cls.vat_on_payment.ids
        )

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_invoice_flow(self):
        generated_content = '{"some": "value"}'
        invoice_uuid = str(uuid4())
        response_result = json.dumps(
            {
                "externalId": "FAC123",
                "issuedAt": "2015-05-05T12:30:00",
                "dueDate": "2015-05-05T12:30:00",
                "name": "Facture couvrant les prestations de service de Decembre",
                "currency": "EUR",
                "grossAmount": 1700,
                "netAmount": 1500,
                "id": invoice_uuid,
                "customerId": "a1b2c3",
                "payments": [
                    {
                        "amount": 1700,
                        "executedAt": "2015-05-05T12:30:00",
                        "instrument": "'WIRE_TRANSFER'",
                    }
                ],
                "pdfUrl": "http://example.com/invoice.pdf",
                "state": "DUE",
            }
        )

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=response_result,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_invoice"
            ".EdiOutputGenerateUpflowPostInvoice.generate",
            return_value=generated_content,
        ) as m_generate:
            self.invoice.action_post()
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            [call for call in responses.calls if call.request.url.endswith("invoices")][
                0
            ].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", self.invoice.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_invoices"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(self.partner.upflow_edi_backend_id, self.backend)

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_invoice_pdf_flow(self):
        generated_content = '{"some": "value"}'
        invoice_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=json.dumps(
                {
                    "id": invoice_uuid,
                }
            ),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_invoice_pdf"
            ".EdiOutputGenerateUpflowPostInvoicePDF.generate",
            return_value=generated_content,
        ) as m_generate:
            self.invoice.action_post()
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            [
                call
                for call in responses.calls
                if call.request.url.endswith(f"{invoice_uuid}/pdf")
            ][0].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", self.invoice.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_invoices_pdf"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_credit_notes_flow(self):
        generated_content = '{"some": "value"}'
        credit_note_uuid = str(uuid4())
        response_result = json.dumps(
            {
                "customId": "FAC123",
                "externalId": "92842AB37",
                "issuedAt": "2015-05-05T12:30:00",
                "dueDate": "2015-05-05T12:30:00",
                "name": "Facture couvrant les prestations de service de Decembre",
                "currency": "EUR",
                "grossAmount": 1700,
                "netAmount": 1500,
                "id": credit_note_uuid,
                "pdfUrl": "http://example.com/invoice.pdf",
                "customer": {
                    "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": "1a2c3b",
                    "companyName": "Upflow SAS",
                    "accountingRef": "UPFL",
                },
                "linkedInvoices": [],
            }
        )

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/credit_notes"),
            body=response_result,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(
                endpoint=f"v1/credit_notes/{credit_note_uuid}/pdf"
            ),
            body="",
            status=204,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_credit_notes"
            ".EdiOutputGenerateUpflowPostCreditNotes.generate",
            return_value=generated_content,
        ) as m_generate:
            self.refund.action_post()
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            [
                call
                for call in responses.calls
                if call.request.url.endswith("credit_notes")
            ][0].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", self.refund.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_credit_notes"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_credit_notes_as_payment_flow(self):
        """Testing forcing upflow type"""
        generated_content = '{"some": "value"}'
        credit_note_uuid = str(uuid4())
        response_result = json.dumps(
            {
                "customId": "FAC123",
                "externalId": "92842AB37",
                "issuedAt": "2015-05-05T12:30:00",
                "dueDate": "2015-05-05T12:30:00",
                "name": "Facture couvrant les prestations de service de Decembre",
                "currency": "EUR",
                "grossAmount": 1700,
                "netAmount": 1500,
                "id": credit_note_uuid,
                "pdfUrl": "http://example.com/invoice.pdf",
                "customer": {
                    "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": "1a2c3b",
                    "companyName": "Upflow SAS",
                    "accountingRef": "UPFL",
                },
                "linkedInvoices": [],
            }
        )

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/payments"),
            body=response_result,
        )
        self.refund.upflow_type = "payments"
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_payments"
            ".EdiOutputGenerateUpflowPostPayments.generate",
            return_value=generated_content,
        ) as m_generate:
            self.refund.action_post()
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 2)
        self.assertEqual(
            [call for call in responses.calls if call.request.url.endswith("payments")][
                0
            ].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", self.refund.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_credit_notes"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 0)
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", self.refund.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_payments"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)

        self.refund.upflow_type = "none"
        self.refund._compute_upflow_type()
        self.assertEqual(self.refund.upflow_type, "payments")
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_credit_notes_flow_pdf(self):
        generated_content = '{"some": "value"}'
        credit_note_uuid = str(uuid4())

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/credit_notes"),
            body=json.dumps(
                {
                    "id": credit_note_uuid,
                }
            ),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(
                endpoint=f"v1/credit_notes/{credit_note_uuid}/pdf"
            ),
            body=json.dumps(
                {
                    "id": credit_note_uuid,
                }
            ),
            status=204,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_credit_notes_pdf"
            ".EdiOutputGenerateUpflowPostCreditNotesPDF.generate",
            return_value=generated_content,
        ) as m_generate:
            self.refund.action_post()
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            [
                call
                for call in responses.calls
                if call.request.url.endswith(f"credit_notes/{credit_note_uuid}/pdf")
            ][0].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", self.refund.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_credit_notes_pdf"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_payments_flow(self):
        generated_content = '{"some": "value"}'
        response_result = json.dumps(
            {
                "currency": "EUR",
                "amount": 1700,
                "instrument": "CARD",
                "validatedAt": "2015-05-05T12:30:00",
                "externalId": "92842AB37",
                "bankAccountId": "00a70b35-2be3-4c43-aefb-397190134655",
                "id": "00a70b35-2be3-4c43-aefb-397190134655",
                "type": "ACCOUNT",
                "amountLinked": 1700,
                "modifiedAt": "2015-05-05T12:30:00",
                "linkedInvoices": [
                    {
                        "linkedAmount": 3000,
                        "invoice": {
                            "id": "00a70b35-2be3-4c43-aefb-397190134655",
                            "currency": "EUR",
                            "status": "DUE",
                            "amountOutstanding": 1500,
                            "customId": "FAC123",
                            "grossAmount": 1700,
                            "netAmount": 1500,
                            "name": "Facture couvrant les prestations de service de Decembre",
                            "issuedAt": "2015-05-05T12:30:00",
                            "dueDate": "2015-05-05T12:30:00",
                            "paidDate": "2015-05-05T12:30:00",
                            "externalId": "92842AB37",
                        },
                    }
                ],
                "customer": {
                    "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": "1a2c3b",
                    "companyName": "Upflow SAS",
                    "accountingRef": "UPFL",
                },
            }
        )
        invoice_uuid = uuid4()
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=json.dumps({"id": str(invoice_uuid)}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/payments"),
            body=response_result,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/reconcile"),
            body="CREATED",
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_payments"
            ".EdiOutputGenerateUpflowPostPayments.generate",
            return_value=generated_content,
        ) as m_generate:
            self.invoice.action_post()
            move = self._register_manual_payment_reconciled(self.invoice)
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 5)
        self.assertEqual(
            [call for call in responses.calls if call.request.url.endswith("payments")][
                0
            ].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", move.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_payments"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_refunds_flow(self):
        generated_content = '{"some": "value"}'
        response_result = json.dumps(
            {
                "currency": "EUR",
                "amount": 1700,
                "instrument": "CARD",
                "validatedAt": "2015-05-05T12:30:00",
                "externalId": "92842AB37",
                "id": "00a70b35-2be3-4c43-aefb-397190134655",
                "amountLinked": 1700,
                "modifiedAt": "2015-05-05T12:30:00",
                "linkedTransactions": [],
                "linkedCreditNotes": [],
                "customer": {
                    "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": "1a2c3b",
                    "companyName": "Upflow SAS",
                    "accountingRef": "UPFL",
                },
            }
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        credit_note_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/credit_notes"),
            body=json.dumps({"id": credit_note_uuid}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(
                endpoint=f"v1/credit_notes/{credit_note_uuid}/pdf"
            ),
            body=json.dumps(
                {
                    "id": credit_note_uuid,
                }
            ),
            status=204,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/refunds"),
            body=response_result,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/reconcile"),
            body="CREATED",
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_refunds"
            ".EdiOutputGenerateUpflowPostRefunds.generate",
            return_value=generated_content,
        ) as m_generate:
            self.refund.action_post()
            move = self._register_manual_payment_reconciled(self.refund)
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 5)
        self.assertEqual(
            [call for call in responses.calls if call.request.url.endswith("refunds")][
                0
            ].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                ("res_id", "=", move.id),
                (
                    "type_id",
                    "=",
                    self.env.ref("edi_upflow.upflow_edi_exchange_type_post_refunds").id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_reconcile_flow(self):
        generated_content = '{"some": "value"}'
        response_result = json.dumps("CREATED")

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        invoice_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=json.dumps({"id": invoice_uuid}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/payments"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/reconcile"),
            body=response_result,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_reconcile"
            ".EdiOutputGenerateUpflowPostReconcile.generate",
            return_value=generated_content,
        ) as m_generate:
            self.invoice.action_post()
            self._register_manual_payment_reconciled(self.invoice)
            # Depending of test database this is useless as it done by payment
            # force to reconcile vat amounts while using temporary account
            # to manage on payment VAT
            self.env["account.move.line"].search(
                [
                    ("account_id", "=", self.transition_vat_acct.id),
                    ("parent_state", "=", "posted"),
                    ("full_reconcile_id", "=", False),
                ]
            ).reconcile()
            partial_reconcile = self.invoice.line_ids.matched_credit_ids
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 5)
        self.assertEqual(
            [
                call
                for call in responses.calls
                if call.request.url.endswith("reconcile")
            ][0].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", partial_reconcile._name),
                ("res_id", "in", partial_reconcile.ids),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_reconcile"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_unlink_reconcile_flow(self):
        response_result = json.dumps("CREATED")

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        invoice_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=json.dumps({"id": invoice_uuid}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/payments"),
            body=json.dumps({"id": str(uuid4())}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/reconcile"),
            body=response_result,
        )
        self.invoice.action_post()
        self._register_manual_payment_reconciled(self.invoice)
        partial_reconcile = self.invoice.line_ids.matched_credit_ids
        partial_reconcile.unlink()

        self.assertEqual(len(responses.calls), 6)
        reconcile_calls = [
            call for call in responses.calls if call.request.url.endswith("reconcile")
        ]
        self.assertEqual(
            len(json.loads(reconcile_calls[0].request.body)["invoices"]), 1
        )
        self.assertEqual(
            len(json.loads(reconcile_calls[1].request.body)["invoices"]), 0
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", partial_reconcile._name),
                ("res_id", "in", partial_reconcile.ids),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_reconcile"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 2)

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_reconcile_with_refund_flow(self):
        def group_recordset_by(recordset, key):
            groups = defaultdict(self.env[recordset._name].browse)
            for elem in recordset:
                groups[key(elem)] |= elem
            return groups.items()

        generated_content = '{"some": "value"}'
        response_result = json.dumps("CREATED")

        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=json.dumps({"id": str(uuid4())}),
        )
        invoice_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=json.dumps({"id": invoice_uuid}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )

        credit_note_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/credit_notes"),
            body=json.dumps({"id": credit_note_uuid}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(
                endpoint=f"v1/credit_notes/{credit_note_uuid}/pdf"
            ),
            body=json.dumps(
                {
                    "id": credit_note_uuid,
                }
            ),
            status=204,
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/reconcile"),
            body=response_result,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_reconcile"
            ".EdiOutputGenerateUpflowPostReconcile.generate",
            return_value=generated_content,
        ) as m_generate:
            self.invoice.action_post()
            self.refund.action_post()
            for _key, group in group_recordset_by(
                (self.invoice.line_ids | self.refund.line_ids).filtered(
                    lambda line: line.account_id.reconcile
                ),
                lambda l: l.account_id.user_type_id.type,
            ):
                group.reconcile()
            partial_reconcile = self.invoice.line_ids.matched_credit_ids
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 6)
        self.assertEqual(
            [
                call
                for call in responses.calls
                if call.request.url.endswith("reconcile")
            ][0].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", partial_reconcile._name),
                ("res_id", "in", partial_reconcile.ids),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_reconcile"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")

    @mute_logger("odoo.addons.queue_job.delay")
    @responses.activate
    def test_output_exchange_sync_post_customers_flow(self):
        generated_content = '{"some": "value"}'
        response_result = json.dumps(
            {
                "name": "Upflow SAS",
                "vatNumber": "838718328",
                "accountingRef": "UPFL",
                "externalId": "1a2c3b",
                "accountManagerId": "00a70b35-2be3-4c43-aefb-397190134655",
                "dunningPlanId": "7a6c91dc-3580-4c43-aefb-397190134655",
                "address": {
                    "address": "25 Passage Dubail",
                    "zipcode": "75010",
                    "city": "Paris",
                    "state": "Île",
                    "country": "France",
                },
                "parent": {
                    "id": "00a70b35-2be3-4c43-aefb-397190134655",
                    "externalId": "1a2c3b",
                },
                "paymentMethods": {
                    "card": {"enabled": False},
                    "check": {"enabled": False},
                    "achDebit": {"enabled": False},
                    "sepaDebit": {"enabled": False},
                    "goCardless": {"enabled": False},
                    "wireTransfer": {
                        "enabled": False,
                        "bankAccount": {"id": "00a70b35-2be3-4c43-aefb-397190134655"},
                        "bankAccounts": [
                            {"id": "00a70b35-2be3-4c43-aefb-397190134655"}
                        ],
                    },
                },
                "customFields": [
                    {
                        "externalId": "AEGaaZD",
                        "id": "00a70b35-2be3-4c43-aefb-397190134655",
                        "value": None,
                        "source": "USER_DEFINED",
                    }
                ],
                "id": "00a70b35-2be3-4c43-aefb-397190134655",
                "countInvoicesDue": 0,
                "countInvoicesOverdue": 1,
                "amountDue": 0,
                "amountOverdue": 118000,
                "currency": "Currency",
                "directUrl": "https://app.upflow.io/customers/ABCDEFGHI",
            }
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/customers"),
            body=response_result,
        )
        invoice_uuid = str(uuid4())
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint="v1/invoices"),
            body=json.dumps({"id": invoice_uuid}),
        )
        responses.add(
            responses.POST,
            self.upflow_ws.url.format(endpoint=f"v1/invoices/{invoice_uuid}/pdf"),
            body="",
            status=204,
        )
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_customers"
            ".EdiOutputGenerateUpflowPostCustomers.generate",
            return_value=generated_content,
        ) as m_generate:
            self.invoice.action_post()
            # self.backend._cron_check_output_exchange_sync(skip_sent=False)
            m_generate.assert_called_once()

        self.assertEqual(len(responses.calls), 3)
        self.assertEqual(
            [
                call
                for call in responses.calls
                if call.request.url.endswith("customers")
            ][0].request.body,
            generated_content,
        )
        records = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "res.partner"),
                ("res_id", "=", self.invoice.commercial_partner_id.id),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                    ).id,
                ),
            ]
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "output_sent_and_processed")


@tagged("post_install", "-at_install")
class TestEDIUpflowInvoices(EDIUpflowCommonCase):
    """Invoices flows POST v1/invoices"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=False)

    def test_post_invoice_create_exchange_record(self):
        domain = [
            ("model", "=", "account.move"),
            ("res_id", "=", self.invoice.id),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_invoices").id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.invoice.action_post()
            # 1 customer + 1 invoice + 1 PDF=> 2 jobs
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_post_invoice_on_synchronized_partner_create_exchange_record(self):
        self.partner.upflow_uuid = str(uuid4())
        self.partner.upflow_edi_backend_id = self.backend
        domain = [
            ("model", "=", "account.move"),
            ("res_id", "=", self.invoice.id),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.invoice.action_post()
            # 1 invoice + 1 PDF=> 2 jobs
            trap.assert_jobs_count(2, only=self.backend.exchange_generate)
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(
                domain
                + [
                    (
                        "type_id",
                        "=",
                        self.env.ref(
                            "edi_upflow.upflow_edi_exchange_type_post_invoices"
                        ).id,
                    ),
                ]
            ),
            1,
        )
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(
                domain
                + [
                    (
                        "type_id",
                        "=",
                        self.env.ref(
                            "edi_upflow.upflow_edi_exchange_type_post_invoices_pdf"
                        ).id,
                    ),
                ]
            ),
            1,
        )
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(
                domain
                + [
                    (
                        "type_id",
                        "=",
                        self.env.ref(
                            "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                        ).id,
                    ),
                ]
            ),
            0,
        )

    def test_perform_invoice_job_before_customer_job_is_send_and_processed(self):
        with trap_jobs() as trap:
            self.invoice.action_post()
            # 1 customer + 1 invoice + 1 invoice PDF => 3 jobs
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)
            account_move_job = [
                job
                for job in trap.enqueued_jobs
                if job.args[0].res_id == self.invoice.id
                and job.args[0].model == "account.move"
            ][0]
            with self.assertRaisesRegex(
                RetryableJobError, "Waiting related exchanges to be done before"
            ):
                account_move_job.perform()

    def test_upflow_post_invoice_generate(self):
        record = self.backend.create_record(
            "upflow_post_invoice",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_invoice_match_generate(self):
        record = self.backend.create_record(
            "upflow_post_invoice",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_invoice"
            ".EdiOutputGenerateUpflowPostInvoice.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_invoice_check(self):
        record = self.backend.create_record(
            "upflow_post_invoice",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        uuid = str(uuid4())
        record._set_file_content(
            json.dumps({"id": uuid}), field_name="ws_response_content"
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(self.invoice.upflow_uuid, uuid)


@tagged("post_install", "-at_install")
class TestEDIUpflowInvoicesPDF(EDIUpflowCommonCase):
    """Invoices flows POST v1/invoices/<uuid>/pdf"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=False)

    def test_post_invoice_pdf_create_exchange_record(self):
        domain = [
            ("model", "=", "account.move"),
            ("res_id", "=", self.invoice.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_post_invoices_pdf"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.invoice.action_post()
            # 1 customer + 1 invoice + 1 invoice pdf => 3 jobs
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_upflow_post_invoice_pdf_generate(self):
        record = self.backend.create_record(
            "upflow_post_invoice_pdf",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_invoice_pdf_match_generate(self):
        record = self.backend.create_record(
            "upflow_post_invoice_pdf",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_invoice_pdf"
            ".EdiOutputGenerateUpflowPostInvoicePDF.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_invoice_pdf_check(self):
        record = self.backend.create_record(
            "upflow_post_invoice_pdf",
            {
                "model": self.invoice._name,
                "res_id": self.invoice.id,
            },
        )
        # real end point do not return uuid
        # so here we ensure we would not erase data if any founds
        uuid = str(uuid4())
        record._set_file_content(
            json.dumps({"id": uuid}), field_name="ws_response_content"
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertFalse(self.invoice.upflow_uuid)


@tagged("post_install", "-at_install")
class TestEDIUpflowCreditNotes(EDIUpflowCommonCase):
    """Credit notes flows POST v1/credit_notes"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.refund = cls._create_invoice(move_type="out_refund", auto_validate=False)

    def test_post_refund_create_exchange_record(self):
        domain = [
            ("model", "=", "account.move"),
            ("res_id", "=", self.refund.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_post_credit_notes"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)
        with trap_jobs() as trap:
            self.refund.action_post()
            # 1 customer + 1 refund + 1pdf => 2 jobs
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_upflow_post_refund_generate(self):
        record = self.backend.create_record(
            "upflow_post_credit_notes",
            {
                "model": self.refund._name,
                "res_id": self.refund.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_credit_notes_match_generate(self):
        record = self.backend.create_record(
            "upflow_post_credit_notes",
            {
                "model": self.refund._name,
                "res_id": self.refund.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_credit_notes"
            ".EdiOutputGenerateUpflowPostCreditNotes.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_credit_notes_check(self):
        record = self.backend.create_record(
            "upflow_post_credit_notes",
            {
                "model": self.refund._name,
                "res_id": self.refund.id,
            },
        )
        uuid = str(uuid4())
        record._set_file_content(
            json.dumps({"id": uuid}), field_name="ws_response_content"
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(self.refund.upflow_uuid, uuid)


@tagged("post_install", "-at_install")
class TestEDIUpflowInvoicePayment(EDIUpflowCommonCase):
    """Credit notes flows POST v1/credit_notes"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=True)

    def test_post_payment_create_exchange_record(self):
        domain = [
            ("model", "=", "account.move"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_payments").id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self._register_manual_payment_reconciled(self.invoice)
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_upflow_post_payments_generate(self):
        move = self._register_manual_payment_reconciled(self.invoice)
        record = self.backend.create_record(
            "upflow_post_payments",
            {
                "model": move._name,
                "res_id": move.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_payments_match_generate(self):
        move = self._register_manual_payment_reconciled(self.invoice)
        record = self.backend.create_record(
            "upflow_post_payments",
            {
                "model": move._name,
                "res_id": move.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_payments"
            ".EdiOutputGenerateUpflowPostPayments.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_payments_check(self):
        move = self._register_manual_payment_reconciled(self.invoice)
        record = self.backend.create_record(
            "upflow_post_payments",
            {
                "model": move._name,
                "res_id": move.id,
            },
        )
        uuid = str(uuid4())
        record._set_file_content(
            json.dumps({"id": uuid}), field_name="ws_response_content"
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(move.upflow_uuid, uuid)


@tagged("post_install", "-at_install")
class TestEDIUpflowRefunds(EDIUpflowCommonCase):
    """flows POST v1/credit_notes"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.refund = cls._create_invoice(
            move_type="out_refund",
            auto_validate=True,
        )

    def test_post_refund_payment_create_exchange_record(self):
        domain = [
            ("model", "=", "account.move"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_refunds").id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)
        with trap_jobs() as trap:
            self._register_manual_payment_reconciled(self.refund)
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_upflow_post_refunds_generate(self):
        move = self._register_manual_payment_reconciled(self.refund)
        record = self.backend.create_record(
            "upflow_post_refunds",
            {
                "model": move._name,
                "res_id": move.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_refunds_match_generate(self):
        move = self._register_manual_payment_reconciled(self.refund)
        record = self.backend.create_record(
            "upflow_post_refunds",
            {
                "model": move._name,
                "res_id": move.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_refunds"
            ".EdiOutputGenerateUpflowPostRefunds.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_refunds_check(self):
        move = self._register_manual_payment_reconciled(self.refund)
        record = self.backend.create_record(
            "upflow_post_refunds",
            {
                "model": move._name,
                "res_id": move.id,
            },
        )
        uuid = str(uuid4())
        record._set_file_content(
            json.dumps({"id": uuid}), field_name="ws_response_content"
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(move.upflow_uuid, uuid)


@tagged("post_install", "-at_install")
class TestEdiUpflowReconcileOperation(EDIUpflowCommonCase):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=True)

    def test_on_create_account_partial_reconcile_create_exchange_record(self):
        domain = [
            ("model", "=", "account.partial.reconcile"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_reconcile").id,
            ),
        ]
        self.assertEqual(self.env["edi.exchange.record"].search_count(domain), 0)
        with trap_jobs() as trap:
            self._register_manual_payment_reconciled(self.invoice)
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_on_create_payed_supplier_invoice_should_not_create_any_exchanges(self):
        domain = []
        count_before = self.env["edi.exchange.record"].search_count(domain)
        with trap_jobs() as trap:
            supplier_invoice = self._create_invoice(
                move_type="in_invoice", auto_validate=True
            )
            self._register_manual_payment_reconciled(
                supplier_invoice,
                payment_type="outbound",
                bank_journal=None,
                method=self.env.ref("account.account_payment_method_manual_out"),
            )
            trap.assert_jobs_count(0, only=self.backend.exchange_generate)
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(domain), count_before
        )

    def test_on_create_reconcile_without_payment_create_exchange_record_and_payment_record(
        self,
    ):
        reconcile_domain = [
            ("model", "=", "account.partial.reconcile"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_reconcile").id,
            ),
        ]

        payments_domain = [
            ("model", "=", "account.move"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_payments").id,
            ),
        ]
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(reconcile_domain), 0
        )
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(payments_domain), 0
        )
        self.invoice.commercial_partner_id.upflow_uuid = "abc"
        with trap_jobs() as trap:
            self._make_credit_transfer_payment_reconciled(
                self.invoice,
                reconcile_param=[
                    {
                        "id": self.invoice.line_ids.filtered(
                            lambda line: line.account_internal_type
                            in ("receivable", "payable")
                        ).id
                    }
                ],
            )
            trap.assert_jobs_count(2, only=self.backend.exchange_generate)
        reconcile_exchange = self.env["edi.exchange.record"].search(reconcile_domain)
        self.assertEqual(len(reconcile_exchange), 1)
        self.assertEqual(reconcile_exchange.edi_exchange_state, "new")
        payment_exchange = self.env["edi.exchange.record"].search(payments_domain)
        self.assertEqual(len(payment_exchange), 1)
        self.assertEqual(payment_exchange.edi_exchange_state, "new")
        # test related exchanges
        invoice_exchange = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_invoices"
                    ).id,
                ),
            ]
        )
        invoice_pdf_exchange = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "account.move"),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_post_invoices_pdf"
                    ).id,
                ),
            ]
        )
        customer_exchange = self.env["edi.exchange.record"].search(
            [
                ("model", "=", "res.partner"),
                (
                    "type_id",
                    "=",
                    self.env.ref(
                        "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                    ).id,
                ),
            ]
        )
        self.assertEqual(invoice_exchange.dependent_exchange_ids, (customer_exchange))
        self.assertEqual(
            invoice_pdf_exchange.dependent_exchange_ids, (invoice_exchange)
        )
        self.assertEqual(
            reconcile_exchange.dependent_exchange_ids,
            (payment_exchange | invoice_exchange),
        )

    def test_on_create_account_full_reconcile_without_payment_raise_on_reconcile(
        self,
    ):
        reconcile_domain = [
            ("model", "=", "account.partial.reconcile"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_reconcile").id,
            ),
        ]

        payments_domain = [
            ("model", "=", "account.move"),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_payments").id,
            ),
        ]
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(reconcile_domain), 0
        )
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(payments_domain), 0
        )
        self.invoice.commercial_partner_id.upflow_uuid = "abc"
        with trap_jobs() as trap:
            self._make_credit_transfer_payment_reconciled(
                self.invoice,
                reconcile_param=[
                    {
                        "id": self.invoice.line_ids.filtered(
                            lambda line: line.account_internal_type
                            in ("receivable", "payable")
                        ).id
                    }
                ],
                partner=False,
            )
            trap.assert_jobs_count(2, only=self.backend.exchange_generate)
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(reconcile_domain), 1
        )
        self.assertEqual(
            self.env["edi.exchange.record"].search_count(payments_domain), 1
        )

    def test_create_missing_exchange_record_without_partner(self):
        move_payment_id = self._make_credit_transfer_payment_reconciled(
            self.invoice,
            reconcile_param=[
                {
                    "id": self.invoice.line_ids.filtered(
                        lambda line: line.account_internal_type
                        in ("receivable", "payable")
                    ).id
                }
            ],
            partner=False,
        )
        move_payment_id.line_ids.partner_id = False
        move_payment_id._compute_upflow_commercial_partner_id()
        with self.assertRaisesRegex(
            UserError,
            "You can reconcile journal items because the journal entry .* "
            "is not synchronisable with upflow.io, because partner is not "
            "set but required.",
        ):
            self.comp_registry["account.partial.reconcile.upflow.event.listener"](
                None
            )._create_missing_exchange_record(
                self.env["edi.exchange.record"].browse(), move_payment_id
            )

    def test_upflow_post_reconcile(self):
        self._register_manual_payment_reconciled(self.invoice)
        partial_reconcile = self.invoice.line_ids.matched_credit_ids
        record = self.backend.create_record(
            "upflow_post_reconcile",
            {
                "model": partial_reconcile._name,
                "res_id": partial_reconcile.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_reconcile_match_generate(self):
        self._register_manual_payment_reconciled(self.invoice)
        partial_reconcile = self.invoice.line_ids.matched_credit_ids
        record = self.backend.create_record(
            "upflow_post_reconcile",
            {
                "model": partial_reconcile._name,
                "res_id": partial_reconcile.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_reconcile"
            ".EdiOutputGenerateUpflowPostReconcile.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_reconcile_check(self):
        self._register_manual_payment_reconciled(self.invoice)
        partial_reconcile = self.invoice.line_ids.matched_credit_ids
        exchange_record = self.backend.create_record(
            "upflow_post_reconcile",
            {
                "model": partial_reconcile._name,
                "res_id": partial_reconcile.id,
            },
        )
        exchange_record._set_file_content(
            json.dumps("CREATED"), field_name="ws_response_content"
        )
        exchange_record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(exchange_record)
        self.assertEqual(
            exchange_record.edi_exchange_state, "output_sent_and_processed"
        )
        self.assertTrue(exchange_record.record.sent_to_upflow)


@tagged("post_install", "-at_install")
class TestEDIUpflowCustomersContacts(EDIUpflowCommonCase):
    """Invoices flows POST v1/invoices"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=False)
        cls.partner.upflow_edi_backend_id = cls.backend

    def test_post_invoice_create_exchange_record(self):
        domain = [
            ("model", "=", "res.partner"),
            ("res_id", "=", self.invoice.commercial_partner_id.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.invoice.action_post()
            trap.assert_jobs_count(3, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_update_synchronized_customer_create_exchange_record(self):
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            ("res_id", "=", self.partner.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.partner.street = "abcd"
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_update_other_field_on_synchronized_customer_do_not_create_exchange_record(
        self,
    ):
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            ("res_id", "=", self.partner.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        self.assertEqual(self.env["edi.exchange.record"].search_count(domain), 0)

        with trap_jobs() as trap:
            self.partner.phone = "101"
            trap.assert_jobs_count(0, only=self.backend.exchange_generate)

        self.assertEqual(self.env["edi.exchange.record"].search_count(domain), 0)

    def test_add_contact_to_synchronized_customer_create_exchange_record(self):
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            ("res_id", "=", self.partner.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.env["res.partner"].create(
                {"name": "test", "parent_id": self.partner.id}
            )
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_unlink_contact_to_synchronized_customer_create_exchange_record(self):
        contact = self.env["res.partner"].create(
            {"name": "test", "parent_id": self.partner.id}
        )
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            ("res_id", "=", self.partner.id),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            contact.unlink()
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")

    def test_change_parent_contact_to_synchronized_customer_create_exchange_record(
        self,
    ):
        partner2 = self.env["res.partner"].create({"name": "test 2"})
        contact = self.env["res.partner"].create(
            {"name": "test", "parent_id": self.partner.id}
        )
        partner2.upflow_uuid = str(uuid4())
        partner2.upflow_edi_backend_id = self.backend
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            contact.parent_id = partner2
            trap.assert_jobs_count(2, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 2)
        exchange_partners = [r.record for r in records]
        self.assertTrue(partner2 in exchange_partners)
        self.assertTrue(self.partner in exchange_partners)

    def test_change_customer_main_contact_id_generate_one_edi_call_on_contact(
        self,
    ):
        contact = self.env["res.partner"].create(
            {"name": "test", "parent_id": self.partner.id}
        )
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_put_contacts"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)

        with trap_jobs() as trap:
            self.partner.main_contact_id = contact.id
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        exchange_partners = [r.record for r in records]
        self.assertTrue(contact in exchange_partners)

    def test_change_contacts_field_generate_one_edi_call_on_contact(self):
        contact = self.env["res.partner"].create(
            {"name": "test", "parent_id": self.partner.id}
        )
        contact.upflow_uuid = str(uuid4())
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_put_contacts"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)
        with trap_jobs() as trap:
            contact.name = "test 2"
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        exchange_partners = [r.record for r in records]
        self.assertTrue(contact in exchange_partners)

    def test_change_contacts_field_without_upflow_uuid_generate_one_edi_call_on_customer(
        self,
    ):
        contact = self.env["res.partner"].create(
            {"name": "test", "parent_id": self.partner.id}
        )
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)
        with trap_jobs() as trap:
            contact.name = "test 2"
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        exchange_partners = [r.record for r in records]
        self.assertTrue(self.partner in exchange_partners)

    def test_contact_already_exist_and_link_to_customer_setting_email(self):
        contact = self.env["res.partner"].create(
            {"name": "test", "parent_id": self.partner.id}
        )
        self.partner.upflow_uuid = str(uuid4())

        domain = [
            ("model", "=", "res.partner"),
            (
                "type_id",
                "=",
                self.env.ref(
                    "edi_upflow.upflow_edi_exchange_type_upflow_post_customers"
                ).id,
            ),
        ]
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 0)
        with trap_jobs() as trap:
            contact.email = "example@email.com"
            trap.assert_jobs_count(1, only=self.backend.exchange_generate)

        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        exchange_partners = [r.record for r in records]
        self.assertTrue(self.partner in exchange_partners)

    def test_upflow_post_customers_generate(self):
        record = self.backend.create_record(
            "upflow_post_customers",
            {
                "model": self.invoice.commercial_partner_id._name,
                "res_id": self.invoice.commercial_partner_id.id,
            },
        )
        self.backend.exchange_generate(record)
        self.assertTrue(
            record._get_file_content(),
        )

    def test_upflow_post_customers_match_generate(self):
        record = self.backend.create_record(
            "upflow_post_customers",
            {
                "model": self.invoice.commercial_partner_id._name,
                "res_id": self.invoice.commercial_partner_id.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_post_customers"
            ".EdiOutputGenerateUpflowPostCustomers.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    def test_upflow_post_customers_check(self):

        contact1 = self.env["res.partner"].create({"name": "test 1"})
        self.invoice.commercial_partner_id.child_ids = [(6, 0, [contact1.id])]

        record = self.backend.create_record(
            "upflow_post_customers",
            {
                "model": self.invoice.commercial_partner_id._name,
                "res_id": self.invoice.commercial_partner_id.id,
            },
        )
        uuid = str(uuid4())
        uuid2 = str(uuid4())
        record._set_file_content(
            json.dumps(
                {
                    "id": uuid,
                    "contacts": [
                        {
                            "id": uuid2,
                            "externalId": contact1.id,
                        }
                    ],
                }
            ),
            field_name="ws_response_content",
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(self.invoice.commercial_partner_id.upflow_uuid, uuid)
        self.assertEqual(contact1.upflow_uuid, uuid2)

    def test_upflow_post_customers_check_contact_null_external_id(self):
        contact1 = self.env["res.partner"].create({"name": "test 1"})
        self.invoice.commercial_partner_id.child_ids = [(6, 0, [contact1.id])]
        record = self.backend.create_record(
            "upflow_post_customers",
            {
                "model": self.invoice.commercial_partner_id._name,
                "res_id": self.invoice.commercial_partner_id.id,
            },
        )
        uuid = str(uuid4())
        uuid2 = str(uuid4())
        record._set_file_content(
            json.dumps(
                {
                    "id": uuid,
                    "contacts": [
                        {
                            "id": uuid2,
                            "externalId": None,
                        }
                    ],
                }
            ),
            field_name="ws_response_content",
        )
        record.ws_response_status_code = 200
        with self.assertLogs(check_upflow_post_customer_logger, level="WARNING") as log:
            self.backend._exchange_output_check_state(record)
        self.assertIn(
            "WARNING:odoo.addons.edi_upflow.components"
            ".edi_output_check_upflow_post_customers:"
            "No externalId found for contact %s" % uuid2,
            log.output,
        )
        self.assertNotEqual(contact1.upflow_uuid, uuid2)

    def test_upflow_put_contacts_match_generate(self):
        contact = self.env["res.partner"].create(
            {"name": "test 1", "email": "test@foodles.co"}
        )
        self.partner.child_ids = [(6, 0, [contact.id])]
        record = self.backend.create_record(
            "upflow_put_contacts",
            {
                "model": contact._name,
                "res_id": contact.id,
            },
        )
        generated_content = '{"some": "value"}'
        with mock.patch(
            "odoo.addons.edi_upflow.components"
            ".edi_output_generate_upflow_put_contacts"
            ".EdiOutputGenerateUpflowPutContacts.generate",
            return_value=generated_content,
        ) as m_generate:
            self.backend.exchange_generate(record)
            m_generate.assert_called_once()
        self.assertEqual(record._get_file_content(), generated_content)

    @mock.patch(
        "odoo.addons.base_upflow.models.res_partner.Partner"
        ".get_upflow_api_post_contacts_payload",
        return_value={"some": "value"},
    )
    def test_upflow_put_contacts_call_post_contact_payload(self, m_payload):
        contact = self.env["res.partner"].create(
            {"name": "test 1", "email": "test@foodles.co"}
        )
        self.partner.child_ids = [(6, 0, [contact.id])]
        record = self.backend.create_record(
            "upflow_put_contacts",
            {
                "model": contact._name,
                "res_id": contact.id,
            },
        )
        self.backend.exchange_generate(record)
        m_payload.assert_called_once()
        self.assertEqual(record._get_file_content(), json.dumps({"some": "value"}))

    def test_upflow_put_contacts_check(self):
        record = self.backend.create_record(
            "upflow_put_contacts",
            {
                "model": self.partner._name,
                "res_id": self.partner.id,
            },
        )
        uuid = str(uuid4())
        record._set_file_content(
            json.dumps({"id": uuid}), field_name="ws_response_content"
        )
        record.ws_response_status_code = 200
        self.backend._exchange_output_check_state(record)
        self.assertEqual(record.edi_exchange_state, "output_sent_and_processed")
        self.assertEqual(self.partner.upflow_uuid, uuid)
