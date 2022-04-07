# Copyright 2022 Akretion France (http://www.akretion.com/)
# Copyright 2022 ForgeFlow (http://www.forgeflow.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# Copied and adapted from the OCA module intrastat_product

from openupgradelib import openupgrade  # pylint: disable=W7936


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.table_exists(env.cr, "account_invoice"):
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_invoice_overdue_reminder aior
            SET invoice_id = am.id
            FROM account_move am
            WHERE aior.%(old_inv_id)s = am.old_invoice_id"""
            % {"old_inv_id": openupgrade.get_legacy_name("invoice_id")},
        )
