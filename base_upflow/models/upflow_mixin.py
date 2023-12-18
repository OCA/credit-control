# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class UpflowMixin(models.AbstractModel):
    _name = "upflow.mixin"
    _description = "Upflow mixin to add common fields and behaviour"

    upflow_uuid = fields.Char(readonly=True, copy=False)
    upflow_direct_url = fields.Char(readonly=True, copy=False)

    def prepare_base_payload(self):
        self.ensure_one()
        data = {
            "externalId": str(self.id),
        }
        if self.upflow_uuid:
            data["id"] = self.upflow_uuid
        return data
