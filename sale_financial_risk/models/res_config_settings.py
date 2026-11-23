# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # The done state became the locked flag in 17.0, the parameter keeps its key
    include_risk_sale_order_done = fields.Boolean(
        "Include locked sale orders into risk calculation",
        config_parameter="sale_financial_risk.include_risk_sale_order_done",
    )
    allow_overrisk_sale_confirmation = fields.Boolean(
        related="company_id.allow_overrisk_sale_confirmation", readonly=False
    )

    def set_values(self):
        SaleOrder = self.env["sale.order"]
        include_locked = SaleOrder._get_risk_include_locked()
        res = super().set_values()
        if SaleOrder._get_risk_include_locked() != include_locked:
            # The stored line risk depends on this setting: recompute the
            # lines of locked orders and the risk amounts depending on them
            orders = SaleOrder.sudo().search(
                [("locked", "=", True), ("state", "in", SaleOrder._get_risk_states())]
            )
            orders.modified(["locked"])
            orders.order_line.flush_recordset(["risk_amount"])
        return res
