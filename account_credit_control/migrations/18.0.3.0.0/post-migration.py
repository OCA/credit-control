# Copyright 2025 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    cr = env.cr
    if openupgrade.column_exists(cr, "credit_control_line", "channel_old"):
        openupgrade.map_values(
            cr,
            "channel_old",
            "channel_letter",
            [("letter", "t")],
            table="credit_control_line",
        )
        openupgrade.map_values(
            cr,
            "channel_old",
            "channel_email",
            [("email", "t")],
            table="credit_control_line",
        )
        openupgrade.map_values(
            cr,
            "channel_old",
            "channel_phone",
            [("phone", "t")],
            table="credit_control_line",
        )
    if openupgrade.column_exists(cr, "credit_control_policy", "channel_old"):
        openupgrade.map_values(
            cr,
            "channel_old",
            "channel_letter",
            [("letter", "t")],
            table="credit_control_policy",
        )
        openupgrade.map_values(
            cr,
            "channel_old",
            "channel_email",
            [("email", "t")],
            table="credit_control_policy",
        )
        openupgrade.map_values(
            cr,
            "channel_old",
            "channel_phone",
            [("phone", "t")],
            table="credit_control_policy",
        )
