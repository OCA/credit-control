# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OverdueReminderResult(models.Model):
    _name = "overdue.reminder.result"
    _description = "Overdue Invoice Reminder Result/Info"
    _order = "sequence, id desc"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer()

    _sql_constraints = [
        ("name_unique", "unique(name)", "This overdue reminder result already exists")
    ]
