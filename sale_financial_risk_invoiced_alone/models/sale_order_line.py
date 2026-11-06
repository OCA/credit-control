# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends("qty_to_invoice")
    def _compute_risk_amount(self):
        res = super()._compute_risk_amount()
        # The lines not invoiced alone depend on the other lines of their
        # order. Recompute only them: a dependency on order_id.order_line
        # would recompute every line of the order, and confirmed orders
        # flush once per edited line.
        risk_states = self.env["sale.order"]._get_risk_states()
        alone_lines = self.filtered(
            lambda line: line.order_id.state in risk_states
            and line._can_be_invoiced_alone()
        )
        dependent_lines = (alone_lines.order_id.order_line - self).filtered(
            lambda line: line.id
            and not line.display_type
            and not line._can_be_invoiced_alone()
        )
        if dependent_lines:
            self.env.add_to_compute(self._fields["risk_amount"], dependent_lines)
        return res

    def _get_risk_qty(self, risk_states):
        risk_qty = super()._get_risk_qty(risk_states)
        if (
            not risk_qty
            or self.env.context.get("skip_risk_invoiced_alone")
            or self._can_be_invoiced_alone()
        ):
            return risk_qty
        # Delivery, discount and reward lines are only invoiced with other
        # lines, so they have no risk when the other lines of the order have
        # nothing left to invoice
        other_lines = self.order_id.order_line.filtered(
            lambda other: not other.display_type
            and not other.is_downpayment
            and other._can_be_invoiced_alone()
        )
        if other_lines and not any(
            other._get_risk_qty(risk_states) for other in other_lines
        ):
            return 0.0
        return risk_qty
