# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PartnerCreditLimitWizard(models.TransientModel):
    _name = "partner.credit.limit.wizard"
    _description = "Partner Credit History"

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Partner", required=True
    )
    amount = fields.Float(string="New Amount", required=True)
    note = fields.Char(string="Reason", required=True)

    def action_confirm(self):
        """We will need to apply sudo because regular user does not have
        creation permissions."""
        history = (
            self.env["res.partner.credit.history"]
            .sudo()
            .create(
                {
                    "partner_id": self.partner_id.id,
                    "note": self.note,
                    "previous_amount": self.partner_id.credit_limit,
                    "new_amount": self.amount,
                }
            )
        )
        self.partner_id.credit_limit = self.amount
        return history
