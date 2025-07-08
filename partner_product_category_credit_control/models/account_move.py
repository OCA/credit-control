from odoo import models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        for record in self:
            if record.partner_id and record.move_type == 'out_invoice':
                for line in record.invoice_line_ids:
                    credit_line = self.env["product.category.credit"].search([
                        ("partner_id", "=", record.partner_id.id),
                        ("category_id", "=", line.product_id.categ_id.id),
                        ("type", "=", "customer")
                    ], limit=1)
                    if credit_line:
                        invoices = self.env['account.move'].search([
                            ("partner_id", "=", record.partner_id.id),
                            ("move_type", "=", "out_invoice"),
                            ("state", "=", "posted"),
                            ("payment_state", "in", ["not_paid", "partial"])
                        ])
                        total = sum(inv.amount_residual for inv in invoices)
                        total += sum(line.price_subtotal for line in record.invoice_line_ids if line.product_id.categ_id == credit_line.category_id)
                        if total > credit_line.credit:
                            raise ValidationError(f"El cliente excede su línea de crédito para la categoría '{credit_line.category_id.name}'.")

            elif record.partner_id and record.move_type == 'in_invoice':
                credit_line = record.partner_id.supplier_credit_id
                if credit_line:
                    invoices = self.env['account.move'].search([
                        ("partner_id", "=", record.partner_id.id),
                        ("move_type", "=", "in_invoice"),
                        ("state", "=", "posted"),
                        ("payment_state", "in", ["not_paid", "partial"])
                    ])
                    total = sum(inv.amount_residual for inv in invoices) + record.amount_total
                    if total > credit_line.credit:
                        raise ValidationError("No se puede confirmar la factura porque se ha rebasado el crédito disponible con el proveedor.")

        result = super().action_post()

        all_credit_lines = self.env['product.category.credit'].search([])
        all_credit_lines._invalidate_cache()
        all_credit_lines._compute_used_credit()
        all_credit_lines._compute_available_credit()

        return result