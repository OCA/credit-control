from odoo.tests.common import tagged

from odoo.addons.edi_upflow.components.edi_output_generate_upflow_post_customers import (
    EdiOutputGenerateUpflowPostCustomersError,
)
from odoo.addons.edi_upflow.components.edi_output_generate_upflow_post_reconcile import (
    EdiOutputGenerateUpflowPostReconcileError,
)

from .common import EDIUpflowCommonCase


@tagged("post_install", "-at_install")
class TestEdiUpflowError(EDIUpflowCommonCase):
    def test_generate_post_reconcile_with_nothing_to_reconcile(self):
        partial_reconcile = self.env["account.partial.reconcile"].browse()
        record = self.backend.create_record(
            "upflow_post_reconcile",
            {
                "model": partial_reconcile._name,
                "res_id": partial_reconcile.id,
            },
        )
        with self.assertRaisesRegex(
            EdiOutputGenerateUpflowPostReconcileError,
            "No record found to generate the payload.",
        ):
            record.action_exchange_generate()

    def test_generate_post_customers_with_no_customer(self):
        customer = self.env["res.partner"].browse()
        record = self.backend.create_record(
            "upflow_post_customers",
            {
                "model": customer._name,
                "res_id": customer.id,
            },
        )
        with self.assertRaisesRegex(
            EdiOutputGenerateUpflowPostCustomersError,
            "No record found to generate the payload.",
        ):
            record.action_exchange_generate()
