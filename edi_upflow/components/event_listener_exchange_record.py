# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class ExchangeRecordUpflowEventListener(Component):
    """Intent of this class is to listen others exchange

    queue job task to create the next one and speed-up synchro
    """

    _name = "exchange.record.upflow.event.listener"
    _inherit = "base.event.listener"
    _apply_on = ["edi.exchange.record"]

    def on_edi_exchange_generate_complete(self, exchange_record):
        """save time creating task right away and do no wait cron task"""
        if exchange_record.backend_id.backend_type_id.code == "upflow":
            exchange_record.with_delay().action_exchange_send()

    def on_edi_exchange_send_complete(self, exchange_record):
        if (
            exchange_record.backend_id.backend_type_id.code == "upflow"
            and exchange_record.ws_response_status_code >= 200
            and exchange_record.ws_response_status_code < 300
        ):
            # speed up post treatment creating job right away avoiding to wait cron task
            exchange_record.backend_id.with_delay()._exchange_output_check_state(
                exchange_record
            )
