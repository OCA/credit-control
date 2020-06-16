# Copyright 2020 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import tools


def pre_init_hook(cr):
    if not tools.column_exists(cr, "account_move", "company_currency_id"):
        cr.execute(
            """
            ALTER TABLE account_move
            ADD COLUMN company_currency_id integer"""
        )
        cr.execute(
            """
            UPDATE account_move am
            SET company_currency_id = rc.currency_id
            FROM res_company rc
            WHERE am.company_id = rc.id"""
        )
