# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class PurchaseRiskException(models.TransientModel):
    _name = "purchase.risk.exception"
    _description = "Purchase Risk Exception Wizard"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        readonly=True,
        string="Vendor",
    )
    purchase_risk = fields.Monetary(
        related="partner_id.purchase_risk",
        string="Current Purchase Risk",
        currency_field="currency_id",
    )
    purchase_risk_limit = fields.Monetary(
        related="partner_id.purchase_risk_limit",
        string="Purchase Risk Limit",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="partner_id.purchase_risk_currency_id",
        string="Currency",
    )
    exception_msg = fields.Text(readonly=True, string="Exception Message")
    order_id = fields.Many2one(
        comodel_name="purchase.order",
        readonly=True,
        string="Purchase Order",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        readonly=True,
        string="Vendor Bill",
    )

    def action_show(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase risk limit exceeded"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def button_confirm(self):
        self.ensure_one()
        if self.order_id:
            return self.order_id.with_context(bypass_risk=True).button_confirm()
        if self.move_id:
            return self.move_id.with_context(bypass_risk=True).action_post()
        return True
