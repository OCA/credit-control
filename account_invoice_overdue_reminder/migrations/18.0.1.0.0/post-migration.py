# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade, openupgrade_180


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.table_exists(env.cr, "ir_property"):
        # The database may have been already touched by Odoo's
        # official migration scripts
        return
    openupgrade_180.convert_company_dependent(env, "res.partner", "no_overdue_reminder")
