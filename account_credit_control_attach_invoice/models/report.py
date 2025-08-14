# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import io
from io import BytesIO

import PyPDF2

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        report_xml_id = report.xml_id
        reports = [
            "account_credit_control.report_credit_control_summary",
            "account_credit_control.credit_control_summary",
        ]
        if (
            report_xml_id in reports
            and self.env.user.company_id.credit_control_report_to_attach_id
        ):
            io_list = []
            for comm in self.env["credit.control.communication"].browse(res_ids):
                comm_pdf, _ = super()._render_qweb_pdf(report_ref, comm.id, data)
                io_list.append(io.BytesIO(comm_pdf))
                invoices = comm.mapped("credit_control_line_ids.invoice_id")
                inv_report = self.env.user.company_id.credit_control_report_to_attach_id
                for inv in invoices:
                    invoice_pdf, _ = inv_report._render_qweb_pdf(
                        inv_report.xml_id, data=data, res_ids=[inv.id]
                    )
                    io_list.append(io.BytesIO(invoice_pdf))
            pdf = self.merge_pdf_in_memory(io_list)
            for io_file in io_list:
                io_file.close()
            return (pdf, "pdf")
        else:
            return super()._render_qweb_pdf(report_ref, res_ids, data)

    def merge_pdf_in_memory(self, docs):
        if not docs:
            return b""
        streams = []
        writer = PyPDF2.PdfFileWriter()
        for doc in docs:
            if doc:
                doc.seek(0)
                current_buff = BytesIO()
                streams.append(current_buff)
                current_buff.write(doc.read())
                current_buff.seek(0)
                reader = PyPDF2.PdfFileReader(current_buff)
                for page in range(reader.getNumPages()):
                    writer.addPage(reader.getPage(page))
            else:
                writer.addBlankPage()
        buff = BytesIO()
        try:
            # The writer close the reader file here
            writer.write(buff)
            return buff.getvalue()
        except OSError:
            raise
        finally:
            buff.close()
            for stream in streams:
                stream.close()
