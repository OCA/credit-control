# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import SQL


class AccountFinanceChargeLine(models.Model):
    """One billed period of interest on one past-due invoice.

    The source invoice can only have one active charge starting on a given
    day, which stops two people billing the same period at the same moment.
    Overlaps from a cancelled charge coming back are refused in button_draft.
    """

    _name = "account.finance.charge.line"
    _description = "Billed Finance Charge Period"
    _order = "date_to desc, id desc"

    source_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Past-Due Invoice",
        required=True,
        index=True,
        ondelete="restrict",
    )
    charge_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Charge Line",
        required=True,
        index=True,
        ondelete="cascade",
    )
    charge_move_id = fields.Many2one(
        related="charge_line_id.move_id", store=True, string="Charge Invoice"
    )
    charge_state = fields.Selection(
        related="charge_line_id.parent_state", store=True, string="Charge Status"
    )
    company_id = fields.Many2one(related="charge_line_id.company_id", store=True)
    currency_id = fields.Many2one(related="charge_line_id.currency_id", store=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    base_amount = fields.Monetary(currency_field="currency_id", required=True)
    rate = fields.Float(digits=(16, 4), required=True)
    days = fields.Integer(required=True)
    amount = fields.Monetary(
        related="charge_line_id.price_subtotal",
        store=True,
        currency_field="currency_id",
    )

    def init(self):
        self.env.cr.execute(
            SQL(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    account_finance_charge_line_period_uniq
                ON %s (source_move_id, date_from)
                WHERE charge_state != 'cancel'
                """,
                SQL.identifier(self._table),
            )
        )
