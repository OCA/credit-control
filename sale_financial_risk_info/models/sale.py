# Copyright 2021 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # partner_credit_limit = fields.Monetary(
    #     compute="_compute_risk_info",
    # )
    # partner_risk_total = fields.Monetary(
    #     compute="_compute_risk_info",
    # )
    # partner_risk_percent = fields.Float(digits=(16, 0), compute='_compute_risk_info')
    risk_info = fields.Html(compute="_compute_risk_info")

    @api.depends("partner_invoice_id")
    def _compute_risk_info(self):
        for sale in self:
            partner = sale.partner_invoice_id.commercial_partner_id
            if not partner.credit_limit:
                sale.risk_info = _("Unlimited")
                continue
            risk_percent = round(partner.risk_total / partner.credit_limit * 100)
            symbol = partner.risk_currency_id.symbol
            if risk_percent >= partner.risk_percent_warning:
                text_class = ' class="text-danger"'
            else:
                text_class = ""
            sale.risk_info = _("<h5%s>%s%s of %s%s (%s%%)</h5>") % (
                text_class,
                round(partner.risk_total),
                symbol,
                round(partner.credit_limit),
                symbol,
                risk_percent,
            )
