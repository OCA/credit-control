# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Lines that are not invoiced alone (delivery, discount, reward) have no
    risk when the rest of the order has none. Recompute only those lines.
    End migration because the compute needs modules loaded after this one, as
    sale_stock for the moves of the other lines."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = (
        env["sale.order.line"]
        .search([("risk_amount", "!=", 0.0)])
        .filtered(lambda line: not line._can_be_invoiced_alone())
    )
    env.add_to_compute(lines._fields["risk_amount"], lines)
    lines.flush_recordset(["risk_amount"])
