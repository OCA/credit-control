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
    _fill_line_channel_states(cr)


def _fill_line_channel_states(cr):
    """Set the state of the line channel from the line state.

    Before, a line had one channel, so the line state is the channel state.
    """
    for channel in ("letter", "email"):
        column = f"state_channel_{channel}"
        if not column_exists(cr, "credit_control_line", column):
            create_column(cr, "credit_control_line", column, "varchar")
        cr.execute(
            f"""
            UPDATE credit_control_line
            SET {column} = CASE state
                WHEN 'sent' THEN 'sent'
                WHEN 'queued' THEN 'queued'
                ELSE 'error'
            END
            WHERE use_channel_{channel}
              AND state IN ('sent', 'queued', 'error', 'email_error')
            """  # pylint: disable=E8103
        )
