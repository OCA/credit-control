# Copyright 2024 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PartnerRiskExceededWiz(models.TransientModel):
    _inherit = "partner.risk.exceeded.wiz"

    def button_continue_with_action(self):
        self.ensure_one()
        action = self.env.ref(
            "sale_financial_risk_confirm_action.action_sale_order_changes_to_confirm"
        )
        action.with_context(active_id=self.id).run()
        return self.button_continue()
