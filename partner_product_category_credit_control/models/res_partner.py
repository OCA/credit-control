from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    product_category_credit_ids = fields.One2many(
        "product.category.credit",
        "partner_id",
        string="Líneas de crédito (cliente)",
        domain=[("type", "=", "customer")],
    )

    supplier_credit_id = fields.Many2one(
        "product.category.credit",
        string="Línea de crédito (proveedor)",
        domain=[("type", "=", "supplier")],
    )
