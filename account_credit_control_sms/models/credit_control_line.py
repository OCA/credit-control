# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CreditControlLine(models.Model):
    _inherit = "credit.control.line"

    channel = fields.Selection(
        selection_add=[("sms", "SMS")],
        ondelete={"sms": lambda recs: recs.write({"channel": "letter"})},
    )
    state = fields.Selection(
        selection_add=[("sms_error", "SMS Error")],
        ondelete={"sms_error": lambda recs: recs.write({"state": "email_error"})},
    )

    @api.model
    def _prepare_from_move_line(
        self, move_line, level, controlling_date, open_amount, default_lines_vals
    ):
        data = super()._prepare_from_move_line(
            move_line, level, controlling_date, open_amount, default_lines_vals
        )
        partner = move_line.partner_id
        # Fallback to letter, as done for email channel
        if (
            data.get("channel") == "sms"
            and partner
            and not (partner.mobile or partner.phone)
        ):
            data["channel"] = "letter"
        return data

    def _filter_sms_lines_to_send(self):
        return self.filtered(
            lambda line: line.state == "to_be_sent" and line.channel == "sms"
        )

    def action_send_sms(self):
        lines = self._filter_sms_lines_to_send()
        if not lines:
            raise UserError(_("No credit control lines to send by SMS selected."))
        comms = self.env[
            "credit.control.communication"
        ]._generate_comm_from_credit_lines(lines)
        comms._generate_sms()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_credit_control.credit_control_communication_action"
        )
        action["name"] = _("Generated communications")
        action["domain"] = [("id", "in", comms.ids)]
        return action
