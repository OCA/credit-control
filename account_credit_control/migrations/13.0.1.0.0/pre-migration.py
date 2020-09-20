# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade  # pylint: disable=W7936
from psycopg2 import sql


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_columns(env.cr, {"credit_control_line": [("invoice_id", None)]})
    openupgrade.logged_query(
        env.cr, "ALTER TABLE credit_control_line ADD invoice_id INT4"
    )
    openupgrade.logged_query(
        env.cr,
        sql.SQL(
            """UPDATE credit_control_line ccl
            SET invoice_id = ai.move_id
            FROM account_invoice ai
            WHERE ai.id = ccl.{}"""
        ).format(sql.Identifier(openupgrade.get_legacy_name("invoice_id"))),
    )
