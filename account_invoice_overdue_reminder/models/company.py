# -*- coding: utf-8 -*-
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    overdue_reminder_attach_invoice = fields.Boolean(
        string='Attach Invoices to Overdue Reminder E-mails', default=True)
    overdue_reminder_start_days = fields.Integer(
        string='Default Overdue Reminder Trigger Delay (days)')
    overdue_reminder_min_interval_days = fields.Integer(
        string='Default Overdue Reminder Minimum Interval (days)', default=5)
    overdue_reminder_interface = fields.Selection(
        '_overdue_reminder_interface_selection',
        string='Default Overdue Reminder Wizard Interface',
        default='onebyone')
    overdue_reminder_partner_policy = fields.Selection(
        '_overdue_reminder_partner_policy_selection',
        default='last_reminder', string='Contact to Remind')

    @api.model
    def _overdue_reminder_interface_selection(self):
        return [
            ('onebyone', _('One by One')),
            ('mass', _('Mass')),
            ]

    @api.model
    def _overdue_reminder_partner_policy_selection(self):
        return [
            ('last_reminder', _('Last Reminder')),
            ('last_invoice', _('Last Invoice')),
            ('invoice_contact', _('Invoice Contact')),
            ]

    _sql_constraints = [
        (
            'overdue_reminder_start_days_positive',
            'CHECK(overdue_reminder_start_days >= 0)',
            'Overdue Reminder Trigger Delay must always be positive'),
        (
            'overdue_reminder_min_interval_days_positive',
            'CHECK(overdue_reminder_min_interval_days > 0)',
            'Overdue Reminder Trigger Delay must always be strictly positive'),
        ]
