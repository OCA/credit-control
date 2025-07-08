from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    product_category_credit_ids = fields.One2many(
        "product.category.credit",
        "partner_id",
        string="Credit Lines (Customer)",
        domain=[("type", "=", "customer")],
    )

    supplier_credit_id = fields.Many2one(
        "product.category.credit",
        string="Credit Line (Supplier)",
        domain=[("type", "=", "supplier")],
    )
