# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_limit_exception = fields.Boolean(
        string="Apply Credit Limit Validation",
        default=True,
        help="""When checked, the partner will be validated against
        average credit days on order confirmation.""",
    )
    credit_limit_day = fields.Integer(
        string="Credit Limit (Days)",
        help="Maximum allowed average age (in days) of open invoices for this partner.",
    )
    credit_average_day = fields.Float(
        string="Average Credit Days",
        compute="_compute_credit_average_day",
        store=False,
        help="Computed average age (in days) of the partner open invoices.",
    )

    def _compute_credit_average_day(self):
        """
        Compute the average age (in days) of all open customer invoices.
        An invoice is considered when:
            - move_type = 'out_invoice'
            - state = 'posted'
            - amount_residual > 0 (still unpaid or partially paid)

        The age of an invoice = today - invoice_date.
        If invoice_date is missing, fallback to move.date or create_date.
        """
        AccountMove = self.env["account.move"]
        today = fields.Date.context_today(self)
        for partner in self:
            # Search unpaid posted customer invoices
            moves = AccountMove.search(
                [
                    ("partner_id", "=", partner.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("amount_residual", ">", 0),
                ]
            )
            ages = []

            for move in moves:
                # Determine invoice date using a safe fallback chain
                invoice_date = (
                    move.invoice_date
                    or move.date
                    or (move.create_date.date() if move.create_date else None)
                )

                if isinstance(invoice_date, str):
                    invoice_date = fields.Date.from_string(invoice_date)

                # If still no date found, skip invoice
                if not invoice_date:
                    continue

                # Calculate age
                age_days = (today - invoice_date).days

                # Avoid negative values if invoice date is in the future
                ages.append(max(age_days, 0))

            # Assign computed average or 0 if no invoices
            partner.credit_average_day = (sum(ages) / len(ages)) if ages else 0.0
