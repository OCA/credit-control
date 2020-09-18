# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def message_format(self):
        result = super().message_format()
        credit_control = self.env['ir.model.data'].xmlid_to_res_id(
            'account_credit_control.mt_request'
        )
        for message in result:
            message.update({
                'is_discussion': message['is_discussion'] or (
                    message['subtype_id'] and
                    message['subtype_id'][0] == credit_control
                )
            })
        return result
