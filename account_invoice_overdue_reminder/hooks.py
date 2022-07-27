# Copyright 2022 ForgeFlow, S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    _logger.info(
        "Pre-creating column overdue_reminder_last_date for table account_move"
    )
    cr.execute(
        """
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS overdue_reminder_last_date Date;
        """
    )
    _logger.info("Pre-creating column overdue_reminder_counter for table account_move")
    cr.execute(
        """
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS overdue_reminder_counter INTEGER DEFAULT 0;
        ALTER TABLE account_move ALTER COLUMN overdue_reminder_counter DROP DEFAULT;
        """
    )
    _logger.info("Pre-creating column no_overdue_reminder for table account_move")
    cr.execute(
        """
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS no_overdue_reminder BOOL DEFAULT False;
        ALTER TABLE account_move ALTER COLUMN no_overdue_reminder DROP DEFAULT;
        """
    )
