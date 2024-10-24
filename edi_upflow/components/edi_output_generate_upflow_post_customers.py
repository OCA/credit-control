# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json

from odoo.addons.component.core import Component


class EdiOutputGenerateUpflowPostCustomers(Component):
    _name = "edi.output.generate.upflow_post_customers"
    _inherit = "base.upflow.edi.output.generate"
    _exchange_type = "upflow_post_customers"

    def generate(self):
        if not self.record:
            raise EdiOutputGenerateUpflowPostCustomersError(
                "No record found to generate the payload."
            )
        payload = self.record.get_upflow_api_post_customers_payload()
        return json.dumps(payload)


class EdiOutputGenerateUpflowPostCustomersError(Exception):
    pass
