# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PartnerRiskExceededWiz(models.TransientModel):
    _name = "partner.risk.exceeded.wiz"
    _description = "Partner Risk Exceeded Wizard"

    partner_id = fields.Many2one(
        comodel_name="res.partner", readonly=True, string="Customer"
    )
    exception_msg = fields.Text(readonly=True)
    origin_reference = fields.Reference(
        lambda self: [
            (m.model, m.name) for m in self.env["ir.model"].sudo().search([])
        ],
        string="Object",
    )
    continue_method = fields.Char()

    def action_show(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Partner risk exceeded"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def button_continue(self):
        self.ensure_one()
        return getattr(
            self.origin_reference.with_context(bypass_risk=True), self.continue_method
        )()
