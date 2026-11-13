# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo.tests import tagged

from .test_credit_control_run import TestCreditControlRunCase


@tagged("post_install", "-at_install")
class TestCreditControlCommunication(TestCreditControlRunCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a second invoice for the same partner to test aggregation
        cls.invoice2 = cls.invoice.copy(
            {
                "invoice_date": "2025-09-01",
                "invoice_date_due": "2025-09-01",
            }
        )
        cls.invoice2.action_post()

        # Generate credit lines for both invoices
        control_run = cls.env["credit.control.run"].create(
            {"date": "2025-11-13", "policy_ids": [(6, 0, [cls.policy.id])]}
        )
        control_run.generate_credit_lines()
        cls.credit_lines = cls.invoice.credit_control_line_ids
        cls.credit_lines |= cls.invoice2.credit_control_line_ids

    def test_communication_aggregation_and_totals(self):
        """Test that lines are aggregated correctly into one communication."""
        self.assertEqual(len(self.credit_lines), 2)
        comm_model = self.env["credit.control.communication"]
        communications = comm_model._generate_comm_from_credit_lines(self.credit_lines)

        self.assertEqual(
            len(communications),
            1,
            "Should create only one communication for the same partner, policy, "
            "and currency.",
        )

        comm = communications[0]
        self.assertEqual(comm.partner_id, self.invoice.partner_id)
        self.assertEqual(len(comm.credit_control_line_ids), 2)

        # Check computed totals
        expected_total_due = sum(self.credit_lines.mapped("balance_due"))
        expected_total_invoiced = sum(self.credit_lines.mapped("amount_due"))
        self.assertAlmostEqual(comm.total_due, expected_total_due)
        self.assertAlmostEqual(comm.total_invoiced, expected_total_invoiced)

    def test_get_emailing_contact(self):
        """Test the logic for finding the correct contact for emailing."""
        comm = self.env[
            "credit.control.communication"
        ]._generate_comm_from_credit_lines(self.credit_lines)
        partner = self.invoice.partner_id
        contact = comm.contact_address_id

        # Case 1: Contact has an email
        contact.email = "contact@test.com"
        partner.email = "partner@test.com"
        self.assertEqual(comm.get_emailing_contact(), contact)

        # Case 2: Contact has no email, fallback to commercial partner
        contact.email = False
        self.assertEqual(comm.get_emailing_contact(), partner)

    def test_mail_composer_table_injection(self):
        """Test that the invoice summary table is injected into the email body."""
        comm = self.env[
            "credit.control.communication"
        ]._generate_comm_from_credit_lines(self.credit_lines)
        comm.policy_level_id.mail_show_invoice_detail = True

        composer = (
            self.env["mail.compose.message"]
            .with_context(
                default_model="credit.control.communication",
                default_res_ids=[comm.id],
                inject_credit_control_communication_table=True,
            )
            .create({})
        )

        # Trigger the _compute_body method
        body = composer.body
        self.assertIn("<h3>Invoices summary</h3>", body)
        self.assertIn(self.invoice.name, body)
        self.assertIn(self.invoice2.name, body)

        # Test with a pre-existing body
        initial_body = Markup("<p>Initial content.</p>")
        composer.body = initial_body
        composer._compute_body()
        self.assertIn(initial_body, composer.body)
        self.assertIn("<h3>Invoices summary</h3>", composer.body)
