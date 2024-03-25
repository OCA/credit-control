# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component

logger = logging.getLogger(__name__)


class AccountPartialReconcileUpflowEventListener(Component):

    _name = "account.partial.reconcile.upflow.event.listener"
    _inherit = "base.upflow.event.listener"
    _apply_on = ["account.partial.reconcile"]

    def _filter_relevant_account_event_state_method(self, states):
        """Only accounting event (ignore pdf events)"""
        event_types = (
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_invoices"),
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_credit_notes"),
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_payments"),
            self.env.ref("edi_upflow.upflow_edi_exchange_type_post_refunds"),
        )
        return (
            lambda ex, event_types=event_types, states=states: ex.type_id in event_types
            and ex.edi_exchange_state in states
        )

    def _ensure_related_move_is_synced(self, reconcile_exchange, move):
        "output_sent_and_processed"
        ongoing_move_exchanges = move.exchange_record_ids.filtered(
            self._filter_relevant_account_event_state_method(
                [
                    "new",
                    "output_pending",
                    "output_sent",
                ]
            )
        )
        finalized_move_exchanges = move.exchange_record_ids.filtered(
            self._filter_relevant_account_event_state_method(
                [
                    "output_sent_and_processed",
                ]
            )
        )
        if move.upflow_uuid or ongoing_move_exchanges:
            # we don't know if an error happens on the first exchange
            # then user manage to create an other exchange that passed
            # we only link on going exchange and processed
            # and there is a good change that the event will raise anyway
            reconcile_exchange.dependent_exchange_ids |= (
                ongoing_move_exchanges | finalized_move_exchanges
            )
        else:
            self._create_missing_exchange_record(reconcile_exchange, move)

    def _create_missing_exchange_record(self, reconcile_exchange, move):
        if move.upflow_commercial_partner_id:
            # create payment from bank statements
            # do not necessarily generate account.payment

            # At this point we expect customer to be already synchronized
            reconcile_exchange.dependent_exchange_ids |= self.send_moves_to_upflow(move)
        else:
            raise UserError(
                _(
                    "You can reconcile journal items because the journal entry "
                    "%s (ID: %s) is not synchronisable with upflow.io, "
                    "because partner is not set but required."
                )
                % (
                    move.name,
                    move.id,
                )
            )

    def _is_customer_entry(self, reconcile):
        # both should share the same type anyway
        return (
            reconcile.debit_move_id.account_id.user_type_id.type == "receivable"
            or reconcile.credit_move_id.account_id.user_type_id.type == "receivable"
        )

    def _get_reconcile_partner(self, account_partial_reconcile):
        """credit/debit move line should be link to the same partner
        and partner_id should be present on receivable account.move.line

        Anyway we try to be kind here and find
        """
        return (
            account_partial_reconcile.debit_move_id.partner_id.commercial_partner_id
            or account_partial_reconcile.credit_move_id.partner_id.commercial_partner_id
            or account_partial_reconcile.debit_move_id.move_id.commercial_partner_id
            or account_partial_reconcile.credit_move_id.move_id.commercial_partner_id
        )

    def _get_backend(self, account_partial_reconcile):
        partner = self._get_reconcile_partner(account_partial_reconcile)
        return partner.upflow_edi_backend_id or self._get_followup_backend(
            account_partial_reconcile.debit_move_id.move_id
        )

    def on_record_create(self, account_partial_reconcile, fields=None):
        if not self._is_customer_entry(account_partial_reconcile):
            return

        reconcile_exchange = self._create_and_generate_upflow_exchange_record(
            self._get_backend(account_partial_reconcile),
            "upflow_post_reconcile",
            account_partial_reconcile,
        )
        if not reconcile_exchange:
            # in case no backend is returned there are nothing to do
            return
        self._ensure_related_move_is_synced(
            reconcile_exchange,
            account_partial_reconcile.credit_move_id.move_id,
        )
        self._ensure_related_move_is_synced(
            reconcile_exchange,
            account_partial_reconcile.debit_move_id.move_id,
        )

    def on_record_unlink(self, account_partial_reconcile):
        if account_partial_reconcile.sent_to_upflow:
            # we are not using _create_and_generate_upflow_exchange_record
            # here because we want to generate payload synchronously
            # after wards record will be unlinked with no chance to retrieves
            # upflow_uuid
            backend = self._get_backend(account_partial_reconcile)
            if backend:
                exchange_record = backend.create_record(
                    "upflow_post_reconcile",
                    self._get_exchange_record_vals(account_partial_reconcile),
                )
                backend.with_context(unlinking_reconcile=True).exchange_generate(
                    exchange_record
                )
