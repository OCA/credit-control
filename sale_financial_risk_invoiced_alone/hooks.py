# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def _recompute_risk_amount(lines):
    lines = lines.filtered(lambda line: not line._can_be_invoiced_alone())
    lines.env.add_to_compute(lines._fields["risk_amount"], lines)
    lines.flush_recordset(["risk_amount"])


def post_init_hook(env):
    """Only lines not invoiced alone that have risk can lose it."""
    _recompute_risk_amount(env["sale.order.line"].search([("risk_amount", "!=", 0.0)]))


def uninstall_hook(env):
    """Give back their risk to the lines not invoiced alone left without it.
    The code of this module is still loaded, so a context key skips it."""
    risk_states = env["sale.order"]._get_risk_states()
    env.cr.execute(
        """
        SELECT id FROM sale_order_line
        WHERE COALESCE(risk_amount, 0) = 0
            AND state IN %s
            AND display_type IS NULL
            AND NOT COALESCE(is_downpayment, FALSE)
            AND (qty_invoiced <> product_uom_qty OR qty_invoiced <> qty_delivered)
        """,
        (tuple(risk_states),),
    )
    line_ids = [row[0] for row in env.cr.fetchall()]
    _recompute_risk_amount(
        env["sale.order.line"]
        .with_context(skip_risk_invoiced_alone=True)
        .browse(line_ids)
    )
