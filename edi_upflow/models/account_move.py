# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    upflow_type = fields.Selection(
        store=True,
        copy=False,
        required=True,
        readonly=False,
        default="none",
        compute="_compute_upflow_type",
    )
    """
    In some corner case and for historical reason we may force
    upflow types likes migrating data from other system
    """

    def get_latest_upflow_exchange(self):
        # we could probably inprove this a bit according state
        # for the time being as exchange_record are sorted by
        # `exchanged_on desc and id desc` this should gives
        # the latest exchange
        return fields.first(
            self.exchange_record_ids.filtered(
                lambda exchange: exchange.type_id.code
                in [
                    "upflow_post_invoice",
                    "upflow_post_credit_notes",
                    "upflow_post_payments",
                    "upflow_post_refunds",
                ]
            )
        )

    @api.depends("state")
    def _compute_upflow_type(self):
        not_processed = self.browse()
        for move in self:
            if move.upflow_type != "none":
                move.upflow_type = move.upflow_type
                continue
            latest_exchange = move.get_latest_upflow_exchange()
            if latest_exchange:
                move.upflow_type = self.mapping_exchange_upflow().get(
                    latest_exchange.type_id.code, "none"
                )
            if move.upflow_type == "none":
                not_processed |= move
        super(AccountMove, not_processed)._compute_upflow_type()

    @api.model
    def mapping_upflow_exchange(self):
        """mappings between upflow types (using keys
        of reconcile payload) and exchange types
        """
        return {
            "invoices": (
                "upflow_post_invoice",
                "upflow_post_invoice_pdf",
            ),
            "payments": (
                "upflow_post_payments",
                None,
            ),
            "creditNotes": (
                "upflow_post_credit_notes",
                "upflow_post_credit_notes_pdf",
            ),
            "refunds": (
                "upflow_post_refunds",
                None,
            ),
        }

    @api.model
    def mapping_exchange_upflow(self):
        mapping = {}
        for key, value in self.mapping_upflow_exchange().items():
            mapping[value[0]] = key
        return mapping
