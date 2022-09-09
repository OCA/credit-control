# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    no_overdue_reminder = fields.Boolean(
        string="Disable Overdue Reminder", tracking=True
    )
    overdue_reminder_ids = fields.One2many(
        "account.invoice.overdue.reminder",
        "invoice_id",
        string="Overdue Reminder Action History",
    )
    overdue_reminder_last_date = fields.Date(
        compute="_compute_overdue_reminder",
        string="Last Overdue Reminder Date",
        store=True,
    )
    overdue_reminder_counter = fields.Integer(
        string="Overdue Reminder Count",
        store=True,
        compute="_compute_overdue_reminder",
        help="This counter is not increased in case of phone reminder.",
    )
    overdue = fields.Boolean(compute="_compute_overdue")

    _sql_constraints = [
        (
            "counter_positive",
            "CHECK(overdue_reminder_counter >= 0)",
            "Overdue Invoice Counter must always be positive",
        )
    ]

    @api.depends("move_type", "state", "payment_state", "invoice_date_due")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for move in self:
            overdue = False
            if (
                move.move_type == "out_invoice"
                and move.state == "posted"
                and move.payment_state not in ("paid", "reversed", "in_payment")
                and move.invoice_date_due
                and move.invoice_date_due < today
            ):
                overdue = True
            move.overdue = overdue

    @api.depends(
        "overdue_reminder_ids.action_id.date",
        "overdue_reminder_ids.counter",
        "overdue_reminder_ids.action_id.reminder_type",
    )
    def _compute_overdue_reminder(self):
        aioro = self.env["account.invoice.overdue.reminder"]
        for move in self:
            reminder = aioro.search(
                [("invoice_id", "=", move.id)], order="action_date desc", limit=1
            )
            date = reminder and reminder.action_date or False
            counter_reminder = aioro.search(
                [
                    ("invoice_id", "=", move.id),
                    ("action_reminder_type", "in", ("mail", "post")),
                ],
                order="action_date desc, id desc",
                limit=1,
            )
            counter = counter_reminder and counter_reminder.counter or False
            move.overdue_reminder_last_date = date
            move.overdue_reminder_counter = counter
