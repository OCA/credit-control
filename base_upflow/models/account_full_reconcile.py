# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountJournal(models.Model):
    _name = "account.full.reconcile"
    _inherit = ["account.full.reconcile"]

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
        for partial in self.partial_reconcile_ids:
            data = {
                "externalId": str(partial.debit_move_id.move_id.id),
                "amountLinked": partial.company_currency_id.to_lowest_division(
                    partial.amount
                ),
            }
            if partial.debit_move_id.move_id.upflow_uuid:
                data["id"] = partial.debit_move_id.move_id.upflow_uuid
            if partial.debit_move_id.move_id.move_type == "out_invoice":
                kind = "invoices"
                data["customId"] = partial.debit_move_id.move_id.name
            else:
                kind = "refunds"

            payload[kind].append(data)

            data = {
                "externalId": str(partial.credit_move_id.move_id.id),
                "amountLinked": partial.company_currency_id.to_lowest_division(
                    partial.amount
                ),
            }
            if partial.credit_move_id.move_id.upflow_uuid:
                data["id"] = partial.credit_move_id.move_id.upflow_uuid
            if partial.credit_move_id.move_id.move_type == "out_refund":
                kind = "creditNotes"
                data["customId"] = partial.credit_move_id.move_id.name
            else:
                kind = "payments"

            payload[kind].append(data)

        return payload
