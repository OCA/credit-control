# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    # to be place in a view extending account_payment_mode module
    # and/or setting data
    upflow_instrument = fields.Selection(
        [
            ("WIRE_TRANSFER", "Wire Transfer"),
            ("DIRECT_DEBIT", "Direct Debit"),
            ("CARD", "Card"),
            ("CASH", "Cash"),
            ("CHECK", "Check"),
            ("UNKNOWN", "Unknown"),
        ],
        "Upflow instrument",
        required=True,
        default="UNKNOWN",
        copy=False,
        help="Used by upflow.io integration to set payment instrument field",
    )
