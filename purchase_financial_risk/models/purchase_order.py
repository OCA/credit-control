# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    purchase_risk_amount = fields.Monetary(
        compute="_compute_purchase_risk_amount",
        compute_sudo=True,
        store=True,
        currency_field="company_currency_id",
        help="Uninvoiced amount for this line in company currency.",
    )
    purchase_risk_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="order_id.partner_id.commercial_partner_id",
        string="Commercial Vendor",
        store=True,
        index=True,
    )

    @api.depends(
        "state",
        "price_total",
        "qty_invoiced",
        "product_qty",
        "order_id.currency_id",
        "order_id.date_order",
    )
    def _compute_purchase_risk_amount(self):
        for line in self:
            if line.state not in ("purchase", "done") or not line.product_qty:
                line.purchase_risk_amount = 0.0
                continue
            qty_to_invoice = max(line.product_qty - line.qty_invoiced, 0.0)
            if not qty_to_invoice:
                line.purchase_risk_amount = 0.0
                continue
            risk_amount = line.price_total * qty_to_invoice / line.product_qty
            date = (
                line.order_id.date_order.date()
                if line.order_id.date_order
                else fields.Date.context_today(self)
            )
            line.purchase_risk_amount = line.order_id.currency_id._convert(
                risk_amount,
                line.company_id.currency_id,
                line.company_id,
                date,
                round=False,
            )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _evaluate_purchase_risk(self, partner):
        """Return exception message if this order would exceed the vendor risk limit."""
        self.ensure_one()
        if not partner.purchase_risk_limit or partner.purchase_risk_exception:
            return ""
        risk_currency = partner.purchase_risk_currency_id or self.company_id.currency_id
        date = (
            self.date_order.date()
            if self.date_order
            else fields.Date.context_today(self)
        )
        risk_amount = self.currency_id._convert(
            self.amount_total,
            risk_currency,
            self.company_id,
            date,
            round=False,
        )
        if (partner.purchase_risk + risk_amount) > partner.purchase_risk_limit:
            return _("This document exceeds the vendor's purchase risk limit.\n")
        return ""

    def button_confirm(self):
        if not self.env.context.get("bypass_risk", False):
            for order in self:
                partner = order.partner_id.commercial_partner_id
                exception_msg = order._evaluate_purchase_risk(partner)
                if exception_msg:
                    return (
                        self.env["purchase.risk.exception"]
                        .create(
                            {
                                "exception_msg": exception_msg,
                                "partner_id": partner.id,
                                "order_id": order.id,
                            }
                        )
                        .action_show()
                    )
        return super().button_confirm()
