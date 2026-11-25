# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tools.sql import column_exists, create_column

CHANNELS = ("letter", "email", "phone")


def migrate(cr, version):
    """Replace the ``channel`` selection.

    * level: one boolean ``use_channel_<channel>`` per channel,
    * line: one state ``state_channel_<channel>`` per channel.

    Odoo drops the ``channel`` column at the end of the upgrade, so a module
    adding its own channel value (e.g. "sms") can still read it in its own
    pre-migration.
    """
    if not version:
        return
    _migrate_levels(cr)
    _migrate_lines(cr)


def _migrate_levels(cr):
    if not column_exists(cr, "credit_control_policy_level", "channel"):
        return
    for channel in CHANNELS:
        column = f"use_channel_{channel}"
        if not column_exists(cr, "credit_control_policy_level", column):
            create_column(cr, "credit_control_policy_level", column, "boolean")
    assignments = ", ".join(
        f"use_channel_{channel} = (channel IS NOT DISTINCT FROM '{channel}')"
        for channel in CHANNELS
    )
    query = f"UPDATE credit_control_policy_level SET {assignments}"
    cr.execute(query)  # pylint: disable=sql-injection


def _migrate_lines(cr):
    """Before, a line had one channel: the line state is the channel state."""
    if not column_exists(cr, "credit_control_line", "channel"):
        return
    for channel in CHANNELS:
        column = f"state_channel_{channel}"
        if not column_exists(cr, "credit_control_line", column):
            create_column(cr, "credit_control_line", column, "varchar")
        query = f"""
            UPDATE credit_control_line
            SET {column} = CASE
                WHEN channel IS DISTINCT FROM '{channel}' THEN 'unused'
                WHEN state = 'sent' THEN 'sent'
                WHEN state = 'queued' THEN 'queued'
                WHEN state IN ('error', 'email_error') THEN 'error'
                ELSE 'to_send'
            END
        """
        cr.execute(query)  # pylint: disable=sql-injection
