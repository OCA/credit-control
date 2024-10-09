# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class EdiOutputCheckUpflowPostCustomers(Component):
    _name = "edi.output.check.upflow_post_customers"
    _inherit = "base.upflow.edi.output.check"
    _exchange_type = "upflow_post_customers"

    def _check_and_process(self):
        self._upflow_check_and_process()
        for contact in self._parse_upflow_response().get("contacts", []):
            if not contact.get("externalId"):
                _logger.warning("No externalId found for contact %s", contact.get("id"))
                continue
            self.exchange_record.record.child_ids.filtered_domain(
                [("id", "=", int(contact.get("externalId")))]
            ).upflow_uuid = contact.get("id")
