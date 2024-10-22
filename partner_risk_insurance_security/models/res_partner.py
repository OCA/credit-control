from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_full_access_user = fields.Boolean(
        string="Is Full Access User",
        compute="_compute_is_full_access_user",
        store=False,
    )

    @api.depends("user_id")
    def _compute_is_full_access_user(self):
        for partner in self:
            partner.is_full_access_user = (
                self.env.user
                in self.env.ref(
                    "partner_risk_insurance_security.group_full_access_credit_policy_state"
                ).users
            )
