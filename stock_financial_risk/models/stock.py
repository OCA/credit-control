# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, exceptions, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        if not self.env.context.get("bypass_risk"):
            moves = self.filtered(
                lambda x: (
                    x.location_dest_id.usage == "customer"
                    and x.partner_id.commercial_partner_id.risk_exception
                )
            )
            if moves:
                raise exceptions.UserError(
                    _(
                        "Financial risk exceeded in partner:\n%s",
                        moves.mapped("partner_id.name"),
                    )
                )
        return super()._action_done(cancel_backorder=cancel_backorder)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def show_risk_wizard(self, continue_method):
        return (
            self.env["partner.risk.exceeded.wiz"]
            .create(
                {
                    "exception_msg": _("Financial risk exceeded \n"),
                    "partner_id": self.partner_id.id,
                    "origin_reference": "{},{}".format(self._name, self.id),
                    "continue_method": continue_method,
                }
            )
            .action_show()
        )

    def action_confirm(self):
        if not self.env.context.get("bypass_risk"):
            if (
                self.location_dest_id.usage == "customer"
                and self.partner_id.commercial_partner_id.risk_exception
            ):
                return self.show_risk_wizard("action_confirm")
        return super(StockPicking, self).action_confirm()

    def action_assign(self):
        if not self.env.context.get("bypass_risk") and self.filtered(
            "partner_id.commercial_partner_id.risk_exception"
        ):
            return self.show_risk_wizard("action_assign")
        return super(StockPicking, self).action_assign()

    def button_validate(self):
        if not self.env.context.get("bypass_risk"):
            if (
                self.location_dest_id.usage == "customer"
                and self.partner_id.commercial_partner_id.risk_exception
            ):
                return self.show_risk_wizard("button_validate")
        return super(StockPicking, self).button_validate()
