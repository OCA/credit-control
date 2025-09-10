# Copyright 2025 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends(
        "show_product_stickers", "line_ids.product_id", "credit_policy_state_id"
    )
    def _compute_sticker_ids(self):
        res = super()._compute_sticker_ids()
        for record in self:
            allowed_credit_company_ids = [False]
            if record.credit_policy_state_id.insure_invoices:
                allowed_credit_company_ids.append(record.credit_policy_company_id.id)
            record.sticker_ids -= record.sticker_ids.filtered_domain(
                [("credit_policy_company_id", "not in", allowed_credit_company_ids)]
            )
        return res
