# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """Restore action domain, which was probably polluted.

    This patch release fixes a bug whose result may be stored in database, so
    although it's still a patch, we need to clear the database, just in case.
    """
    action = env.ref("account_credit_control.credit_control_communication_action",
                     raise_if_not_found=False)
    # if not found, this XML id has not been created,
    # so clearing the database is not needed.
    if action:
        action.domain = []
