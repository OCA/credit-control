# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    purchase_order_line_risk_ids = fields.One2many(
        comodel_name="purchase.order.line",
        inverse_name="purchase_risk_partner_id",
        string="Purchase Order Lines (Risk)",
    )
    purchase_risk_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Purchase Risk Currency",
        default=lambda self: self.env.company.currency_id,
        help="Currency used for the purchase risk limit and exposure amounts.",
    )
    purchase_risk_limit = fields.Monetary(
        currency_field="purchase_risk_currency_id",
        help="Maximum financial exposure allowed for this vendor.",
        tracking=True,
    )
    purchase_risk_po = fields.Monetary(
        string="Purchase Risk from POs",
        compute="_compute_purchase_risk",
        compute_sudo=True,
        store=True,
        currency_field="purchase_risk_currency_id",
        help="Total financial exposure from open POs (uninvoiced).",
    )
    purchase_risk_bill_draft = fields.Monetary(
        string="Purchase Risk from Draft Bills",
        compute="_compute_purchase_risk",
        compute_sudo=True,
        store=True,
        currency_field="purchase_risk_currency_id",
        help="Total financial exposure from draft vendor bills.",
    )
    purchase_risk_bill_open = fields.Monetary(
        string="Purchase Risk from Open Bills",
        compute="_compute_purchase_risk",
        compute_sudo=True,
        store=True,
        currency_field="purchase_risk_currency_id",
        help="Total financial exposure from posted/open unpaid vendor bills.",
    )
    purchase_risk = fields.Monetary(
        string="Purchase Financial Risk",
        compute="_compute_purchase_risk",
        compute_sudo=True,
        store=True,
        currency_field="purchase_risk_currency_id",
        help="Total financial exposure: open POs (uninvoiced) + unpaid vendor bills.",
    )
    purchase_risk_percent = fields.Float(
        string="Purchase Risk (%)",
        compute="_compute_purchase_risk",
        compute_sudo=True,
        store=True,
        help="Percentage of purchase risk limit consumed.",
    )
    purchase_risk_exception = fields.Boolean(
        help="If checked, purchase orders bypass the risk limit check.",
    )
    purchase_risk_allow_edit = fields.Boolean(
        compute="_compute_purchase_risk_allow_edit",
    )

    def _compute_purchase_risk_allow_edit(self):
        is_manager = self.env.user.has_group(
            "purchase_financial_risk.group_purchase_risk_manager"
        )
        self.update({"purchase_risk_allow_edit": is_manager})

    @api.depends(
        "purchase_order_line_risk_ids.purchase_risk_amount",
        "child_ids.purchase_order_line_risk_ids.purchase_risk_amount",
        "move_line_ids.amount_residual",
        "move_line_ids.parent_state",
        "child_ids.move_line_ids.amount_residual",
        "child_ids.move_line_ids.parent_state",
        "purchase_risk_limit",
        "purchase_risk_currency_id",
    )
    def _compute_purchase_risk(self):
        self.update(
            {
                "purchase_risk": 0.0,
                "purchase_risk_percent": 0.0,
                "purchase_risk_po": 0.0,
                "purchase_risk_bill_draft": 0.0,
                "purchase_risk_bill_open": 0.0,
            }
        )
        vendors = self.filtered(
            lambda p: p == p.commercial_partner_id
            or (p._origin and p._origin.id in p.commercial_partner_id.ids)
        )
        if not vendors:
            return
        today = fields.Date.context_today(self)
        # --- Purchase order risk (uninvoiced POs, stored in company currency) ---
        orders_group = self.env["purchase.order.line"]._read_group(
            domain=[
                ("purchase_risk_partner_id", "in", vendors.ids),
            ],
            groupby=["purchase_risk_partner_id", "company_id"],
            aggregates=["purchase_risk_amount:sum"],
        )
        po_risk = {}
        for partner, company, amount in orders_group:
            p_id = partner.id
            risk_currency = partner.purchase_risk_currency_id or company.currency_id
            converted = company.currency_id._convert(
                amount,
                risk_currency,
                company,
                today,
                round=False,
            )
            po_risk[p_id] = po_risk.get(p_id, 0.0) + converted
        # --- Vendor bill risk ---
        # amount_residual_signed is always in company currency (negative for payables).
        bills_group = self.env["account.move"]._read_group(
            domain=[
                ("commercial_partner_id", "in", vendors.ids),
                ("move_type", "=", "in_invoice"),
                ("state", "in", ("draft", "posted")),
                ("payment_state", "not in", ("paid", "reversed")),
            ],
            groupby=["commercial_partner_id", "company_id", "state"],
            aggregates=["amount_residual_signed:sum"],
        )
        bill_draft_risk = {}
        bill_open_risk = {}
        for partner, company, state, amount in bills_group:
            p_id = partner.id
            if p_id in vendors.ids:
                risk_currency = partner.purchase_risk_currency_id or company.currency_id
                # Negate: vendor bills carry a negative sign in amount_residual_signed.
                converted_amount = company.currency_id._convert(
                    -amount,
                    risk_currency,
                    company,
                    today,
                    round=False,
                )
                if state == "draft":
                    bill_draft_risk[p_id] = (
                        bill_draft_risk.get(p_id, 0.0) + converted_amount
                    )
                elif state == "posted":
                    bill_open_risk[p_id] = (
                        bill_open_risk.get(p_id, 0.0) + converted_amount
                    )

        for vendor in vendors:
            v_id = vendor._origin.id or vendor.id
            total_po = po_risk.get(v_id, 0.0)
            total_bill_draft = bill_draft_risk.get(v_id, 0.0)
            total_bill_open = bill_open_risk.get(v_id, 0.0)

            vendor.purchase_risk_po = total_po
            vendor.purchase_risk_bill_draft = total_bill_draft
            vendor.purchase_risk_bill_open = total_bill_open

            total_risk = total_po + total_bill_draft + total_bill_open
            vendor.purchase_risk = total_risk
            if vendor.purchase_risk_limit:
                vendor.purchase_risk_percent = round(
                    100.0 * total_risk / vendor.purchase_risk_limit, 2
                )
            else:
                vendor.purchase_risk_percent = 0.0

    def _get_field_purchase_risk_model_domain(self, field_name):
        vendors = self.mapped("commercial_partner_id").ids
        if field_name == "purchase_risk_po":
            return "purchase.order.line", [("purchase_risk_partner_id", "in", vendors)]
        elif field_name == "purchase_risk_bill_draft":
            return "account.move", [
                ("commercial_partner_id", "in", vendors),
                ("move_type", "=", "in_invoice"),
                ("state", "=", "draft"),
                ("payment_state", "not in", ("paid", "reversed")),
            ]
        elif field_name == "purchase_risk_bill_open":
            return "account.move", [
                ("commercial_partner_id", "in", vendors),
                ("move_type", "=", "in_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "not in", ("paid", "reversed")),
            ]
        return False, []

    def open_purchase_risk_pivot_info(self):
        open_risk_field = self.env.context.get("open_risk_field")
        if not open_risk_field:
            return  # pragma: no cover
        model_name, domain = self._get_field_purchase_risk_model_domain(open_risk_field)
        if not model_name:
            return  # pragma: no cover

        view_name = "financial_risk_{}_pivot_view".format(model_name.replace(".", "_"))
        view_id = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [("name", "=", view_name), ("model", "=", "ir.ui.view")],
                limit=1,
            )
            .res_id
        )
        return {
            "name": _("Purchase financial risk information"),
            "view_mode": "pivot",
            "res_model": model_name,
            "view_id": view_id,
            "type": "ir.actions.act_window",
            "context": self.env.context,
            "domain": domain,
        }
