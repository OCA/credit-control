from uuid import uuid4

from odoo.tests.common import tagged

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import EDIUpflowCommonCase


@tagged("post_install", "-at_install")
class TestNoCompanyBackendSet(EDIUpflowCommonCase):
    """Invoices flows POST v1/invoices"""

    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.invoice = cls._create_invoice(auto_validate=False)
        cls.env.company.upflow_backend_id = False

    def test_post_invoice_do_not_create_exchange_record(self):
        domain = [
            ("model", "=", "account.move"),
            ("res_id", "=", self.invoice.id),
            (
                "type_id",
                "=",
                self.env.ref("edi_upflow.upflow_edi_exchange_type_post_invoices").id,
            ),
        ]
        self.assertEqual(self.env["edi.exchange.record"].search_count(domain), 0)

        with trap_jobs() as trap:
            self.invoice.action_post()
            trap.assert_jobs_count(0, only=self.backend.exchange_generate)
        self.assertEqual(self.env["edi.exchange.record"].search_count(domain), 0)

    def test_on_create_account_full_reconcile_do_not_create_exchange_record(self):
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
            self.invoice.action_post()
            self._register_manual_payment_reconciled(self.invoice)
            trap.assert_jobs_count(0, only=self.backend.exchange_generate)
        self.assertEqual(self.env["edi.exchange.record"].search_count(domain), 0)

    def test_post_invoice_on_already_synched_customer_create_exchange_record(self):
        self.partner.upflow_edi_backend_id = self.backend
        self.partner.upflow_uuid = str(uuid4())
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
            # 1 invoice + 1 PDF=> 2 jobs
            trap.assert_jobs_count(2, only=self.backend.exchange_generate)
        records = self.env["edi.exchange.record"].search(domain)
        self.assertEqual(len(records), 1)
        self.assertEqual(records.edi_exchange_state, "new")
