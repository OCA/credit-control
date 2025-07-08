from odoo import api, fields, models


class ProductCategoryCredit(models.Model):
    _name = "product.category.credit"
    _description = "Credit by Product Category"
    _order = "partner_id, category_id"

    name = fields.Char("Credit Key", required=True)
    partner_id = fields.Many2one(
        "res.partner", string="Contact", required=True, ondelete="cascade"
    )
    category_id = fields.Many2one("product.category", string="Product Category")
    credit = fields.Float("Authorized Amount")
    type = fields.Selection(
        [("customer", "Customer"), ("supplier", "Supplier")], required=True
    )
    used_credit = fields.Float(
        "Used Amount", compute="_compute_used_credit", store=True
    )
    available_credit = fields.Float(
        "Available Amount", compute="_compute_available_credit", store=True
    )

    @api.depends("credit", "used_credit")
    def _compute_available_credit(self):
        for rec in self:
            rec.available_credit = rec.credit - rec.used_credit

    @api.depends("partner_id", "category_id", "type")
    def _compute_used_credit(self):
        for rec in self:
            domain = [
                ("partner_id", "=", rec.partner_id.id),
                ("state", "=", "posted"),
                ("payment_state", "in", ["not_paid", "partial"]),
            ]
            if rec.type == "customer":
                domain += [("move_type", "=", "out_invoice")]
            elif rec.type == "supplier":
                domain += [("move_type", "=", "in_invoice")]
            invoices = self.env["account.move"].search(domain)
            total = 0.0
            for inv in invoices:
                for line in inv.invoice_line_ids:
                    if rec.type == "supplier" or (
                        line.product_id.categ_id == rec.category_id
                    ):
                        total += line.price_subtotal
            rec.used_credit = total

    _sql_constraints = [
        (
            "unique_credit_per_category",
            "UNIQUE(partner_id, category_id, type)",
            "Only one credit line per category and type \
                is allowed per contact.",
        )
    ]
