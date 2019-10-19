# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields


class CreditControlEmailer(models.TransientModel):

    _inherit = 'credit.control.emailer'

    run_in_jobs = fields.Boolean(
        default=True,
        help='Create and send emails in jobs',
    )

    @api.multi
    def _send_emails(self, group_size=50):
        self.ensure_one()
        if self.run_in_jobs:
            comm_obj = self.env['credit.control.communication']
            filtered_lines = self._filter_lines(self.line_ids)
            datas = comm_obj._aggregate_credit_lines(filtered_lines)
            filtered_lines.write({'state': 'sending'})
            offset = 0
            while offset <= len(datas):
                sub_datas = datas[offset:offset+group_size]
                comm_obj.with_delay()._generate_emails_in_jobs(sub_datas)
                offset += group_size
        else:
            super(CreditControlEmailer, self)._send_emails()
