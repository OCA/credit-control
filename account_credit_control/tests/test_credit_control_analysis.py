# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from dateutil import relativedelta

from odoo import fields
from odoo.tests import tagged

from .test_credit_control_run import TestCreditControlRunCase


@tagged("post_install", "-at_install")
class TestCreditControlAnalysis(TestCreditControlRunCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create more data for analysis
        # Invoice 2 for the same partner, will generate a level 2 line later
        cls.invoice2 = cls.invoice.copy(
            {
                "invoice_date": datetime.today()
                - relativedelta.relativedelta(months=7),
                "invoice_date_due": datetime.today()
                - relativedelta.relativedelta(months=7),
            }
        )
        cls.invoice2.action_post()

        # Run 1: generates level 1 for invoice 1 and level 2 for invoice 2
        first_run_date = fields.Date.to_string(
            datetime.today() - relativedelta.relativedelta(months=5)
        )
        control_run_1 = cls.env["credit.control.run"].create(
            {"date": first_run_date, "policy_ids": [(6, 0, [cls.policy.id])]}
        )
        control_run_1.generate_credit_lines()

        # Run 2: generates level 2 for invoice 1 and level 3 for invoice 2
        second_run_date = fields.Date.to_string(
            datetime.today() - relativedelta.relativedelta(months=2)
        )
        control_run_2 = cls.env["credit.control.run"].create(
            {"date": second_run_date, "policy_ids": [(6, 0, [cls.policy.id])]}
        )
        control_run_2.generate_credit_lines()

    def test_analysis_view_content(self):
        """Test the content of the credit.control.analysis SQL view."""
        # Flush to ensure the view is updated with the latest data
        self.env.cr.flush()

        analysis_records = self.env["credit.control.analysis"].search(
            [("partner_id", "=", self.invoice.partner_id.id)]
        )

        self.assertEqual(
            len(analysis_records),
            1,
            "Should be one analysis record per partner/policy/currency.",
        )

        analysis = analysis_records[0]
        partner_lines = self.env["credit.control.line"].search(
            [("partner_id", "=", self.invoice.partner_id.id)]
        )

        # Find the highest level among the partner's credit lines
        max_level = max(partner_lines.mapped("level"))
        highest_level_line = partner_lines.filtered(
            lambda pl: pl.level == max_level
        ).sorted("id", reverse=True)[0]

        # The analysis should reflect the highest level reached
        self.assertEqual(analysis.level, max_level)
        self.assertEqual(analysis.policy_level_id, highest_level_line.policy_level_id)

        # The open_balance should be the sum of all open move lines for that partner
        total_open_balance = (
            self.invoice.amount_residual + self.invoice2.amount_residual
        )
        self.assertAlmostEqual(
            analysis.open_balance,
            total_open_balance,
            "Open balance should be the sum of all open amounts for the partner.",
        )
