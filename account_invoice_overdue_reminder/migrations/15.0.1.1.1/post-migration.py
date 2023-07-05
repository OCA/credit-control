# Copyright 2023 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr,
        "account_invoice_overdue_reminder",
        "migrations/15.0.1.1.1/noupdate_changes.xml",
    )
    openupgrade.delete_record_translations(
        env.cr,
        "account_invoice_overdue_reminder",
        ["overdue_invoice_reminder_mail_template"],
    )
