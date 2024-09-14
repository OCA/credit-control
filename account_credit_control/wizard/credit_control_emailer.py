# Copyright 2012-2017 Camptocamp SA
# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CreditControlEmailer(models.TransientModel):
    """Send emails for each selected credit control lines."""

    _name = "credit.control.emailer"
    _description = """Mass credit line emailer"""
    _rec_name = "id"

    @api.model
    def _get_line_ids(self):
        context = self.env.context
        if context.get("active_model") != "credit.control.line" or not context.get(
            "active_ids"
        ):
            return False
        line_obj = self.env["credit.control.line"]
        lines = line_obj.browse(context["active_ids"])
        return self._filter_lines(lines)

    line_ids = fields.Many2many(
        comodel_name="credit.control.line",
        string="Credit Control Lines",
        default=lambda self: self._get_line_ids(),
        domain=[("state", "=", "to_be_sent"), ("channel", "=", "email")],
    )

    @api.model
    def _filter_lines(self, lines):
        """filter lines to use in the wizard"""
        line_obj = self.env["credit.control.line"]
        domain = [
            ("state", "=", "to_be_sent"),
            ("id", "in", lines.ids),
            ("channel", "=", "email"),
        ]
        return line_obj.search(domain)

    def _send_emails(self):
        self.ensure_one()
        comm_obj = self.env["credit.control.communication"]

        filtered_lines = self._filter_lines(self.line_ids)
        comms = comm_obj._generate_comm_from_credit_lines(filtered_lines)
        comms._generate_emails()
        return comms

    def email_lines(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No credit control lines selected."))

        communications = self._send_emails()
        if not communications:
            return {"type": "ir.actions.act_window_close"}
        action = self.sudo().env.ref(
            "account_credit_control.credit_control_communication_action"
        )
        action["name"] = _("Generated communications")
        action["domain"] = [("id", "in", communications.ids)]
        return action
