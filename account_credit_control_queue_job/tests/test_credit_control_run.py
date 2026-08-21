# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_credit_control.tests.test_credit_control_run import (
    TestCreditControlRunCase,
)


@tagged("post_install", "-at_install")
class TestCreditControlRun(TestCreditControlRunCase):
    def test_sent_email_in_job(self):
        self.invoice.partner_id.email = "test@test.com"
        control_run = self.env["credit.control.run"].create(
            {"date": fields.Date.today(), "policy_ids": [(6, 0, [self.policy.id])]}
        )
        control_run.generate_credit_lines()
        self.assertTrue(len(self.invoice.credit_control_line_ids), 1)
        control_lines = self.invoice.credit_control_line_ids
        marker = self.env["credit.control.marker"].create(
            {"name": "to_be_sent", "line_ids": [(6, 0, control_lines.ids)]}
        )
        marker.mark_lines()
        wiz_emailer = self.env["credit.control.emailer"].create({})
        wiz_emailer.line_ids = control_lines

        wiz_emailer.email_lines()

        communications = control_lines.communication_id
        self.assertTrue(communications)
        domain = [("method_name", "=", "_send_communications_by_email")]
        jobs = self.env["queue.job"].sudo().search(domain)
        self.assertEqual(len(jobs), len(communications))
