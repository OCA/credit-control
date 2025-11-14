# Copyright 2025 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Preserve channel historic data from credit.control.line records
    if openupgrade.column_exists(env.cr, "credit_control_line", "channel"):
        openupgrade.copy_columns(
            env.cr,
            {
                "credit_control_line": [
                    ("channel", "channel_old", None),
                ],
            },
        )
    if openupgrade.column_exists(env.cr, "credit_control_policy", "channel"):
        openupgrade.copy_columns(
            env.cr,
            {
                "credit_control_policy": [
                    ("channel", "channel_old", None),
                ],
            },
        )
