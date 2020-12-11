# Copyright 2012-2017 Camptocamp SA
# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class Mail(models.Model):
    _inherit = "mail.mail"

    def _postprocess_sent_message(
        self, success_pids, failure_reason=False, failure_type=None
    ):
        """Mark credit control lines states."""
        for mail in self:
            msg = mail.mail_message_id
            if msg.model != "credit.control.communication":
                continue
            mt_request = self.env.ref("account_credit_control.mt_request")
            if mail.subtype_id == mt_request:
                lines = self.env["credit.control.line"].search(
                    [("communication_id", "=", msg.res_id), ("state", "=", "queued")]
                )
                new_state = "sent" if mail.state == "sent" else "email_error"
                lines.write({"state": new_state})
        return super()._postprocess_sent_message(
            success_pids=success_pids,
            failure_reason=failure_reason,
            failure_type=failure_type,
        )
