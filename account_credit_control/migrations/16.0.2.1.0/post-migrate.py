# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    credit_control_lines = env["credit.control.policy.level"].search(
        [("custom_mail_text", "!=", False)]
    )
    for ccl in credit_control_lines:
        ccl.custom_mail_text = (
            ccl.custom_mail_text.replace("&nbsp;", "")
            .replace("<p>", "")
            .replace("</p>", "\n")
        )
