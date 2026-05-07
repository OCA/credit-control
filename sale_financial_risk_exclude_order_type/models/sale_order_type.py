from odoo import fields, models


class SaleOrderType(models.Model):
    _inherit = "sale.order.type"

    exclude_from_risk = fields.Boolean(
        string="Exclude from Risk Computation",
        help=(
            "If enabled, sale orders of this type are excluded from "
            "sale financial risk computation."
        ),
    )
    allow_blocking_bypass = fields.Boolean(
        string="Allow Risk Blocking Bypass",
        help=(
            "If enabled, sale orders of this type can be confirmed "
            "without financial risk blocking."
        ),
    )
