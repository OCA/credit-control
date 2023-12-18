# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.edi_oca.models.edi_backend import _get_exception_msg


class BaseUpflowEDIOutputCheck(Component):
    _name = "base.upflow.edi.output.check"
    _inherit = "edi.component.check.mixin"
    _usage = "output.check"
    _backend_type = "upflow"

    _action = "check"

    def check(self):
        try:
            self._check_and_process()
        except Exception as ex:
            state = "output_sent_and_error"
            self.exchange_record.exchange_error = (
                f"{ex.__class__.__name__}: {_get_exception_msg()}"
            )
        else:
            state = "output_sent_and_processed"
        finally:
            self.exchange_record.edi_exchange_state = state

    def _check_ws_response_status_code(self):
        if (
            self.exchange_record.ws_response_status_code < 200
            or self.exchange_record.ws_response_status_code >= 300
        ):
            raise ValidationError(
                _(
                    "Not a valid HTTP error (expected 2xx, received %s) "
                    "in order to processed the payload (%s)"
                )
                % (
                    self.exchange_record.ws_response_status_code,
                    self._get_upflow_response(),
                )
            )

    def _get_upflow_response(self):
        return self.exchange_record._get_file_content(field_name="ws_response_content")

    def _parse_upflow_response(self):
        try:
            data = json.loads(self._get_upflow_response())
        except Exception:
            data = {}
        return data

    def _get_response_upflow_uuid(self):
        return self._parse_upflow_response()["id"]

    def _get_response_upflow_direct_url(self):
        return self._parse_upflow_response().get("directUrl", False)

    def _set_record_upflow_uuid(self):
        self.exchange_record.record.upflow_uuid = self._get_response_upflow_uuid()

    def _set_record_upflow_direct_url(self):
        self.exchange_record.record.upflow_direct_url = (
            self._get_response_upflow_direct_url()
        )

    def _upflow_check_and_process(self):
        self._check_ws_response_status_code()
        self._set_record_upflow_uuid()
        self._set_record_upflow_direct_url()

    def _check_and_process(self):
        raise NotImplementedError(
            _(
                "You should implement _check_and_process method "
                "to process upflow.io REST response "
                "on this exchange type (code: %s)"
            )
            % (self.exchange_record.type_id.code)
        )
