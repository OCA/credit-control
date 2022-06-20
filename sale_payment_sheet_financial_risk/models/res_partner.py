# Copyright 2022 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    risk_sale_payment_sheet_include = fields.Boolean(
        string="Deduct Sale Payment Sheet",
        help="Deduct pending payments in sales payment sheet",
    )
    risk_sale_payment_sheet_limit = fields.Monetary(
        string="Limit Sale Payment Sheet",
        currency_field="risk_currency_id",
        help="Set 0 if it is not locked",
    )
    risk_sale_payment_sheet = fields.Monetary(
        compute="_compute_risk_sale_payment_sheet",
        currency_field="risk_currency_id",
        compute_sudo=True,
        string="Total Sale Payment Sheet",
    )
    sale_payment_sheet_ids = fields.One2many(
        comodel_name="sale.payment.sheet.line", inverse_name="partner_id"
    )

    def _get_risk_sale_payment_sheet_domain(self):
        # When p is NewId object instance bool(p.id) is False
        commercial_partners = self.filtered(
            lambda p: (p.id and p == p.commercial_partner_id)
        )
        return [
            ("partner_id", "in", commercial_partners.ids),
            "|",
            ("state", "=", "open"),
            ("statement_line_id.state", "=", "open"),
        ]

    @api.depends(
        "sale_payment_sheet_ids.amount", "child_ids.sale_payment_sheet_ids.amount",
    )
    def _compute_risk_sale_payment_sheet(self):
        self.update({"risk_sale_payment_sheet": 0.0})
        payments_group = self.env["sale.payment.sheet.line"].read_group(
            domain=self._get_risk_sale_payment_sheet_domain(),
            fields=["partner_id", "amount"],
            groupby=["partner_id"],
            orderby="id",
            lazy=False,
        )
        for group in payments_group:
            partner = self.browse(group["partner_id"][0])
            company = self.env.user.company_id
            company_currency = company.currency_id
            partner.risk_sale_payment_sheet = company_currency._convert(
                -group["amount"],
                partner.risk_currency_id,
                company,
                fields.Date.context_today(self),
                round=False,
            )

    @api.model
    def _risk_field_list(self):
        res = super(ResPartner, self)._risk_field_list()
        res.append(
            (
                "risk_sale_payment_sheet",
                "risk_sale_payment_sheet_limit",
                "risk_sale_payment_sheet_include",
            )
        )
        return res

    def _get_field_risk_model_domain(self, field_name):
        if field_name == "risk_sale_payment_sheet":
            return "sale.payment.sheet.line", self._get_risk_sale_payment_sheet_domain()
        else:
            return super()._get_field_risk_model_domain(field_name)
