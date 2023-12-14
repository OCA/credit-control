# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_unpaid_margin = fields.Integer(
        string="Maturity Margin",
        help="Days after due date to set an invoice as unpaid. "
        "The change of this field recompute all partners risk, "
        "be patient.",
    )
    allow_overrisk_invoice_validation = fields.Boolean(
        string="Allow invoice validation over the risk",
        help="Always allow the validation of draft invoices. "
        "Useful when the flow comes from sales orders and the over-risk "
        "has already been allowed when confirming these.",
    )
