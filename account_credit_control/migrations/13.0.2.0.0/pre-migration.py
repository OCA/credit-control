# Copyright 2020 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from openupgradelib import openupgrade

from odoo.tools.parse_version import parse_version


@openupgrade.migrate()
def migrate(env, version):
    # Skip migration if 12.0.3 was already installed (migration was already run)
    if parse_version("12.0.3.0.0") <= parse_version(version) < parse_version("13.0"):
        return
    # Preserve mail_message_id historic data from credit.control.line records
    mail_message_legacy = openupgrade.get_legacy_name("mail_message_id")
    openupgrade.copy_columns(
        env.cr,
        {"credit_control_line": [("mail_message_id", mail_message_legacy, None)]},
    )
    # Vacuum meaningless transient data from credit.control.communication
    openupgrade.logged_query(
        env.cr, "DELETE FROM credit_control_communication",
    )
