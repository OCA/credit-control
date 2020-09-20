# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade  # pylint: disable=W7936


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, "account_credit_control", "migrations/13.0.1.0.0/noupdate_changes.xml"
    )
    openupgrade.logged_query(
        env.cr,
        """UPDATE account_move am
        SET credit_policy_id = ai.credit_policy_id
        FROM account_invoice ai
        WHERE ai.id = am.old_invoice_id""",
    )
