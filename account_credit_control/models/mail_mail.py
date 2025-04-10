# Copyright 2012-2017 Camptocamp SA
# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class Mail(models.Model):
    _inherit = "mail.mail"

    def _update_control_line_status(self):
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

    def _postprocess_sent_message(
        self, success_pids, failure_reason=False, failure_type=None
    ):
        """Mark credit control lines states."""
        self._update_control_line_status()
        return super()._postprocess_sent_message(
            success_pids=success_pids,
            failure_reason=failure_reason,
            failure_type=failure_type,
        )

    def _send(
        self,
        auto_commit=False,
        raise_exception=False,
        smtp_session=None,
        alias_domain_id=False,
        mail_server=False,
        post_send_callback=None,
    ):
        # because of
        # https://github.com/odoo/odoo/blob/bcba6c0dda4818e67a9023beb26593a7d74ff6a6/
        # addons/mail/models/mail_mail.py#L606-L607
        # we don't go through _postprocess_sent_message if the address is blacklisted
        no_postprocess = self.filtered(lambda m: m.state != "outgoing")
        no_postprocess._update_control_line_status()
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
            alias_domain_id=alias_domain_id,
            mail_server=mail_server,
            post_send_callback=post_send_callback,
        )
