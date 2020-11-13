# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        UPDATE mail_message SET
        res_id=overdue_reminder_action.commercial_partner_id,
        model='res.partner'
        FROM overdue_reminder_action, mail_mail
        WHERE overdue_reminder_action.mail_id=mail_mail.id
        AND mail_mail.mail_message_id = mail_message.id
        """)
