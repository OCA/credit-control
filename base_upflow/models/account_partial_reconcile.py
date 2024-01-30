# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountPartialReconcile(models.Model):

    _inherit = ["account.partial.reconcile"]

    def _prepare_reconcile_payload(self):
        payload = {
            "externalId": str(self.id),
            "invoices": [],
            "payments": [],
            "creditNotes": [],
            "refunds": [],
        }
        return payload

    def get_upflow_api_post_reconcile_payload(self):
        """expect to be called from account move type:

        * customer invoice
        * customer refund

        Once there are considered fully paid
        """
        payload = self._prepare_reconcile_payload()

        data = {
            "externalId": str(self.debit_move_id.move_id.id),
            "amountLinked": self.company_currency_id.to_lowest_division(self.amount),
        }
        if self.debit_move_id.move_id.upflow_uuid:
            data["id"] = self.debit_move_id.move_id.upflow_uuid
        if self.debit_move_id.move_id.move_type == "out_invoice":
            kind = "invoices"
            data["customId"] = self.debit_move_id.move_id.name
        else:
            kind = "refunds"

        payload[kind].append(data)

        data = {
            "externalId": str(self.credit_move_id.move_id.id),
            "amountLinked": self.company_currency_id.to_lowest_division(self.amount),
        }
        if self.credit_move_id.move_id.upflow_uuid:
            data["id"] = self.credit_move_id.move_id.upflow_uuid
        if self.credit_move_id.move_id.move_type == "out_refund":
            kind = "creditNotes"
            data["customId"] = self.credit_move_id.move_id.name
        else:
            kind = "payments"

        payload[kind].append(data)

        return payload
