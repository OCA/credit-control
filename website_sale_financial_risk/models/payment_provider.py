# Copyright 2025 Tecnativa - Pilar Vargas
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("credit", "On Credit")], ondelete={"credit": "set default"}
    )

    @api.model
    def _get_compatible_providers(
        self, *args, sale_order_id=None, website_id=None, **kwargs
    ):
        all_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, website_id=website_id, **kwargs
        )
        # Always hide "credit" unless explicitly allowed
        providers = all_providers.filtered(lambda p: p.code != "credit")
        if sale_order_id:
            order = self.env["sale.order"].browse(sale_order_id).exists()
            if (
                self.env.user.credit_limit
                and self.env.user.risk_remaining_value >= order.amount_total
            ):
                providers += all_providers.filtered(lambda p: p.code == "credit")
        return providers
