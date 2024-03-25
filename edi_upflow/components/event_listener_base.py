# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class BaseUpflowEventListner(Component):

    _name = "base.upflow.event.listener"
    _inherit = "base.event.listener"

    def _get_followup_backend(self, record):
        return record.company_id.upflow_backend_id

    def _get_exchange_record_vals(self, record):
        return {
            "model": record._name,
            "res_id": record.id,
        }

    def _create_and_generate_upflow_exchange_record(
        self, backend, exchange_type, record
    ):
        if backend:
            exchange_record = backend.create_record(
                exchange_type, self._get_exchange_record_vals(record)
            )
            backend.with_delay().exchange_generate(exchange_record)
        else:
            return self.env["edi.exchange.record"]
        return exchange_record

    def send_moves_to_upflow(self, moves):
        move_exchanges = self.env["edi.exchange.record"].browse()
        # if a lot of things happen in this same transaction probably
        # depends are not computed yet better to refresh value
        moves._compute_upflow_type()
        for move in moves:
            exchange_type, pdf_exchange = move.mapping_upflow_exchange().get(
                move.upflow_type,
                (
                    None,
                    None,
                ),
            )

            if not exchange_type:
                continue
            customer_exchange = self.env["edi.exchange.record"]
            backend = (
                move.upflow_commercial_partner_id.upflow_edi_backend_id
                or self._get_followup_backend(move)
            )
            if not move.upflow_commercial_partner_id.upflow_uuid:
                customer_exchange = self._create_and_generate_upflow_exchange_record(
                    backend, "upflow_post_customers", move.upflow_commercial_partner_id
                )
                move.upflow_commercial_partner_id.upflow_edi_backend_id = backend
            account_move_exchange = self._create_and_generate_upflow_exchange_record(
                backend, exchange_type, move
            )
            if not account_move_exchange:
                # empty recordset could be return in case no backend found
                continue
            account_move_exchange.dependent_exchange_ids |= customer_exchange
            if pdf_exchange:
                pdf_exchange = self._create_and_generate_upflow_exchange_record(
                    backend, pdf_exchange, move
                )
                pdf_exchange.dependent_exchange_ids |= account_move_exchange
            move_exchanges |= account_move_exchange
        return move_exchanges
