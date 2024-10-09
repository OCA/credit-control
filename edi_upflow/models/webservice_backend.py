# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class WebserviceBackend(models.Model):

    _inherit = "webservice.backend"

    upflow_api_key = fields.Char(string="Upflow API Key", auth_type="upflow")
    upflow_api_secret = fields.Char(string="Upflow API Secret", auth_type="upflow")
    auth_type = fields.Selection(
        selection_add=[("upflow", "Upflow.io")],
        ondelete={
            "upflow": lambda recs: recs.write({"auth_type": "none"}),
        },
    )

    @property
    def _server_env_fields(self):
        fields = super()._server_env_fields
        fields.update(
            {
                "upflow_api_key": {},
                "upflow_api_secret": {},
            }
        )
        return fields
