# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    overdue_invoice_count = fields.Integer(
        compute="_compute_overdue_invoice_count_amount",
        string="# of Overdue Invoices",
        compute_sudo=True,
    )
    # the currency_id field on res.partner =
    # partner.company_id.currency_id or self.env.user.company_id.currency_id
    overdue_invoice_amount = fields.Monetary(
        compute="_compute_overdue_invoice_count_amount",
        string="Overdue Invoices Residual",
        compute_sudo=True,
        help="Overdue invoice total residual amount in company currency.",
    )

    def _compute_overdue_invoice_count_amount(self):
        user_company_id = self.env.user.company_id.id
        for partner in self:
            company_id = partner.company_id.id or user_company_id
            (
                count,
                amount_company_currency,
            ) = partner._prepare_overdue_invoice_count_amount(company_id)
            partner.overdue_invoice_count = count
            partner.overdue_invoice_amount = amount_company_currency

    def _prepare_overdue_invoice_count_amount(self, company_id):
        # This method is also called by the module
        # account_invoice_overdue_warn_sale
        self.ensure_one()
        domain = self._prepare_overdue_invoice_domain(company_id)
        # amount_residual_signed is in company currency
        rg_res = self.env["account.invoice"].read_group(
            domain, ["residual_company_signed"], []
        )
        count = 0
        overdue_invoice_amount = 0.0
        if rg_res:
            count = rg_res[0]["__count"]
            overdue_invoice_amount = rg_res[0]["residual_company_signed"]
        return (count, overdue_invoice_amount)

    def _prepare_overdue_invoice_domain(self, company_id):
        # The use of commercial_partner_id is in this method
        self.ensure_one()
        today = fields.Date.context_today(self)
        if company_id is None:
            company_id = self.env.user.company_id.id
        domain = [
            ("type", "=", "out_invoice"),
            ("company_id", "=", company_id),
            ("commercial_partner_id", "=", self.commercial_partner_id.id),
            ("date_due", "<", today),
            ("state", "=", "open"),
        ]
        return domain

    def _prepare_jump_to_overdue_invoices(self, company_id):
        action = self.env['ir.actions.act_window'].for_xml_id(
            "account", "action_invoice_tree")
        action["domain"] = self._prepare_overdue_invoice_domain(company_id)
        action["context"] = {
            "journal_type": "sale",
            "type": "out_invoice",
            "default_type": "out_invoice",
            "default_partner_id": self.id,
        }
        return action

    def jump_to_overdue_invoices(self):
        self.ensure_one()
        company_id = self.company_id.id or self.env.user.company_id.id
        action = self._prepare_jump_to_overdue_invoices(company_id)
        return action
