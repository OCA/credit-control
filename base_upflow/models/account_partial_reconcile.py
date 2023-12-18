# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountPartialReconcile(models.Model):
    _name = "account.partial.reconcile"
    _inherit = ["account.partial.reconcile", "upflow.mixin"]

    def _prepare_reconcile_payload(self):
        self.ensure_one()
        payload = {
            "externalId": "partial-" + str(self.id),
            "invoices": [],
            "payments": [],
            "creditNotes": [],
            "refunds": [],
        }
        return payload

    def _get_part_payload(self, move_line):
        data = {
            "externalId": str(move_line.move_id.id),
            "amountLinked": self.company_currency_id.to_lowest_division(self.amount),
        }
        if move_line.move_id.upflow_uuid:
            data["id"] = move_line.move_id.upflow_uuid

        if move_line.move_id.upflow_type in ["invoices", "creditNotes"]:
            data["customId"] = move_line.move_id.name

        return data

    def get_upflow_api_post_reconcile_payload(self):
        """expect to be called from account move type:

        * customer invoice
        * customer refund

        Once there are considered fully paid
        """
        self.ensure_one()
        payload = self._prepare_reconcile_payload()

        payload[self.debit_move_id.move_id.upflow_type].append(
            self._get_part_payload(self.debit_move_id)
        )
        payload[self.credit_move_id.move_id.upflow_type].append(
            self._get_part_payload(self.credit_move_id)
        )

        return payload
