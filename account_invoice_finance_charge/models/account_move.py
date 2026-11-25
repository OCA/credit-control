# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    is_finance_charge = fields.Boolean(readonly=True)

    def button_draft(self):
        self._check_finance_charge_period_free()
        return super().button_draft()

    def _post(self, soft=True):
        self._check_finance_charge_sources()
        return super()._post(soft=soft)

    def _check_finance_charge_sources(self):
        """Refuse to post interest on an invoice that no longer stands."""
        charges = self.filtered("is_finance_charge")
        if not charges:
            return
        periods = (
            self.env["account.finance.charge.line"]
            .sudo()
            .search([("charge_move_id", "in", charges.ids)])
        )
        for period in periods:
            source = period.source_move_id
            if source.state != "posted" or source.payment_state == "reversed":
                raise UserError(
                    self.env._(
                        "This finance charge cannot be posted because %(invoice)s "
                        "has been cancelled, reset to draft or reversed.",
                        invoice=source.name,
                    )
                )

    def _check_finance_charge_period_free(self):
        """Stop a cancelled charge coming back over a period billed since."""
        charges = self.filtered("is_finance_charge")
        if not charges:
            return
        periods = self.env["account.finance.charge.line"].sudo()
        cancelled = periods.search(
            [
                ("charge_move_id", "in", charges.ids),
                ("charge_state", "=", "cancel"),
            ]
        )
        for period in cancelled:
            overlapping = periods.search_count(
                [
                    ("id", "!=", period.id),
                    ("source_move_id", "=", period.source_move_id.id),
                    ("charge_state", "!=", "cancel"),
                    ("date_from", "<=", period.date_to),
                    ("date_to", ">=", period.date_from),
                ],
                limit=1,
            )
            if overlapping:
                raise UserError(
                    self.env._(
                        "This charge cannot return to draft because part of its "
                        "period on %(invoice)s has been billed again since.",
                        invoice=period.source_move_id.name,
                    )
                )
