# Copyright 2020 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Preserve mail_message_id historic data from credit.control.line records
    mail_message_legacy = openupgrade.get_legacy_name("mail_message_id")
    openupgrade.copy_columns(
        env.cr,
        {
            "credit_control_line": [
                ("mail_message_id", mail_message_legacy, None),
            ]
        },
    )
    # Vacuum meaningless transient data from credit.control.communication
    openupgrade.logged_query(
        env.cr,
        "DELETE FROM credit_control_communication",
    )
