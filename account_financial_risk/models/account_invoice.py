# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    risk_currency_id = fields.Many2one(related="partner_id.risk_currency_id")
    risk_amount_total_currency = fields.Monetary(
        string="Risk Amount Total",
        currency_field="risk_currency_id",
        compute="_compute_risk_amount_total_currency",
    )

    @api.depends(
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
        "partner_id.credit_currency",
        "partner_id.manual_credit_currency_id",
        "partner_id.property_account_receivable_id.currency_id",
        "partner_id.country_id",
        "company_currency_id",
    )
    def _compute_risk_amount_total_currency(self):
        for invoice in self:
            invoice.risk_amount_total_currency = invoice.company_currency_id._convert(
                invoice.amount_total_signed,
                invoice.risk_currency_id,
                invoice.company_id,
                invoice.invoice_date or fields.Date.context_today(self),
                round=False,
            )

    def risk_exception_msg(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        exception_msg = ""
        if partner.risk_exception:
            exception_msg = _("Financial risk exceeded.\n")
        elif partner.risk_invoice_open_limit and (
            (partner.risk_invoice_open + self.risk_amount_total_currency)
            > partner.risk_invoice_open_limit
        ):
            exception_msg = _("This invoice exceeds the open invoices risk.\n")
        # If risk_invoice_draft_include this invoice included in risk_total
        elif not partner.risk_invoice_draft_include and (
            partner.risk_invoice_open_include
            and (partner.risk_total + self.risk_amount_total_currency)
            > partner.credit_limit
        ):
            exception_msg = _("This invoice exceeds the financial risk.\n")
        return exception_msg

    def _first_invoice_exception_msg(self):
        """
        Method used to return the first invoice with exception message.
        """
        ret = False, False
        if self.env.context.get("bypass_risk", False):
            return ret
        for invoice in self.filtered(
            lambda x: x.move_type == "out_invoice"
            and not x.company_id.allow_overrisk_invoice_validation
        ):
            exception_msg = invoice.risk_exception_msg()
            if exception_msg:
                ret = invoice, exception_msg
                break
        return ret

    def _post(self, soft=True):
        invoice, exception_msg = self._first_invoice_exception_msg()
        if exception_msg and self.env.context.get("from_validate_move_wiz", False):
            raise ValidationError(
                _(
                    "The partner %s is in risk exception.\n"
                    "You must post his invoices from form view to allow over risk"
                )
                % invoice.partner_id.commercial_partner_id.display_name
            )
        return super()._post(soft)

    def action_post(self):
        invoice, exception_msg = self._first_invoice_exception_msg()
        if exception_msg and not self.env.context.get("from_validate_move_wiz", False):
            return (
                self.env["partner.risk.exceeded.wiz"]
                .create(
                    {
                        "exception_msg": exception_msg,
                        "partner_id": invoice.partner_id.commercial_partner_id.id,
                        "origin_reference": "{},{}".format("account.move", invoice.id),
                        "continue_method": "action_post",
                    }
                )
                .action_show()
            )
        return super().action_post()
