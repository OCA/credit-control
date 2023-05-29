# Copyright 2022 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    risk_sale_payment_sheet_include = fields.Boolean(
        string="Deduct Sale Payment Sheet",
        help="Deduct pending payments in each field depending of sheet invoice status",
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
        help="Sum of payment sheet amount pending to validate",
    )
    risk_sale_payment_sheet_info = fields.Text(
        compute="_compute_risk_account_amount",
        compute_sudo=True,
        help="Sheet payment amounts grouped by reduce field (amount field in brackets)",
    )
    sale_payment_sheet_ids = fields.One2many(
        comodel_name="sale.payment.sheet.line", inverse_name="partner_id"
    )

    def _get_risk_sale_payment_sheet_domain(self):
        # When p is NewId object instance is not equal to "Normal" registry
        commercial_partners = self.filtered(
            lambda p: (p.ids == p.commercial_partner_id.ids)
        )
        return [
            ("partner_id", "in", commercial_partners.ids),
            "|",
            ("state", "=", "open"),
            ("statement_line_id.state", "=", "open"),
        ]

    @api.depends(
        "sale_payment_sheet_ids.amount",
        "child_ids.sale_payment_sheet_ids.amount",
        "risk_sale_payment_sheet_include",
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
            partner = self.filtered(lambda p: p.ids[0] == group["partner_id"][0])
            if partner.risk_sale_payment_sheet_include:
                continue
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

    def get_risk_sale_payment_sheet_info(self, info_values):
        # Not put space between values to avoid line break
        return "\n".join(
            "{:.2f}({:.2f})".format(-v, self[k]) for k, v in info_values.items() if v
        )

    @api.depends("risk_sale_payment_sheet_include")
    def _compute_risk_account_amount(self):
        res = super()._compute_risk_account_amount()
        self.update({"risk_sale_payment_sheet_info": ""})
        sheet_lines = self.env["sale.payment.sheet.line"].search(
            self._get_risk_sale_payment_sheet_domain()
        )
        # Get all account risk fields with empty dummy group
        dummy_groups = defaultdict(lambda: {"read_group": []})
        account_vals_zero = self._prepare_risk_account_vals(dummy_groups)
        risk_fields = account_vals_zero.keys()
        info_dic = {}
        for sheet_line in sheet_lines:
            partner_id = sheet_line.partner_id.id
            partner = self.filtered(lambda p: p.ids == [partner_id])
            if not partner.risk_sale_payment_sheet_include:
                continue
            if partner_id not in info_dic:
                info_dic[partner_id] = account_vals_zero.copy()
            move_lines = sheet_line.invoice_id.line_ids
            for risk_field in risk_fields:
                # Get field domain and evaluate to reduce value in match field
                domain = self._get_field_risk_model_domain(risk_field)[1]
                if move_lines.filtered_domain(domain):
                    partner[risk_field] -= sheet_line.amount
                    info_dic[partner_id][risk_field] += sheet_line.amount
                    break
            else:
                partner["risk_account_amount"] -= sheet_line.amount
            # Set for each sheet line to avoid NewId iterable issue if fill dict
            self.risk_sale_payment_sheet_info = (
                partner.get_risk_sale_payment_sheet_info(info_dic[partner_id])
            )
        return res
