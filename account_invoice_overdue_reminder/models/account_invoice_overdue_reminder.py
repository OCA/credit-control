# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountInvoiceOverdueReminder(models.Model):
    _name = "account.invoice.overdue.reminder"
    _description = "Overdue Invoice Reminder Action History"
    _order = "id desc"

    # For the link to invoice: why a M2O and not a M2M ?
    # Because of the "counter" field: a single reminder action for a customer,
    # the "counter" may not be the same for each invoice
    invoice_id = fields.Many2one(
        "account.move", string="Invoice", ondelete="cascade", readonly=True
    )
    action_id = fields.Many2one(
        "overdue.reminder.action", string="Overdue Reminder Action", ondelete="cascade"
    )
    action_commercial_partner_id = fields.Many2one(
        related="action_id.commercial_partner_id", store=True
    )
    action_partner_id = fields.Many2one(related="action_id.partner_id", store=True)
    action_date = fields.Date(related="action_id.date", store=True)
    action_user_id = fields.Many2one(related="action_id.user_id")
    action_reminder_type = fields.Selection(
        related="action_id.reminder_type", store=True
    )
    action_result_id = fields.Many2one(related="action_id.result_id", readonly=False)
    action_result_notes = fields.Text(related="action_id.result_notes", readonly=False)
    action_mail_id = fields.Many2one(related="action_id.mail_id")
    action_mail_cc = fields.Char(
        related="action_id.mail_id.email_cc", readonly=True, string="Cc"
    )
    action_mail_state = fields.Selection(
        related="action_id.mail_id.state", string="E-mail Status"
    )
    counter = fields.Integer(readonly=True)
    company_id = fields.Many2one(related="invoice_id.company_id", store=True)

    _sql_constraints = [
        ("counter_positive", "CHECK(counter >= 0)", "Counter must always be positive")
    ]

    @api.constrains("invoice_id")
    def invoice_id_check(self):
        for action in self:
            if action.invoice_id and action.invoice_id.move_type != "out_invoice":
                raise ValidationError(
                    _(
                        "An overdue reminder can only be attached "
                        "to a customer invoice"
                    )
                )

    @api.depends("invoice_id", "counter")
    def name_get(self):
        res = []
        for rec in self:
            name = _("%s Reminder %d") % (rec.invoice_id.name, rec.counter)
            res.append((rec.id, name))
        return res
