# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOverdueWarn(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.bad_payer = self.env["res.partner"].create(
            {
                "name": "Bad payer",
                "country_id": self.env.ref("base.fr").id,
                "company_id": self.company.id,
            }
        )
        today = datetime.now().date()
        revenue_acc = self.env["account.account"].search(
            [
                ("company_id", "=", self.company.id),
                (
                    "user_type_id",
                    "=",
                    self.env.ref("account.data_account_type_revenue").id,
                ),
            ],
            limit=1,
        )
        self.out_invoice1 = self.env["account.move"].create(
            {
                "partner_id": self.bad_payer.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": today - timedelta(days=5),
                "invoice_date_due": today - timedelta(days=5),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "test line",
                            "price_unit": 500,
                            "quantity": 1,
                            "account_id": revenue_acc.id,
                        },
                    )
                ],
            }
        )
        self.out_invoice1.action_post()
        self.out_invoice2 = self.env["account.move"].create(
            {
                "partner_id": self.bad_payer.id,
                "move_type": "out_invoice",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": datetime.now().date(),
                "invoice_date_due": today + timedelta(days=30),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "test line",
                            "price_unit": 1000,
                            "quantity": 1,
                            "account_id": revenue_acc.id,
                        },
                    )
                ],
            }
        )
        self.out_invoice2.action_post()

    def test_overdue_warn(self):
        self.assertEqual(self.bad_payer.overdue_invoice_count, 1)
        self.assertEqual(self.bad_payer.overdue_invoice_amount, 500)
