# Copyright 2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2024 Engenere.one
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
    # partner.company_id.currency_id or self.env.company.cueency_id
    overdue_invoice_amount = fields.Monetary(
        compute="_compute_overdue_invoice_count_amount",
        string="Overdue Invoices Residual",
        compute_sudo=True,
        help="Overdue invoice total residual amount in company currency.",
    )

    def _compute_overdue_invoice_count_amount(self):
        for partner in self:
            company_id = partner.company_id.id or partner.env.company.id
            (
                count,
                amount_company_currency,
            ) = partner._prepare_overdue_invoice_count_amount(company_id)
            partner.overdue_invoice_count = count
            partner.overdue_invoice_amount = amount_company_currency

    def _get_overdue_move_lines(self, company_id):
        domain = self._prepare_overdue_move_lines_domain(company_id)
        overdue_move_lines = self.env["account.move.line"].search(domain)
        return overdue_move_lines

    def _prepare_overdue_invoice_count_amount(self, company_id):
        # This method is also called by the module
        # account_invoice_overdue_warn_sale where the company_id arg is used
        self.ensure_one()
        # amount_residual is in company currency
        overdue_move_lines = self._get_overdue_move_lines(company_id)
        overdue_invoice_amount = self._compute_overdue_move_lines_total(
            overdue_move_lines
        )
        count = self._count_unique_invoices(overdue_move_lines)
        return (count, overdue_invoice_amount)

    def _prepare_overdue_move_lines_domain(self, company_id):
        # The use of commercial_partner_id is in this method
        self.ensure_one()
        today = fields.Date.context_today(self)
        if company_id is None:
            company_id = self.env.company.id
        domain = [
            ("move_id.company_id", "=", company_id),
            ("move_id.commercial_partner_id", "=", self.commercial_partner_id.id),
            ("date_maturity", "<", today),
            ("move_id.state", "=", "posted"),
            ("reconciled", "=", False),
            ("account_internal_type", "=", "receivable"),
        ]
        return domain

    def _compute_overdue_move_lines_total(self, overdue_move_lines):
        return sum(overdue_move_lines.mapped("amount_residual"))

    def _get_unique_invoices_id_list(self, overdue_move_lines):
        return overdue_move_lines.mapped("move_id").ids

    def _count_unique_invoices(self, overdue_move_lines):
        unique_invoices = self._get_unique_invoices_id_list(overdue_move_lines)
        return len(unique_invoices)

    def _prepare_invoice_domain(self, invoice_ids):
        return [("id", "in", invoice_ids)]

    def _prepare_jump_to_overdue_invoices(self, company_id):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        overdue_move_lines = self._get_overdue_move_lines(company_id)
        unique_invoice_ids = self._get_unique_invoices_id_list(overdue_move_lines)
        action["domain"] = self._prepare_invoice_domain(unique_invoice_ids)
        action["context"] = {
            "journal_type": "sale",
            "move_type": "out_invoice",
            "default_move_type": "out_invoice",
            "default_partner_id": self.id,
        }
        return action

    def jump_to_overdue_invoices(self):
        self.ensure_one()
        company_id = self.company_id.id or self.env.company.id
        action = self._prepare_jump_to_overdue_invoices(company_id)
        return action
