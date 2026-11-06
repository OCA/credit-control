# Copyright 2016-2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_round


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def evaluate_risk_message(self, partner):
        self.ensure_one()
        # Credit limit and risk amounts of the order company
        partner = partner.with_company(self.company_id)
        risk_amount = self.currency_id._convert(
            self.amount_total,
            partner.risk_currency_id,
            self.company_id,
            self.date_order
            and self.date_order.date()
            or fields.Date.context_today(self),
            round=False,
        )
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = self.env._("Financial risk exceeded.\n")
        elif partner.risk_sale_order_limit and (
            (partner.risk_sale_order + risk_amount) > partner.risk_sale_order_limit
        ):
            exception_msg = self.env._(
                "This sale order exceeds the sales orders risk.\n"
            )
        elif partner.risk_sale_order_include and (
            (partner.risk_total + risk_amount) > partner.sudo().credit_limit
        ):
            exception_msg = self.env._("This sale order exceeds the financial risk.\n")
        return exception_msg

    def action_confirm(self):
        if not self.env.context.get("bypass_risk", False):
            for order in self.filtered(
                lambda so: not so.company_id.allow_overrisk_sale_confirmation
            ):
                partner = order.partner_invoice_id.commercial_partner_id
                exception_msg = order.evaluate_risk_message(partner)
                if exception_msg:
                    return (
                        self.env["partner.risk.exceeded.wiz"]
                        .create(
                            {
                                "exception_msg": exception_msg,
                                "partner_id": partner.id,
                                "origin_reference": f"{order._name},{order.id}",
                                "continue_method": "action_confirm",
                            }
                        )
                        .action_show()
                    )
        return super().action_confirm()

    @api.model
    def _get_risk_states(self):
        risk_states = ["sale"]
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("sale_financial_risk.include_risk_sale_order_done"):
            risk_states.append("done")
        return risk_states


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    risk_amount = fields.Monetary(
        compute="_compute_risk_amount",
        compute_sudo=True,
        currency_field="company_currency_id",
        store=True,
    )
    risk_partner_id = fields.Many2one(
        related="order_id.partner_invoice_id.commercial_partner_id",
        string="Commercial Entity",
        store=True,
        index=True,
    )

    @api.depends(
        "state",
        "price_reduce_taxinc",
        "qty_delivered",
        "product_uom_qty",
        "qty_invoiced",
        "qty_to_invoice",
    )
    def _compute_risk_amount(self):
        risk_states = self.env["sale.order"]._get_risk_states()
        for line in self:
            risk_qty = line._get_risk_qty(risk_states)
            if risk_qty and not line._can_be_invoiced_alone():
                # Delivery, discount and reward lines are only invoiced with
                # other lines, so they have no risk when the other lines of
                # the order have nothing left to invoice
                other_lines = line.order_id.order_line.filtered(
                    lambda other: not other.display_type
                    and not other.is_downpayment
                    and other._can_be_invoiced_alone()
                )
                if other_lines and not any(
                    other._get_risk_qty(risk_states) for other in other_lines
                ):
                    risk_qty = 0.0
            if risk_qty == 0.0:
                line.risk_amount = 0.0
                continue
            if line.product_uom_qty:
                # This method has more precision that using price_reduce_taxinc
                risk_amount = line.price_total * (risk_qty / line.product_uom_qty)
            else:
                risk_amount = line.price_reduce_taxinc * risk_qty
            # In company currency, the partner risk converts the sum
            line.risk_amount = line.order_id.currency_id._convert(
                risk_amount,
                line.company_currency_id,
                line.company_id,
                line.order_id.date_order
                and line.order_id.date_order.date()
                or fields.Date.context_today(self),
                round=False,
            )
        # The lines not invoiced alone depend on the other lines of their
        # order. Recompute only them: a dependency on order_id.order_line
        # would recompute every line of the order, and confirmed orders
        # flush once per edited line.
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
            field = self._fields["risk_amount"]
            self.env.add_to_compute(field, dependent_lines)
            # Compute them now: recomputing this field alone, as a read_group
            # on it does, skips the records marked in the meantime
            field.recompute(dependent_lines)

    def _get_risk_qty(self, risk_states):
        """Quantity of the line that counts in the sales orders risk"""
        self.ensure_one()
        if self.state not in risk_states or self.display_type:
            return 0.0
        qty = self.product_uom_qty
        if self.product_id.invoice_policy == "delivery":
            qty = max(qty, self.qty_delivered)
        risk_qty = float_round(
            qty - self.qty_invoiced,
            precision_rounding=self.product_uom.rounding or 0.01,
        )
        # There is no risk if the line hasn't stock moves to deliver
        # Added hasattr condition because fails in post-migration compute
        if (
            risk_qty
            and self.qty_delivered_method == "stock_move"
            and (hasattr(self, "move_ids"))
        ):
            if not self.move_ids.filtered(
                lambda move: move.state not in ("done", "cancel")
            ):
                risk_qty = self.qty_to_invoice
        return risk_qty
