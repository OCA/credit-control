# Copyright 2020 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import tools


def pre_init_hook(cr):
    if tools.column_exists(cr, "account_invoice", "company_currency_id"):
        return
    cr.execute("""
        ALTER TABLE account_invoice
        ADD COLUMN company_currency_id integer""")
    cr.execute("""
        UPDATE account_invoice ai
        SET company_currency_id = rc.currency_id
        FROM res_company rc
        WHERE ai.company_id = rc.id""")
