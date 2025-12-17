from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    credit_control_active = fields.Boolean(
        string="Activate Credit Control",
        default=True,
        help="Enable or disable credit control for this invoice."
    )

    def toggle_credit_control_active(self):
        """Toggle the credit_control_active field."""
        for record in self:
            record.credit_control_active = not record.credit_control_active

    def action_post(self):
        for record in self:
            # Skip credit control if disabled for this invoice
            if not record.credit_control_active:
                continue
                
            if (
                not self.env.user.has_group("account.group_account_manager")
                and record.partner_id
                and record.move_type == "out_invoice"
            ):
                for line in record.invoice_line_ids:
                    credit_line = self.env["product.category.credit"].search(
                        [
                            ("partner_id", "=", record.partner_id.id),
                            ("category_id", "=", line.product_id.categ_id.id),
                            ("type", "=", "customer"),
                        ],
                        limit=1,
                    )
                    if credit_line and credit_line.credit > 0:
                        invoices = self.env["account.move"].search(
                            [
                                ("partner_id", "=", record.partner_id.id),
                                ("move_type", "=", "out_invoice"),
                                ("state", "=", "posted"),
                                ("payment_state", "in", ["not_paid", "partial"]),
                            ]
                        )
                        total = sum(inv.amount_residual for inv in invoices)
                        total += sum(
                            line.price_subtotal
                            for line in record.invoice_line_ids
                            if line.product_id.categ_id == credit_line.category_id
                        )
                        if total > credit_line.credit:
                            raise ValidationError(
                                _(f"The customer has exceeded their credit limit \
                                      for the category \
                                          '{credit_line.category_id.name}'.")
                            )

            elif (
                not self.env.user.has_group("account.group_account_manager")
                and record.partner_id
                and record.move_type == "in_invoice"
            ):
                credit_line = record.partner_id.supplier_credit_id
                if credit_line:
                    invoices = self.env["account.move"].search(
                        [
                            ("partner_id", "=", record.partner_id.id),
                            ("move_type", "=", "in_invoice"),
                            ("state", "=", "posted"),
                            ("payment_state", "in", ["not_paid", "partial"]),
                        ]
                    )
                    total = (
                        sum(inv.amount_residual for inv in invoices)
                        + record.amount_total
                    )
                    if total > credit_line.credit:
                        raise ValidationError(
                            _(
                                "Cannot confirm the invoice because the \
                                    available credit with the vendor has \
                                          been exceeded."
                            )
                        )

        result = super().action_post()

        all_credit_lines = self.env["product.category.credit"].search([])
        all_credit_lines._invalidate_cache()
        all_credit_lines._compute_used_credit()
        all_credit_lines._compute_available_credit()

        return result
