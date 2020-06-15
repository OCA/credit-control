# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        orao = env['overdue.reminder.action']
        aioro = env['account.invoice.overdue.reminder']

        # The system is designed so that you can't
        # send 2 reminders for the same customer the
        # same day
        # So, in order to create overdue.reminder.action, we
        # read account.invoice.overdue.reminder and we group by
        # date/company/partner
        cr.execute(
            """
            SELECT id, partner_id as commercial_partner_id, date, user_id,
            reminder_type, result_id, result_notes, mail_id, company_id
            FROM account_invoice_overdue_reminder
            """)
        tmp = {}  # (key = date, company, commercial_partner_id)
        # value = vals with list of ids
        for old in cr.dictfetchall():
            key = (old['date'], old['company_id'], old['commercial_partner_id'])
            if key in tmp:
                tmp[key]['reminder_ids'].append(old['id'])
            else:
                tmp[key] = {
                    'reminder_ids': [old['id']],
                    'date': old['date'],
                    'commercial_partner_id': old['commercial_partner_id'],
                    'partner_id': old['commercial_partner_id'],
                    'user_id': old['user_id'],
                    'reminder_type': old['reminder_type'],
                    'result_id': old['result_id'],
                    'result_notes': old['result_notes'],
                    'mail_id': old['mail_id'],
                    'company_id': old['company_id'],
                    }
        for vals in tmp.values():
            reminder_ids = vals.pop('reminder_ids')
            action = orao.create(vals)
            reminders = aioro.browse(reminder_ids)
            reminders.write({'action_id': action.id})
