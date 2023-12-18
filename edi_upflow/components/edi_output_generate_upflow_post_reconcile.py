# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json

from odoo.addons.component.core import Component


class EdiOutputGenerateUpflowPostReconcile(Component):
    _name = "edi.output.generate.upflow_post_reconcile"
    _inherit = "base.upflow.edi.output.generate"
    _exchange_type = "upflow_post_reconcile"

    def generate(self):
        self._wait_related_exchange_to_be_sent_and_processed()
        if not self.record:
            raise EdiOutputGenerateUpflowPostReconcileError(
                "No record found to generate the payload."
            )
        if self.env.context.get("unlinking_reconcile", False):
            payload = self.record._prepare_reconcile_payload()
        else:
            payload = self.record.get_upflow_api_post_reconcile_payload()
        return json.dumps(payload)


class EdiOutputGenerateUpflowPostReconcileError(Exception):
    pass
