# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class SmsSms(models.Model):
    _inherit = "sms.sms"

    def _get_credit_control_communication_ids(self):
        """Return {sms id: credit control communication id} for SMS
        sent from credit control communications."""
        mt_request = self.env.ref("account_credit_control.mt_request")
        res = {}
        for sms in self.sudo():
            msg = sms.mail_message_id
            if (
                msg.model == "credit.control.communication"
                and msg.res_id
                and msg.subtype_id == mt_request
            ):
                res[sms.id] = msg.res_id
        return res

    def _postprocess_iap_sent_sms(
        self, iap_results, failure_reason=None, unlink_failed=False, unlink_sent=True
    ):
        # Compute before super as sms records may be unlinked
        sms_comm_ids = self.browse(
            [item["res_id"] for item in iap_results]
        )._get_credit_control_communication_ids()
        res = super()._postprocess_iap_sent_sms(
            iap_results,
            failure_reason=failure_reason,
            unlink_failed=unlink_failed,
            unlink_sent=unlink_sent,
        )
        if sms_comm_ids:
            sent_comm_ids, error_comm_ids = set(), set()
            for item in iap_results:
                comm_id = sms_comm_ids.get(item["res_id"])
                if not comm_id:
                    continue
                if item["state"] == "success":
                    sent_comm_ids.add(comm_id)
                else:
                    error_comm_ids.add(comm_id)
            line_obj = self.env["credit.control.line"].sudo()
            for comm_ids, new_state in (
                (sent_comm_ids, "sent"),
                (error_comm_ids, "sms_error"),
            ):
                if not comm_ids:
                    continue
                line_obj.search(
                    [
                        ("communication_id", "in", list(comm_ids)),
                        ("state", "=", "queued"),
                    ]
                ).write({"state": new_state})
        return res
