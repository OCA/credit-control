# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json

from odoo.addons.component.core import Component


class EdiOutputGenerateUpflowPostCreditNotes(Component):
    _name = "edi.output.generate.upflow_post_credit_notes"
    _inherit = "base.upflow.edi.output.generate"
    _exchange_type = "upflow_post_credit_notes"

    def generate(self):
        self._wait_related_exchange_to_be_sent_and_processed()
        return json.dumps(
            self.exchange_record.record.get_upflow_api_post_credit_note_payload()
        )
