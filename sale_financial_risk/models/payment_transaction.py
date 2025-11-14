# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _set_authorized(self, **kwargs):
        """Bypass risk for sale confirmation triggered by this method"""
        self = self.with_context(bypass_risk=True)
        return super()._set_authorized(**kwargs)

    def _post_process(self):
        """Bypass risk for sale confirmation and invoice creation triggered
        by this method
        """
        self = self.with_context(bypass_risk=True)
        return super()._post_process()
