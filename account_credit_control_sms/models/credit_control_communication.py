# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class CreditControlCommunication(models.Model):
    _inherit = "credit.control.communication"

    def _sms_get_partner_fields(self):
        return ["contact_address_id"]

    def get_sms_contact(self):
        """Return the contact to send the SMS to. If the contact address
        doesn't have a phone number we fallback to the commercial partner"""
        self.ensure_one()
        contact = self.contact_address_id
        if not (contact.mobile or contact.phone):
            contact = contact.commercial_partner_id
        return contact

    def _generate_sms(self):
        """Generate SMS using template related to level.

        SMS are queued and sent by the SMS cron, credit control lines states
        are updated once the SMS are processed (see sms.sms).
        """
        subtype_id = self.env.ref("account_credit_control.mt_request").id
        for comm in self:
            # Lines must be queued before posting, as the state of queued
            # lines is updated when the SMS is sent.
            comm.credit_control_line_ids.filtered(
                lambda line: line.state == "to_be_sent"
            ).write({"state": "queued"})
            comm._message_sms_with_template(
                template=comm.policy_level_id.sms_template_id,
                partner_ids=comm.get_sms_contact().ids,
                subtype_id=subtype_id,
                put_in_queue=True,
            )
