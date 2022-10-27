# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.lift_constraints(
        env.cr, "account_invoice_overdue_reminder", "invoice_id"
    )
    openupgrade.rename_columns(
        env.cr, {"account_invoice_overdue_reminder": [("invoice_id", None)]}
    )
