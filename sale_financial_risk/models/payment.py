# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _set_transaction_authorized(self):
        """Bypass risk for sale confirmation triggered by this method"""
        return super(
            PaymentTransaction, self.with_context(bypass_risk=True)
        )._set_transaction_authorized()

    def _reconcile_after_transaction_done(self):
        """Bypass risk for sale confirmation and invoice creation triggered
        by this method
        """
        return super(
            PaymentTransaction, self.with_context(bypass_risk=True)
        )._reconcile_after_transaction_done()
