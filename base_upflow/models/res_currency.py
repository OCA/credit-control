# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class Currency(models.Model):
    _inherit = "res.currency"

    def to_lowest_division(self, currency_amount):
        """return amount as integer to represent
        the lowest division of the currency
        (e.g., cents for US Dollars).
        """
        return round(currency_amount / self.rounding)
