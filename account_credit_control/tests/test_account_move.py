# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from dateutil import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountInvoice(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.env.user.groups_id |= cls.env.ref(
            "account_credit_control.group_account_credit_control_manager"
        )

    def test_action_cancel(self):
        """
        Test the method action_cancel on invoice
        We will create an old invoice, generate a control run
        and check if I can unlink this invoice
        """
        journal = self.company_data["default_journal_sale"]

        account_type_rec = self.env.ref("account.data_account_type_receivable")
        account = self.env["account.account"].create(
            {
                "code": "TEST430",
                "name": "Clients (test)",
                "user_type_id": account_type_rec.id,
                "reconcile": True,
            }
        )

        tag_operation = self.env.ref("account.account_tag_operating")
        account_type_inc = self.env.ref("account.data_account_type_revenue")
        analytic_account = self.env["account.account"].create(
            {
                "code": "TEST700",
                "name": "Ventes en Belgique (test)",
                "user_type_id": account_type_inc.id,
                "reconcile": True,
                "tag_ids": [(6, 0, [tag_operation.id])],
            }
        )
        payment_term = self.env.ref("account.account_payment_term_immediate")

        product = self.env["product.product"].create({"name": "Product test"})

        policy = self.env.ref("account_credit_control.credit_control_3_time")
        policy.write({"account_ids": [(6, 0, [account.id])]})

        # There is a bug with Odoo ...
        # The field "credit_policy_id" is considered as an "old field" and
        # the field property_account_receivable_id like a "new field"
        # The ORM will create the record with old field
        # and update the record with new fields.
        # However constrains are applied after the first creation.
        partner = self.env["res.partner"].create(
            {"name": "Partner", "property_account_receivable_id": account.id}
        )
        partner.credit_policy_id = policy.id

        date_invoice = datetime.today() - relativedelta.relativedelta(years=1)

        # Create an invoice
        invoice_form = Form(
            self.env["account.move"].with_context(
                default_move_type="out_invoice", check_move_validity=False
            )
        )
        invoice_form.invoice_date = date_invoice
        invoice_form.invoice_date_due = date_invoice
        invoice_form.partner_id = partner
        invoice_form.journal_id = journal
        invoice_form.invoice_payment_term_id = payment_term

        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = product
            invoice_line_form.quantity = 1
            invoice_line_form.price_unit = 500
            invoice_line_form.account_id = analytic_account
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()

        invoice.action_post()

        control_run = self.env["credit.control.run"].create(
            {"date": fields.Date.today(), "policy_ids": [(6, 0, [policy.id])]}
        )
        control_run.generate_credit_lines()

        self.assertEqual(len(invoice.credit_control_line_ids), 1)
        control_line = invoice.credit_control_line_ids

        control_marker = self.env["credit.control.marker"]
        marker_line = control_marker.with_context(
            active_model="credit.control.line", active_ids=[control_line.id]
        )._default_lines()

        self.assertIn(control_line, marker_line)

        marker = self.env["credit.control.marker"].create(
            {"name": "to_be_sent", "line_ids": [(6, 0, [control_line.id])]}
        )
        marker.mark_lines()

        with self.assertRaises(UserError):
            invoice.button_cancel()

    def test_action_cancel_draft_credit_lines(self):
        """
        Test the method action_cancel on invoice
        We will create an old invoice, generate a control run
        and check if I can unlink this invoice
        """
        journal = self.company_data["default_journal_sale"]

        account_type_rec = self.env.ref("account.data_account_type_receivable")
        account = self.env["account.account"].create(
            {
                "code": "TEST430",
                "name": "Clients (test)",
                "user_type_id": account_type_rec.id,
                "reconcile": True,
            }
        )

        tag_operation = self.env.ref("account.account_tag_operating")
        account_type_inc = self.env.ref("account.data_account_type_revenue")
        analytic_account = self.env["account.account"].create(
            {
                "code": "TEST700",
                "name": "Ventes en Belgique (test)",
                "user_type_id": account_type_inc.id,
                "reconcile": True,
                "tag_ids": [(6, 0, [tag_operation.id])],
            }
        )
        payment_term = self.env.ref("account.account_payment_term_immediate")

        product = self.env["product.product"].create({"name": "Product test"})

        policy = self.env.ref("account_credit_control.credit_control_3_time")
        policy.write({"account_ids": [(6, 0, [account.id])]})

        # There is a bug with Odoo ...
        # The field "credit_policy_id" is considered as an "old field" and
        # the field property_account_receivable_id like a "new field"
        # The ORM will create the record with old field
        # and update the record with new fields.
        # However constrains are applied after the first creation.
        partner = self.env["res.partner"].create(
            {"name": "Partner", "property_account_receivable_id": account.id}
        )
        partner.credit_policy_id = policy.id

        date_invoice = datetime.today() - relativedelta.relativedelta(years=1)

        # Create an invoice
        invoice_form = Form(
            self.env["account.move"].with_context(
                default_move_type="out_invoice", check_move_validity=False
            )
        )
        invoice_form.invoice_date = date_invoice
        invoice_form.invoice_date_due = date_invoice
        invoice_form.partner_id = partner
        invoice_form.journal_id = journal
        invoice_form.invoice_payment_term_id = payment_term

        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = product
            invoice_line_form.quantity = 1
            invoice_line_form.price_unit = 500
            invoice_line_form.account_id = analytic_account
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()

        invoice.action_post()

        control_run = self.env["credit.control.run"].create(
            {"date": fields.Date.today(), "policy_ids": [(6, 0, [policy.id])]}
        )

        # Draft Lines
        control_run.generate_credit_lines()
        self.assertTrue(len(invoice.credit_control_line_ids), 1)

        invoice.button_cancel()

    def test_invoice_policy_wiz(self):
        """
        Test the wizard to change default credit policy on invoice
        We will create an invoice, change credit policy and check
        if it has change the policy on invoice
        """
        journal = self.company_data["default_journal_sale"]

        account_type_rec = self.env.ref("account.data_account_type_receivable")
        account = self.env["account.account"].create(
            {
                "code": "TEST430",
                "name": "Clients (test)",
                "user_type_id": account_type_rec.id,
                "reconcile": True,
            }
        )

        tag_operation = self.env.ref("account.account_tag_operating")
        account_type_inc = self.env.ref("account.data_account_type_revenue")
        analytic_account = self.env["account.account"].create(
            {
                "code": "TEST700",
                "name": "Ventes en Belgique (test)",
                "user_type_id": account_type_inc.id,
                "reconcile": True,
                "tag_ids": [(6, 0, [tag_operation.id])],
            }
        )
        payment_term = self.env.ref("account.account_payment_term_immediate")

        product = self.env["product.product"].create({"name": "Product test"})

        policy = self.env.ref("account_credit_control.credit_control_2_time")
        policy.write({"account_ids": [(6, 0, [account.id])]})

        # There is a bug with Odoo ...
        # The field "credit_policy_id" is considered as an "old field" and
        # the field property_account_receivable_id like a "new field"
        # The ORM will create the record with old field
        # and update the record with new fields.
        # However constrains are applied after the first creation.
        partner = self.env["res.partner"].create(
            {"name": "Partner", "property_account_receivable_id": account.id}
        )
        partner.credit_policy_id = policy.id

        date_invoice = datetime.today() - relativedelta.relativedelta(years=1)

        # Create an invoice
        invoice_form = Form(
            self.env["account.move"].with_context(
                default_move_type="out_invoice", check_move_validity=False
            )
        )
        invoice_form.invoice_date = date_invoice
        invoice_form.invoice_date_due = date_invoice
        invoice_form.partner_id = partner
        invoice_form.journal_id = journal
        invoice_form.invoice_payment_term_id = payment_term

        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = product
            invoice_line_form.quantity = 1
            invoice_line_form.price_unit = 500
            invoice_line_form.account_id = analytic_account
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()

        invoice.action_post()

        control_run = self.env["credit.control.run"].create(
            {"date": fields.Date.today(), "policy_ids": [(6, 0, [policy.id])]}
        )
        control_run.generate_credit_lines()

        new_policy = self.env.ref("account_credit_control.credit_control_2_time")
        days_30 = self.env.ref("account_credit_control.2_time_1")
        wiz_obj = self.env["credit.control.policy.changer"]
        wiz_rec = wiz_obj.with_context(active_ids=invoice.ids).create(
            {"new_policy_id": new_policy.id, "new_policy_level_id": days_30.id}
        )

        # Verify the lines on wiz belongs to same invoice
        self.assertEqual(wiz_rec.move_line_ids.move_id, invoice)

        # Execute change
        wiz_rec.set_new_policy()

        # Verify on invoice the new policy
        self.assertEqual(invoice.credit_control_line_ids[0].policy_id, new_policy)

        # Verify new level
        self.assertEqual(invoice.credit_control_line_ids[0].policy_level_id, days_30)
