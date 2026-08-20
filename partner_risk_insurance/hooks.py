# Copyright 2024 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def pre_init_hook(cr):
    """Create account move columns to performance installation on large databases"""
    cr.execute(
        """
    ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS insured_with_credit_policy boolean DEFAULT false,
        ADD COLUMN IF NOT EXISTS credit_policy_company_id INT,
        ADD COLUMN IF NOT EXISTS credit_policy_state_id INT;
    """,
    )
