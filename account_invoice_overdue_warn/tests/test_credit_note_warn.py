# Copyright 2024 Akretion France (http://www.akretion.com/)
# @author: Mathieu Delva <mathieu.delva@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOverdueWarn(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.partner = self.env.ref("base.res_partner_2")
        today = datetime.now().date()

        self.credit_note_invoice1 = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_refund",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": today - timedelta(days=5),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "test line",
                            "display_type": "product",
                            "price_unit": 20,
                            "quantity": 1,
                            "tax_ids": [],
                        },
                    )
                ],
            }
        )
        self.credit_note_invoice1.action_post()
        self.credit_note_invoice2 = self.env["account.move"].create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_refund",
                "company_id": self.company.id,
                "currency_id": self.company.currency_id.id,
                "invoice_date": datetime.now().date(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "test line",
                            "display_type": "product",
                            "price_unit": 30,
                            "quantity": 1,
                            "tax_ids": [],
                        },
                    )
                ],
            }
        )
        self.credit_note_invoice2.action_post()

    def test_overdue_warn(self):
        self.assertEqual(self.partner.credit_note_count, 1)
        self.assertEqual(self.partner.credit_note_amount, 20)
