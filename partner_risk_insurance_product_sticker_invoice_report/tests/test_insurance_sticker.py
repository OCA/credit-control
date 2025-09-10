# Copyright 2025 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo.addons.account_invoice_report_product_sticker.tests.common import (
    ProductStickerInvoiceReportCommon,
)


class SomethingCase(ProductStickerInvoiceReportCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.policy_state = cls.env["credit.policy.state"].create(
            {
                "name": "Insurance Policy",
                "insure_invoices": True,
            }
        )
        # Policy Company 1
        cls.policy_company_1 = cls.env["credit.policy.company"].create(
            {"name": "Credit Policy Company 1"}
        )
        cls.ps_ins_1 = cls.ps_global.copy()
        cls.ps_ins_1.name = "Policy Company 1 sticker"
        cls.ps_ins_1.credit_policy_company_id = cls.policy_company_1
        # Policy Company 2
        cls.policy_company_2 = cls.env["credit.policy.company"].create(
            {"name": "Credit Policy Company 2"}
        )
        cls.ps_ins_2 = cls.ps_global.copy()
        cls.ps_ins_2.name = "Policy Company 2 sticker"
        cls.ps_ins_2.credit_policy_company_id = cls.policy_company_2
        # Partner uses Policy Company 1
        cls.partner.credit_policy_state_id = cls.policy_state
        cls.partner.credit_policy_company_id = cls.policy_company_1

    def test_insurance_sticker_on_invoices(self):
        target_product = self.product_as400.product_variant_ids[0]
        out_invoice = self._create_invoice("out_invoice", [target_product])
        self.assertIn(
            self.ps_ins_1, out_invoice.sticker_ids, "Insurance sticker not found"
        )
        self.assertNotIn(
            self.ps_ins_2, out_invoice.sticker_ids, "Insurance Company 2 sticker found"
        )

    def test_insurance_sticker_not_on_invoices(self):
        self.partner.credit_policy_state_id.insure_invoices = False
        target_product = self.product_as400.product_variant_ids[0]
        out_invoice = self._create_invoice("out_invoice", [target_product])
        self.assertNotIn(
            self.ps_ins_1, out_invoice.sticker_ids, "Insurance sticker found"
        )
        self.assertNotIn(
            self.ps_ins_2, out_invoice.sticker_ids, "Insurance Company 2 sticker found"
        )
