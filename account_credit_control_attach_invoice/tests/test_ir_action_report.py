import io
from unittest.mock import patch

import PyPDF2

from odoo import Command
from odoo.fields import Datetime

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestIrActionsReport(SavepointCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["ir.actions.report"].search(
            [("report_name", "=", "account.report_with_payments")]
        )
        cls.company = cls.env.user.company_id
        cls.partner = cls.env["res.partner"].create({"name": "test"})
        cls.credit_control_policy = cls.env["credit.control.policy"].create(
            {"name": "Policy Test"}
        )
        cls.mail_template = cls.env["mail.template"].create(
            {
                "name": "Test template",
                "subject": "{{ 1 + 5 }}",
                "body_html": '<t t-out="4 + 9"/>',
                "lang": "{{ object.lang }}",
                "auto_delete": True,
                "model_id": cls.env.ref("base.model_res_partner").id,
            }
        )
        cls.credit_control_policy_level = cls.env["credit.control.policy.level"].create(
            {
                "name": "Policy Level Test",
                "policy_id": cls.credit_control_policy.id,
                "level": 1,
                "computation_mode": "net_days",
                "delay_days": 2,
                "email_template_id": cls.mail_template.id,
                "channel": "email",
                "custom_mail_text": "<t t-out='4 + 9'/>",
                "custom_text": "<t t-out='4 + 9'/>",
            }
        )
        cls.credit_control = cls.env["credit.control.communication"].create(
            {
                "partner_id": cls.partner.id,
                "policy_level_id": cls.credit_control_policy_level.id,
                "currency_id": cls.env.user.company_id.currency_id.id,
            }
        )
        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "line_ids": [Command.create({"quantity": 1, "price_unit": 12.30})],
            }
        )
        cls.credit_control.write(
            {
                "credit_control_line_ids": [
                    (
                        0,
                        0,
                        {
                            "invoice_id": cls.invoice.id,
                            "partner_id": cls.partner.id,
                            "move_line_id": cls.invoice.line_ids[0].id,
                            "policy_level_id": cls.credit_control_policy_level.id,
                            "channel": "email",
                            "date": Datetime.now(),
                            "date_due": Datetime.now(),
                            "amount_due": 25,
                            "balance_due": 25,
                        },
                    )
                ]
            }
        )

    @patch("odoo.addons.base.models.ir_actions_report.IrActionsReport._render_qweb_pdf")
    def test_render_qweb_pdf_with_attached_report(self, mock_render_qweb_pdf):
        """
        Test that the PDF merging occurs when
        credit_control_report_to_attach_id is true.
        """
        self.company.credit_control_report_to_attach_id = self.report
        mock_render_qweb_pdf.side_effect = lambda x, res_ids, data=None: (
            b"PDF_CONTENT",
            "pdf",
        )
        pdf, pdf_type = self.report._render_qweb_pdf(
            "account_credit_control.report_credit_control_summary",
            [self.credit_control.id],
        )
        self.assertEqual(pdf_type, "pdf")
        self.assertTrue(isinstance(pdf, bytes))

    def test_merge_pdf_in_memory(self):
        """Test that multiple PDFs are merged correctly."""
        writer = PyPDF2.PdfFileWriter()
        writer.addBlankPage(width=200, height=200)
        pdf_stream = io.BytesIO()
        writer.write(pdf_stream)

        merged_pdf = self.report.merge_pdf_in_memory([pdf_stream, pdf_stream])
        self.assertTrue(isinstance(merged_pdf, bytes))
        reader = PyPDF2.PdfFileReader(io.BytesIO(merged_pdf))
        self.assertEqual(reader.getNumPages(), 2)

    @patch("odoo.addons.base.models.ir_actions_report.IrActionsReport._render_qweb_pdf")
    def test_render_qweb_pdf_without_attached_report(self, mock_render_qweb_pdf):
        """
        Test that the report is generated normally when
        credit_control_report_to_attach_id is false.
        """
        self.company.credit_control_report_to_attach_id = False
        mock_render_qweb_pdf.side_effect = lambda x, res_ids, data=None: (
            b"PDF_CONTENT",
            "pdf",
        )
        pdf, pdf_type = self.report._render_qweb_pdf(
            "account_credit_control.report_credit_control_summary",
            [self.credit_control.id],
        )
        self.assertEqual(pdf_type, "pdf")
        self.assertEqual(pdf, b"PDF_CONTENT")
