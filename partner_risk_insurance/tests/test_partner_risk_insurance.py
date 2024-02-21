# Copyright 2018 Tecnativa - Sergio Teruel
# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, TransactionCase, new_test_user, tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("post_install", "-at_install")
class TestSaleOrderLineInput(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            user=new_test_user(
                cls.env,
                "inv_user",
                "base.group_partner_manager,account.group_account_invoice",
            ),
            context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT),
        )
        # set global credit_limit
        cls.env["res.config.settings"].sudo().create(
            {
                "account_use_credit_limit": True,
                "account_default_credit_limit": 100,
            }
        )

    def test_default_company_credit_limit(self):
        partner_f = Form(self.env["res.partner"])
        partner_f.name = "You"
        # Checkbox in Invoicing tab stays false because partner still keeps
        # the default limit from company settings
        self.assertFalse(partner_f.use_partner_credit_limit)
        # User navigates to Credit Insurance tab
        self.assertEqual(partner_f.credit_limit, 100.00)
        self.assertEqual(partner_f.company_credit_limit, 100.00)
        # User sets a custom credit limit; all is covered by us
        partner_f.credit_limit = 50
        self.assertEqual(partner_f.credit_limit, 50.00)
        self.assertEqual(partner_f.company_credit_limit, 50.00)
        # User sets some credit to be covered by insurance
        partner_f.insurance_credit_limit = 25
        self.assertEqual(partner_f.credit_limit, 50.00)
        self.assertEqual(partner_f.company_credit_limit, 25.00)
        # User sets a big insured limit, which forces the total limit to change
        partner_f.insurance_credit_limit = 100
        self.assertEqual(partner_f.credit_limit, 100.00)
        self.assertEqual(partner_f.company_credit_limit, 0.00)
        # After saving, all stays the same
        partner = partner_f.save()
        self.assertEqual(partner.credit_limit, 100.00)
        self.assertEqual(partner.company_credit_limit, 0.00)
        self.assertEqual(partner.insurance_credit_limit, 100.00)
