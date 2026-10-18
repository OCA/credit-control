# Copyright 2024 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import exceptions
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestInvoiceCreditPolicy(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.policy_state = cls.env["credit.policy.state"].create(
            {"name": "Insurance Policy", "insure_invoices": True}
        )
        cls.policy_company = cls.env["credit.policy.company"].create(
            {"name": "Insurance Company"}
        )
        cls.partner_ins = cls.env["res.partner"].create(
            {
                "name": "Test Insurance Partner",
                "credit_policy_state_id": cls.policy_state.id,
                "credit_policy_company_id": cls.policy_company.id,
            }
        )

    def test_insured_out_invoice(self):
        # Create an invoice without partner
        out_inv = self.init_invoice("out_invoice", partner=self.partner_a)
        with Form(out_inv) as out_inv_f:
            self.assertEqual(out_inv_f.insured_with_credit_policy, False)

            # Set partner
            out_inv_f.partner_id = self.partner_ins
            self.assertEqual(out_inv_f.insured_with_credit_policy, True)
            self.assertEqual(
                out_inv_f.credit_policy_company_id,
                self.partner_ins.credit_policy_company_id,
            )
            self.assertEqual(
                out_inv_f.credit_policy_state_id,
                self.partner_ins.credit_policy_state_id,
            )

            # Change partner policy
            self.partner_ins.credit_policy_state_id = False
            self.partner_ins.credit_policy_company_id = False
            self.assertEqual(out_inv_f.insured_with_credit_policy, True)
            self.assertEqual(out_inv_f.credit_policy_company_id, self.policy_company)
            self.assertEqual(out_inv_f.credit_policy_state_id, self.policy_state)

            # Deactivate insured invoice
            out_inv_f.insured_with_credit_policy = False
            self.assertEqual(out_inv_f.insured_with_credit_policy, False)

            # Try to reactivate insured invoice
            with self.assertRaises(exceptions.UserError):
                # Check raises on onchange
                out_inv_f.insured_with_credit_policy = True
            out_inv_f.insured_with_credit_policy = False

        self.partner_ins.credit_policy_state_id = self.policy_state
        self.partner_ins.credit_policy_company_id = self.policy_company
        self.assertEqual(out_inv.insured_with_credit_policy, False)
        self.assertEqual(out_inv.credit_policy_company_id.id, False)
        self.assertEqual(out_inv.credit_policy_state_id.id, False)

    def test_not_insured_other_invoices(self):
        move_types = self.env["account.move"].get_invoice_types(include_receipts=True)
        move_types.remove("out_invoice")
        for move_type in move_types:
            with self.subTest(move_type=move_type):
                inv_p_no_ins = self.init_invoice(move_type, partner=self.partner_a)
                self.assertEqual(inv_p_no_ins.insured_with_credit_policy, False)
                self.assertEqual(inv_p_no_ins.credit_policy_company_id.id, False)
                self.assertEqual(inv_p_no_ins.credit_policy_state_id.id, False)
                inv_p_ins = self.init_invoice(move_type, partner=self.partner_ins)
                self.assertEqual(inv_p_ins.insured_with_credit_policy, False)
                self.assertEqual(inv_p_ins.credit_policy_company_id.id, False)
                self.assertEqual(inv_p_ins.credit_policy_state_id.id, False)

    def test_print_invoices_by_risk(self):
        """The wizard prints the invoices of the dates"""
        self.env.company.external_report_layout_id = self.env.ref(
            "web.external_layout_standard"
        )
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_ins, amounts=[100], post=True
        )
        wizard = self.env["partner.risk.insurance.wizard"].create(
            {"date_from": invoice.date, "date_to": invoice.date}
        )
        action = wizard.action_print_report()
        self.assertEqual(action["context"]["active_ids"], invoice.ids)
        report = self.env.ref(
            "partner_risk_insurance.action_report_invoice_risk_insurance_template"
        )
        html = report._render_qweb_html(report.report_name, invoice.ids)[0].decode()
        self.assertIn("Test Insurance Partner", html)
        self.assertIn(invoice.name, html)
        wizard.date_from = wizard.date_to = invoice.date.replace(year=2000)
        with self.assertRaises(exceptions.ValidationError):
            wizard.action_print_report()
