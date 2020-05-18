# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """
    Convert custom_text fields to Html on policy_level
    """
    cr = env.cr
    openupgrade.copy_columns(
        cr,
        {
            "credit_control_policy_level": [
                ("custom_text", None, None),
                ("custom_text_after_details", None, None),
            ]
        },
    )
    openupgrade.convert_field_to_html(
        cr, "credit_control_policy_level", "custom_text", "custom_text"
    )
    openupgrade.convert_field_to_html(
        cr,
        "credit_control_policy_level",
        "custom_text_after_details",
        "custom_text_after_details",
    )
