# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_credit_control.tests.test_credit_control_run import (
    TestCreditControlRunCase,
)


@tagged("post_install", "-at_install")
class TestCreditControlBatching(TestCreditControlRunCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company.credit_policy_id = cls.policy

        cls.partner2 = cls.env["res.partner"].create(
            {
                "name": "Test Partner 2",
                "email": "test2@test.com",
                "property_account_receivable_id": cls.account.id,
            }
        )
        cls.partner3 = cls.env["res.partner"].create(
            {
                "name": "Test Partner 3",
                "email": "test3@test.com",
                "property_account_receivable_id": cls.account.id,
            }
        )

        (cls.partner | cls.partner2 | cls.partner3).write({"email": "test@example.com"})

        past_date = fields.Date.from_string("2024-01-01")

        cls.invoices = cls.env["account.move"]
        partners = [
            cls.partner,
            cls.partner,
            cls.partner2,
            cls.partner2,
            cls.partner3,
            cls.partner3,
            cls.partner,
        ]

        for _i, partner in enumerate(partners):
            inv = cls._create_invoice(
                partner_id=partner.id,
                post=True,
                invoice_date=past_date,
                invoice_date_due=past_date,
            )
            cls.invoices |= inv

    def _run_test_logic(self):
        """Helper function to run the core test logic."""
        run_company = self.company

        control_run = self.env["credit.control.run"].create(
            {
                "date": fields.Date.today(),
                "policy_ids": [(6, 0, [self.policy.id])],
                "company_id": run_company.id,
            }
        )

        control_run.generate_credit_lines()

        all_lines = self.invoices.mapped("credit_control_line_ids")
        self.assertEqual(len(all_lines), 7, "Should have found 7 credit lines.")

        marker = self.env["credit.control.marker"].create(
            {"name": "to_be_sent", "line_ids": [(6, 0, all_lines.ids)]}
        )
        marker.mark_lines()

        wiz_emailer = self.env["credit.control.emailer"].create({})
        wiz_emailer.line_ids = all_lines
        wiz_emailer.email_lines()

        batches = self.env["queue.job.batch"].sudo().search([])
        self.assertEqual(len(batches), 3)

        jobs = (
            self.env["queue.job"].sudo().search([("job_batch_id", "in", batches.ids)])
        )
        return jobs

    def test_batching_logic(self):
        """
        Test that with 3 communications and a batch size of 3,
        one batch with 1 job is created.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "account_credit_control_queue_job.batch_size", "3"
        )

        jobs = self._run_test_logic()
        self.assertEqual(len(jobs), 3)

    def test_batch_size_one(self):
        """
        Test that with 3 communications and a batch size of 1,
        one batch with 3 jobs is created.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "account_credit_control_queue_job.batch_size", "1"
        )

        jobs = self._run_test_logic()
        self.assertEqual(len(jobs), 3)

    def test_invalid_batch_size_config(self):
        """
        Test that if batch size is not an integer, it falls back to 1,
        creating one batch with 3 jobs.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "account_credit_control_queue_job.batch_size", "invalid_value"
        )

        jobs = self._run_test_logic()
        self.assertEqual(len(jobs), 3)
