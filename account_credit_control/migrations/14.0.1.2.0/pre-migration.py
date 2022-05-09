# Copyright 2022 Abraham Anes - Studio73
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(
        env.cr,
        [
            (
                "account_credit_control."
                "constraint_credit_control_policy_level_unique level",
                "account_credit_control."
                "constraint_credit_control_policy_level_unique_level",
            ),
        ],
    )
    env.cr.execute(
        """
        ALTER TABLE credit_control_policy_level
        DROP CONSTRAINT IF EXISTS "credit_control_policy_level_unique level"
        """
    )
