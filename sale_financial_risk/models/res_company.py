# Copyright 2024 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_order_confirm_risk_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email template sent when confirming sale order risk",
        help="This email template is sent when "
        "the 'Partner risk exceeded wizard' for a sale order is confirmed.",
    )
