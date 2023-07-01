# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, "account_credit_control", "migrations/15.0.1.3.0/noupdate_changes.xml"
    )
    openupgrade.delete_record_translations(
        env.cr, "account_credit_control", ["email_template_credit_control_base"]
    )
