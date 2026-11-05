# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class CreditControlRun(models.Model):
    _inherit = "credit.control.run"

    def run_channel_action(self):
        res = super().run_channel_action()
        target = self.env.user.partner_id
        msg = {
            "type": "info",
            "title": self.env._("Jobs enqueued"),
            "message": self.env._("The emails will be sent in the background"),
        }
        self.env["bus.bus"]._sendone(target, "simple_notification", msg)
        return res
