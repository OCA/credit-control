# Copyright 2026 Graeme Gellatly
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_risk_company_domain(self):
        return Domain.TRUE

    def _compute_risk_account_amount(self):
        return super(ResPartner, self.sudo())._compute_risk_account_amount()
