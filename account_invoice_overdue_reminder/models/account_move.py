# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

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
    overdue_remind_sent = fields.Boolean(
        compute="_compute_overdue_reminder_sent",
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
                and move.payment_state in ("not_paid", "partial")
                and move.invoice_date_due
                and move.invoice_date_due < today
            ):
                overdue = True
            move.overdue = overdue

    @api.depends(
        "overdue_reminder_ids.action_id.date",
        "overdue_reminder_ids.counter",
    )
    def _compute_overdue_reminder(self):
        for move in self:
            all_dates = []
            all_counters = []
            # faster than 2 list comprehension because we loop only once?
            for reminder in move.overdue_reminder_ids.filtered(lambda m: m.action_date):
                all_dates.append(reminder.action_date)
                all_counters.append(reminder.counter or 0)
            move.overdue_reminder_last_date = all_dates and max(all_dates) or False
            move.overdue_reminder_counter = all_counters and max(all_counters) or 0

    @api.depends(
        "company_id.overdue_reminder_min_interval_days",
        "overdue_reminder_last_date",
    )
    def _compute_overdue_reminder_sent(self):
        for move in self:
            today = fields.Date.context_today(self)
            min_interval_days = move.company_id.overdue_reminder_min_interval_days
            interval_date = today - relativedelta(days=min_interval_days)
            last_date = move.overdue_reminder_last_date
            move.overdue_remind_sent = last_date and last_date > interval_date
