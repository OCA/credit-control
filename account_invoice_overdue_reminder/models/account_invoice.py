# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # backport of the v12 field
    amount_untaxed_invoice_signed = fields.Monetary(
        string='Untaxed Amount in Invoice Currency', currency_field='currency_id',
        readonly=True, compute='_compute_amount_untaxed_invoice_signed')
    no_overdue_reminder = fields.Boolean(
        string='Disable Overdue Reminder',
        track_visibility='onchange')
    overdue_reminder_ids = fields.One2many(
        'account.invoice.overdue.reminder',
        'invoice_id',
        string='Overdue Reminder Action History')
    overdue_reminder_last_date = fields.Date(
        compute='_compute_overdue_reminder',
        string='Last Overdue Reminder Date', store=True)
    overdue_reminder_counter = fields.Integer(
        string='Overdue Reminder Count', store=True,
        compute='_compute_overdue_reminder',
        help="This counter is not increased in case of phone reminder.")
    overdue = fields.Boolean(compute='_compute_overdue')

    _sql_constraints = [(
        'counter_positive',
        'CHECK(overdue_reminder_counter >= 0)',
        'Overdue Invoice Counter must always be positive')]

    @api.depends('type', 'state', 'date_due')
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for inv in self:
            overdue = False
            if (
                    inv.type == 'out_invoice' and
                    inv.state == 'open' and
                    inv.date_due < today):
                overdue = True
            inv.overdue = overdue

    @api.depends(
        'overdue_reminder_ids.action_id.date',
        'overdue_reminder_ids.counter',
        'overdue_reminder_ids.action_id.reminder_type')
    def _compute_overdue_reminder(self):
        aioro = self.env['account.invoice.overdue.reminder']
        for inv in self:
            reminder = aioro.search(
                [('invoice_id', '=', inv.id)], order='action_date desc', limit=1)
            date = reminder and reminder.action_date or False
            counter_reminder = aioro.search([
                ('invoice_id', '=', inv.id),
                ('action_reminder_type', 'in', ('mail', 'post'))],
                order='action_date desc, id desc', limit=1)
            counter = counter_reminder and counter_reminder.counter or False
            inv.overdue_reminder_last_date = date
            inv.overdue_reminder_counter = counter

    @api.depends('type', 'amount_untaxed')
    def _compute_amount_untaxed_invoice_signed(self):
        for inv in self:
            sign = inv.type in ('out_refund', 'in_refund') and -1 or 1
            inv.amount_untaxed_invoice_signed = inv.amount_untaxed * sign

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.number.replace('/', '_')
