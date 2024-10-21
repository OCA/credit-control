# Copyright 2024 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class PartnerRiskExceededWiz(models.TransientModel):
    _inherit = "partner.risk.exceeded.wiz"

    def _post_sale_order_confirm_risk(self, origin_record):
        template = origin_record.company_id.sale_order_confirm_risk_template_id
        if template:
            template.send_mail(origin_record.id)

    def button_continue(self):
        continue_result = super().button_continue()
        origin_record = self.origin_reference
        if origin_record._name == "sale.order":
            self._post_sale_order_confirm_risk(origin_record)
        return continue_result
