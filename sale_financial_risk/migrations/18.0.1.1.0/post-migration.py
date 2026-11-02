# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The risk amount was stored in the partner risk currency instead of the
    company currency. Recompute only the lines where both differ."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = (
        env["sale.order.line"]
        .search(
            [
                ("risk_amount", "!=", 0.0),
                ("order_id.partner_id.credit_currency", "!=", "company"),
            ]
        )
        .filtered(
            lambda line: line.order_id.partner_id.with_company(
                line.company_id
            ).risk_currency_id
            != line.company_currency_id
        )
    )
    env.add_to_compute(lines._fields["risk_amount"], lines)
    lines.flush_recordset(["risk_amount"])
