# Copyright 2023 Tecnativa - Stefan Ungureanu
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class InvoiceRiskInsuranceWizard(models.TransientModel):
    _name = "partner.risk.insurance.wizard"
    _description = "Wizard to see invoices sorted by risk"

    date_from = fields.Date(
        string="From", required=True, default=fields.Date.context_today
    )
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)
    only_unpaid = fields.Boolean(
        help="If check, includes only invoices in state not paid"
    )

    def get_moves_domain(self):
        domain = [
            ("state", "=", "posted"),
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]
        if self.only_unpaid:
            domain.append(("payment_state", "=", "not_paid"))
        return domain

    def action_print_report(self):
        moves = self.env["account.move"].search(self.get_moves_domain())
        if not moves:
            raise ValidationError(
                _(
                    "There aren't moves between this dates\n"
                    "Please, select different dates"
                )
            )
        return self.env.ref(
            "partner_risk_insurance.action_report_invoice_risk_insurance_template"
        ).report_action(moves, False)
