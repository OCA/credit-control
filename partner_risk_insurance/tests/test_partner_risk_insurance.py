# Copyright 2018 Tecnativa - Sergio Teruel
# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import Form, TransactionCase, tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("post_install", "-at_install")
class TestSaleOrderLineInput(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test",
                "company_credit_limit": 100.00,
                "insurance_credit_limit": 50.00,
            }
        )

    def test_credit_limit(self):
        self.assertEqual(self.partner.credit_limit, 150.00)
        # set global credit_limit
        form = Form(self.env["res.config.settings"].sudo())
        form.account_use_credit_limit = True
        form.account_default_credit_limit = 100
        form.save()
        # update company_credit_limit
        self.partner.company_credit_limit = 200
        self.assertEqual(self.partner.credit_limit, 350.00)  # 350 = 100 + 200 + 50
