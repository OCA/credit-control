# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)


def pre_init_hook(env):
    env.cr.execute(
        """
        ALTER TABLE res_partner
        ADD COLUMN IF NOT EXISTS credit_limit_sudo jsonb;
    """,
    )
    env.cr.execute(
        """
        UPDATE res_partner
        SET credit_limit_sudo = credit_limit
        WHERE credit_limit_sudo IS NULL;
    """,
    )
