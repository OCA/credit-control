# Copyright 2016-2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    risk_sale_order_include = fields.Boolean(
        string="Include Sales Orders", help="Full risk computation"
    )
    risk_sale_order_limit = fields.Monetary(
        string="Limit Sales Orders", help="Set 0 if it is not locked"
    )
    risk_sale_order = fields.Monetary(
        compute="_compute_risk_sale_order",
        string="Total Sales Orders Not Invoiced",
        help="Total not invoiced of sales orders in Sale Order state",
    )

    def _get_risk_sale_order_domain(self):
        # When p is NewId object instance bool(p.id) is False
        commercial_partners = self.filtered(
            lambda p: (p.id and p == p.commercial_partner_id)
        )
        return self._get_risk_company_domain() + [
            ("state", "=", "sale"),
            ("commercial_partner_id", "in", commercial_partners.ids),
        ]

    @api.depends(
        "sale_order_ids.order_line.risk_amount",
        "child_ids.sale_order_ids.order_line.risk_amount",
    )
    def _compute_risk_sale_order(self):
        self.update({"risk_sale_order": 0.0})
        orders_group = self.env["sale.order.line"].read_group(
            domain=self._get_risk_sale_order_domain(),
            fields=["commercial_partner_id", "risk_amount"],
            groupby=["commercial_partner_id"],
            orderby="id",
        )
        for group in orders_group:
            self.browse(group["commercial_partner_id"][0]).risk_sale_order = group[
                "risk_amount"
            ]

    @api.model
    def _risk_field_list(self):
        res = super(ResPartner, self)._risk_field_list()
        res.append(
            ("risk_sale_order", "risk_sale_order_limit", "risk_sale_order_include")
        )
        return res

    def _get_field_risk_model_domain(self, field_name):
        if field_name == "risk_sale_order":
            return "sale.order.line", self._get_risk_sale_order_domain()
        else:
            return super()._get_field_risk_model_domain(field_name)
