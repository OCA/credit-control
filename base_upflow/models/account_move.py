# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64

from odoo import _,fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "upflow.mixin"]

    upflow_commercial_partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_upflow_commercial_partner_id",
        help="Technical field to get the upflow customer to use on account move",
    )

    def _compute_upflow_commercial_partner_id(self):
        # while using OD as counter part or bank statement
        # there are chance that partner_id is not set on account.move
        # so we try to get the information on first receivable account.move.line
        for move in self:
            self.upflow_commercial_partner_id = (
                self.partner_id.commercial_partner_id
                or self.line_ids.filtered(
                    lambda line: line.account_id.user_type_id.type == "receivable"
                ).partner_id.commercial_partner_id
            )

    def _format_upflow_amount(self, amount, currency=None):
        if not currency:
            currency = self.currency_id
        return currency.to_lowest_division(amount)

    def _prepare_upflow_api_payload(self):
        payload = self.prepare_base_payload()
        payload.update(
            {
                "customId": self.name,
                "issuedAt": self.invoice_date.isoformat(),
                "dueDate": self.invoice_date_due.isoformat(),
                "name": self.name,
                "currency": self.currency_id.name,
                "grossAmount": self._format_upflow_amount(self.amount_total),
                "netAmount": self._format_upflow_amount(self.amount_untaxed),
                "customer": {
                    # "id": self.partner_id.commercial_partner_id.upflow_uuid,
                    "externalId": str(self.upflow_commercial_partner_id.id),
                },
            }
        )
        return payload

    def get_upflow_api_post_invoice_payload(self):
        """An upflow invoice match with account.move out_invoice odoo type"""
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise UserError(
                _(
                    "You try to get upflow invoice payload "
                    "on account entry %s with an other type %s "
                    "(expected out_invoice)"
                )
                % (
                    self.name,
                    self.move_type,
                )
            )
        return self._prepare_upflow_api_payload()

    def get_upflow_api_post_credit_note_payload(self):
        """An upflow credit note match with account.move out_refund odoo type"""
        self.ensure_one()
        if self.move_type != "out_refund":
            raise UserError(
                _(
                    "You try to get upflow refund payload "
                    "on account entry %s with an other type %s "
                    "(expected out_refund)"
                )
                % (
                    self.name,
                    self.move_type,
                )
            )
        return self._prepare_upflow_api_payload()

    def get_upflow_api_post_payment_payload(self):
        """An upflow payment refer to payment received from customer for invoices,
        in odoo it could be done in different ways:
        * account.payment
        * account.bank_statement.line
        * ...

        which in any case generate `entry` type account.move

        So we should not consider an `inbound` account.payment is necessarily present
        """
        self.ensure_one()
        data = self._prepare_upflow_payment_api_payload()
        if self.journal_id.upflow_bank_account_uuid:
            data["bankAccountId"] = self.journal_id.upflow_bank_account_uuid
        return data

    def get_upflow_api_post_refund_payload(self):
        """An upflow refund refer to payment send to customer for refunds,
        in odoo it could be done with different objects:
        * account.payment
        * account.bank_statement.line
        * ...

        Which in any case generate `entry` type account.move

        So we should not consider an `outbound` account.payment is necessarily present
        """
        self.ensure_one()
        return self._prepare_upflow_payment_api_payload()

    def _prepare_upflow_payment_api_payload(self):
        payload = self.prepare_base_payload()
        payload.update(
            {
                "currency": self.currency_id.name,
                "amount": self._format_upflow_amount(self.amount_total),
                "validatedAt": self.date.isoformat(),
                "customer": {
                    # "id": self.partner_id.commercial_partner_id.upflow_uuid,
                    "externalId": str(self.upflow_commercial_partner_id.id),
                },
            }
        )
        if self.payment_id:
            payload.update(self.payment_id._get_upflow_extra_payment_api_payload())
        return payload

    def get_upflow_api_pdf_payload(self):
        self.ensure_one()
        if self.move_type not in [
            "out_invoice",
            "out_refund",
        ]:
            raise UserError(
                _(
                    "You try to get upflow PDF payload "
                    "on account entry %s with an unexpected type %s "
                    "(expected out_invoice or out_refund)"
                )
                % (
                    self.name,
                    self.move_type,
                )
            )
        return {
            "data": self._get_b64_invoice_pdf(),
        }

    def _get_b64_invoice_pdf(self):
        report = self.env.ref("account.account_invoices_without_payment")
        pdf_content, _kind = report.sudo()._render_qweb_pdf(self.id)
        return base64.b64encode(pdf_content).decode()
