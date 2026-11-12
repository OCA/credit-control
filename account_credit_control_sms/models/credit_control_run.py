# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class CreditControlRun(models.Model):
    _inherit = "credit.control.run"

    def run_channel_action(self):
        # SMS must be handled before super, as it returns the printing action
        # for letter lines.
        self.ensure_one()
        sms_lines = self.line_ids._filter_sms_lines_to_send()
        if sms_lines:
            comm_obj = self.env["credit.control.communication"]
            comms = comm_obj._generate_comm_from_credit_lines(sms_lines)
            comms._generate_sms()
        return super().run_channel_action()
