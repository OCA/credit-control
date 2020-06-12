# Copyright 2016-2020 Tecnativa - Carlos Dauden
# Copyright 2020 ForgeFlow
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools import float_round


class SaleOrder(models.Model):
    _inherit = "sale.order"

    risk_currency_id = fields.Many2one(related="partner_id.risk_currency_id")
    risk_amount_total_currency = fields.Monetary(
        string="Risk Amount Total",
        currency_field="risk_currency_id",
        compute="_compute_risk_amount_total_currency",
    )

    @api.depends(
        "order_line.price_total",
        "partner_id.credit_currency",
        "partner_id.manual_credit_currency_id",
        "partner_id.property_account_receivable_id.currency_id",
        "partner_id.country_id",
        "company_id.currency_id",
    )
    def _compute_risk_amount_total_currency(self):
        for sale in self:
            sale.risk_amount_total_currency = sale.currency_id._convert(
                sale.amount_total,
                sale.risk_currency_id,
                sale.company_id,
                sale.date_order
                and sale.date_order.date()
                or fields.Date.context_today(self),
            )

    def evaluate_risk_message(self, partner):
        risk_amount = self.currency_id._convert(
            self.amount_total,
            self.company_id.currency_id,
            self.company_id,
            self.date_order
            and self.date_order.date()
            or fields.Date.context_today(self),
            round=False,
        )
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = _("Financial risk exceeded.\n")
        elif partner.risk_sale_order_limit and (
            (partner.risk_sale_order + risk_amount) > partner.risk_sale_order_limit
        ):
            exception_msg = _("This sale order exceeds the sales orders risk.\n")
        elif partner.risk_sale_order_include and (
            (partner.risk_total + risk_amount) > partner.credit_limit
        ):
            exception_msg = _("This sale order exceeds the financial risk.\n")
        return exception_msg

    def action_confirm(self):
        if not self.env.context.get("bypass_risk", False):
            partner = self.partner_invoice_id.commercial_partner_id
            exception_msg = self.evaluate_risk_message(partner)
            if exception_msg:
                return (
                    self.env["partner.risk.exceeded.wiz"]
                    .create(
                        {
                            "exception_msg": exception_msg,
                            "partner_id": partner.id,
                            "origin_reference": "{},{}".format("sale.order", self.id),
                            "continue_method": "action_confirm",
                        }
                    )
                    .action_show()
                )
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    risk_currency_id = fields.Many2one(related="order_partner_id.risk_currency_id")
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
        store=True,
    )
    risk_amount = fields.Monetary(
        string="Risk amount",
        compute="_compute_risk_amount",
        compute_sudo=True,
        currency_field="company_currency_id",
        store=True,
    )
    risk_amount_currency = fields.Monetary(
        string="Risk amount",
        compute="_compute_risk_amount_currency",
        compute_sudo=True,
        currency_field="risk_currency_id",
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
    )
    def _compute_risk_amount(self):
        for line in self:
            if line.state != "sale" or line.display_type:
                line.risk_amount = 0.0
                continue
            qty = line.product_uom_qty
            if line.product_id.invoice_policy == "delivery":
                qty = max(qty, line.qty_delivered)
            risk_qty = float_round(
                qty - line.qty_invoiced, precision_rounding=line.product_uom.rounding
            )
            # There is no risk if the line hasn't stock moves to deliver
            # Added hasattr condition because fails in post-migration compute
            if (
                risk_qty
                and line.qty_delivered_method == "stock_move"
                and (hasattr(line, "move_ids"))
            ):
                if not line.move_ids.filtered(
                    lambda move: move.state not in ("done", "cancel")
                ):
                    risk_qty = line.qty_to_invoice
            if risk_qty == 0.0:
                line.risk_amount = 0.0
                continue
            if line.product_uom_qty:
                # This method has more precision that using price_reduce_taxinc
                risk_amount = line.price_total * (risk_qty / line.product_uom_qty)
            else:
                risk_amount = line.price_reduce_taxinc * risk_qty
            line.risk_amount = line.order_id.currency_id._convert(
                risk_amount,
                line.company_id.currency_id,
                line.company_id,
                line.order_id.date_order
                and line.order_id.date_order.date()
                or fields.Date.context_today(self),
                round=False,
            )

    @api.depends(
        "state",
        "price_reduce_taxinc",
        "qty_delivered",
        "product_uom_qty",
        "qty_invoiced",
        "order_id.partner_id.credit_currency",
        "order_id.partner_id.manual_credit_currency_id",
        "order_id.partner_id." "property_account_receivable_id.currency_id",
        "order_id.partner_id.country_id",
        "company_id.currency_id",
    )
    def _compute_risk_amount_currency(self):
        for line in self:
            date_order = line.order_id.date_order.date()
            line.risk_amount_currency = line.company_currency_id._convert(
                line.risk_amount,
                line.risk_currency_id,
                line.company_id,
                date_order or fields.Date.context_today(self),
                round=False,
            )
