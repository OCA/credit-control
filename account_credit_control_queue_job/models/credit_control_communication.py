# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.tools import split_every


class CreditControlCommunication(models.Model):
    _inherit = "credit.control.communication"

    def _send_mails(self):
        key = "account_credit_control_queue_job.batch_size"
        batch_size = self.env["ir.config_parameter"].sudo().get_param(key)
        try:
            batch_size = max(1, int(batch_size))
        except Exception:  # pylint: disable=broad-except
            batch_size = 1
        batch_name = _("Credit Control Emails")
        batch = self.env["queue.job.batch"].get_new_batch(batch_name)
        for comms in split_every(batch_size, self.ids, self.browse):
            if batch_size > 1:
                desc = _("Sending credit control emails for ids: %s") % comms.ids
            else:
                desc = _("Sending credit control email for %s") % comms.partner_id.name
            comms.with_context(job_batch=batch).with_delay(
                description=desc
            )._send_communications_by_email()
