# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOverdueWarn(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.ref("base.main_company")
        cls.bad_payer = cls.env["res.partner"].create(
            {
                "name": "Bad payer",
                "country_id": cls.env.ref("base.fr").id,
                "company_id": cls.company.id,
            }
        )
        cls.bad_payer_contact = cls.env["res.partner"].create(
            {
                "name": "Bad payer contact",
                "type": "contact",
                "parent_id": cls.bad_payer.id,
                "company_id": cls.company.id,
            }
        )
        today = datetime.now().date()
        acc = cls.env["account.account"].search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        cls.out_invoice1 = cls.env["account.move"].create(
            {
                "partner_id": cls.bad_payer.id,
                "move_type": "out_invoice",
                "company_id": cls.company.id,
                "currency_id": cls.company.currency_id.id,
                "invoice_date": today - timedelta(days=5),
                "invoice_date_due": today - timedelta(days=5),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "test line",
                            "display_type": "product",
                            "price_unit": 500,
                            "quantity": 1,
                            "account_id": acc.id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        cls.out_invoice1.action_post()
        cls.out_invoice2 = cls.env["account.move"].create(
            {
                "partner_id": cls.bad_payer.id,
                "move_type": "out_invoice",
                "company_id": cls.company.id,
                "currency_id": cls.company.currency_id.id,
                "invoice_date": datetime.now().date(),
                "invoice_date_due": today + timedelta(days=30),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "test line",
                            "display_type": "product",
                            "price_unit": 1000,
                            "quantity": 1,
                            "account_id": acc.id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        cls.out_invoice2.action_post()

    def test_overdue_warn(self):
        self.assertEqual(self.bad_payer.overdue_invoice_count, 1)
        self.assertEqual(self.bad_payer.overdue_invoice_amount, 500)
        self.assertEqual(self.bad_payer_contact.overdue_invoice_count, 1)
        self.assertEqual(self.bad_payer_contact.overdue_invoice_amount, 500)
