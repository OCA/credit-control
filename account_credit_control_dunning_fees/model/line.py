# Copyright 2014-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class CreditControlLine(models.Model):
    """Add dunning_fees_amount_fees field"""

    _inherit = "credit.control.line"

    dunning_fees_amount = fields.Float(string="Fees")
    balance_due_total = fields.Float(
        string="Balance due with fees", compute="_compute_balance_due"
    )

    @api.depends("dunning_fees_amount", "balance_due")
    def _compute_balance_due(self):
        for line in self:
            line.balance_due_total = line.balance_due + line.dunning_fees_amount
