# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_upflow_extra_payment_api_payload(self):
        self.ensure_one()
        return {
            "instrument": self.payment_method_id.upflow_instrument,
        }
