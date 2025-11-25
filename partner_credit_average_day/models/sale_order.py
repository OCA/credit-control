# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        """
        Extend Sale Order confirmation to enforce customer credit rules:
        - If `credit_limit_exception` is enabled on the partner,
        - And user is NOT in the Credit Manager group,
        - And partner's average invoice age exceeds the configured limit,
        Then block confirmation and show a detailed list of open invoices.
        """
        AccountMove = self.env["account.move"]
        today = fields.Date.context_today(self)

        for order in self:
            partner = order.partner_id

            if (
                not partner.credit_limit_exception
                or self.env.user.has_group(
                    "partner_credit_average_day.group_credit_manager"
                )
                or not partner.credit_limit_day
            ):
                continue

            avg_days = float(partner.credit_average_day or 0.0)

            # If average exceeds limit → BLOCK ORDER CONFIRMATION
            if avg_days > float(partner.credit_limit_day):
                # Fetch all open posted customer invoices
                open_invoices = AccountMove.search(
                    [
                        ("partner_id", "=", partner.id),
                        ("move_type", "=", "out_invoice"),
                        ("state", "=", "posted"),
                        ("amount_residual", ">", 0),
                    ],
                    order="invoice_date asc",
                )

                # Header lines
                message_lines = [
                    _(
                        'The customer "%(name)s" exceeds the allowed credit limit.\n'
                        "Average invoice age: %(avg).2f days\n"
                        "Allowed limit: %(limit)s days\n"
                    )
                    % {
                        "name": partner.display_name,
                        "avg": avg_days,
                        "limit": partner.credit_limit_day,
                    },
                    _("Open invoices:"),
                    "",
                ]

                # Detailed invoice list
                for inv in open_invoices:
                    invoice_date = (
                        inv.invoice_date
                        or inv.date
                        or (inv.create_date.date() if inv.create_date else None)
                    )
                    if isinstance(invoice_date, str):
                        invoice_date = fields.Date.from_string(invoice_date)
                    if not invoice_date:
                        continue

                    age_days = (today - invoice_date).days
                    age_days = max(age_days, 0)

                    message_lines.append(
                        f"- {inv.name or inv.display_name} | "
                        f"Date: {invoice_date} | "
                        f"Residual: {inv.amount_residual:.2f} | "
                        f"Age: {age_days} days"
                    )

                # Raise compiled message
                raise UserError("\n".join(message_lines))

        return super().action_confirm()
