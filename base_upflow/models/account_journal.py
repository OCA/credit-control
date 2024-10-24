# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    upflow_bank_account_uuid = fields.Char(
        "Upflow bank account technical id",
        help="Upflow.io bank account UUID linked to payment done in this journal.",
    )
