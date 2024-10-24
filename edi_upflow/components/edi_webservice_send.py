# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from collections import defaultdict

from odoo.addons.component.core import Component


class EDIWebserviceSend(Component):

    _name = "edi.webservice.send"
    _inherit = "edi.webservice.send"

    def _get_call_params(self):
        method, pargs, kwargs = super()._get_call_params()
        upflow_uuid = getattr(self.exchange_record.record, "upflow_uuid", None)
        commercial_partner_id = getattr(
            self.exchange_record.record, "commercial_partner_id", None
        )
        kwargs["url_params"]["endpoint"] = kwargs["url_params"]["endpoint"].format_map(
            defaultdict(
                str,
                upflow_uuid=upflow_uuid,
                commercial_upflow_uuid=commercial_partner_id.upflow_uuid
                if commercial_partner_id
                else None,
            )
        )
        return method, pargs, kwargs
