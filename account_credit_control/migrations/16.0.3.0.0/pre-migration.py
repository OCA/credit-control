# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tools.sql import column_exists, create_column

CHANNELS = ("letter", "email", "phone")
TABLES = ("credit_control_policy_level", "credit_control_line")


def migrate(cr, version):
    """Replace the ``channel`` selection by one boolean per channel.

    Odoo drops the ``channel`` column at the end of the upgrade, so a module
    adding its own channel value (e.g. "sms") can still read it in its own
    pre-migration to fill its own boolean.
    """
    if not version:
        return
    for table in TABLES:
        if not column_exists(cr, table, "channel"):
            continue
        for channel in CHANNELS:
            column = f"use_channel_{channel}"
            if not column_exists(cr, table, column):
                create_column(cr, table, column, "boolean")
        assignments = ", ".join(
            f"use_channel_{channel} = (channel IS NOT DISTINCT FROM '{channel}')"
            for channel in CHANNELS
        )
        cr.execute(f"UPDATE {table} SET {assignments}")  # pylint: disable=E8103
