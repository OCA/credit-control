# Copyright 2026 Humanilog GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAllReceivable(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.user.groups_id |= cls.env.ref(
            "account_credit_control.group_account_credit_control_manager"
        )
        rec_type = cls.env.ref("account.data_account_type_receivable")
        # Individual debtor accounts, as created per partner (DATEV style)
        cls.debtor_1 = cls.env["account.account"].create(
            {
                "code": "10001",
                "name": "Debitor 1",
                "user_type_id": rec_type.id,
                "reconcile": True,
            }
        )
        cls.debtor_2 = cls.debtor_1.copy({"code": "10002", "name": "Debitor 2"})
        cls.partner_1 = cls.env["res.partner"].create(
            {"name": "Kunde 1", "property_account_receivable_id": cls.debtor_1.id}
        )
        cls.partner_2 = cls.env["res.partner"].create(
            {"name": "Kunde 2", "property_account_receivable_id": cls.debtor_2.id}
        )
        cls.policy = cls.env.ref("account_credit_control.credit_control_3_time")
        cls.policy.write({"account_ids": [(5, 0)], "all_receivable_accounts": True})
        cls.env.company.credit_policy_id = cls.policy
        cls.invoices = cls.env["account.move"]
        for partner in (cls.partner_1, cls.partner_2):
            cls.invoices |= cls.init_invoice(
                "out_invoice",
                partner=partner,
                invoice_date=fields.Date.from_string("2026-01-01"),
                amounts=[100.0],
                post=True,
            )

    def _run(self):
        run = self.env["credit.control.run"].create(
            {
                "date": fields.Date.from_string("2026-06-01"),
                "policy_ids": [(6, 0, [self.policy.id])],
            }
        )
        run.with_context(lang="en_US").generate_credit_lines()
        return run

    def test_all_receivable_accounts(self):
        run = self._run()
        self.assertEqual(
            run.line_ids.mapped("partner_id"), self.partner_1 | self.partner_2
        )
        self.assertEqual(
            run.line_ids.mapped("account_id"), self.debtor_1 | self.debtor_2
        )

    def test_new_account_included_automatically(self):
        debtor_3 = self.debtor_1.copy({"code": "10003", "name": "Debitor 3"})
        partner_3 = self.env["res.partner"].create(
            {"name": "Kunde 3", "property_account_receivable_id": debtor_3.id}
        )
        self.init_invoice(
            "out_invoice",
            partner=partner_3,
            invoice_date=fields.Date.from_string("2026-01-01"),
            amounts=[50.0],
            post=True,
        )
        run = self._run()
        self.assertIn(partner_3, run.line_ids.mapped("partner_id"))

    def test_flag_off_uses_account_list(self):
        self.policy.write(
            {
                "all_receivable_accounts": False,
                "account_ids": [(6, 0, self.debtor_1.ids)],
            }
        )
        run = self._run()
        self.assertEqual(run.line_ids.mapped("partner_id"), self.partner_1)

    def test_partner_policy_allowed(self):
        # Must not raise although the account is not listed on the policy
        self.partner_1.credit_policy_id = self.policy
        self.assertEqual(self.partner_1.credit_policy_id, self.policy)

    def test_constraint_requires_accounts(self):
        with self.assertRaises(ValidationError):
            self.policy.all_receivable_accounts = False

    def test_partner_policy_not_allowed_without_flag(self):
        self.policy.write(
            {
                "all_receivable_accounts": False,
                "account_ids": [(6, 0, self.debtor_2.ids)],
            }
        )
        with self.assertRaises(ValidationError):
            self.partner_1.credit_policy_id = self.policy

    def test_non_receivable_account_not_allowed(self):
        payable = self.company_data["default_account_payable"]
        with self.assertRaises(UserError):
            self.policy.check_policy_against_account(payable)

    def test_form_view(self):
        self.policy.write(
            {
                "all_receivable_accounts": False,
                "account_ids": [(6, 0, self.debtor_1.ids)],
            }
        )
        with Form(self.policy) as form:
            form.all_receivable_accounts = True
        self.assertTrue(self.policy.all_receivable_accounts)
