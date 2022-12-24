# Copyright 2021 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools.misc import format_amount


class SaleOrder(models.Model):
    _inherit = "sale.order"

    risk_info = fields.Html(compute="_compute_risk_info")
    risk_remaining_value = fields.Monetary(related="partner_id.risk_remaining_value")
    risk_remaining_percentage = fields.Float(
        related="partner_id.risk_remaining_percentage"
    )

    @api.depends("partner_invoice_id")
    def _compute_risk_info(self):
        ICP = self.env["ir.config_parameter"].sudo()
        info_pattern = ICP.get_param(
            "sale_financial_risk_info.info_pattern",
            default="<h5{text_class}>{risk_total} / {credit_limit} ("
            "{risk_percent}%)</h5>",
        )
        for sale in self:
            partner = sale.partner_invoice_id.commercial_partner_id
            if not partner.credit_limit:
                sale.risk_info = _("Unlimited")
                continue
            risk_percent = round(partner.risk_total / partner.credit_limit * 100)
            if risk_percent >= partner.risk_percent_warning:
                text_class = ' class="text-danger"'
            else:
                text_class = ""
            sale.risk_info = info_pattern.format(
                text_class=text_class,
                risk_total=format_amount(
                    self.env, partner.risk_total, partner.risk_currency_id
                ),
                credit_limit=format_amount(
                    self.env, partner.credit_limit, partner.risk_currency_id
                ),
                risk_percent=risk_percent,
                risk_available=format_amount(
                    self.env,
                    partner.credit_limit - partner.risk_total,
                    partner.risk_currency_id,
                ),
            )
