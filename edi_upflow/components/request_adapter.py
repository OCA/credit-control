# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.component.core import Component


class BaseRestRequestsAdapter(Component):

    _inherit = "base.request"

    def _get_headers_for_upflow(self, **kw):
        return {
            "X-Api-Key": self.collection.upflow_api_key,
            "X-Api-Secret": self.collection.upflow_api_secret,
        }
