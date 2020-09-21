# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.addons.queue_job.job import job


class CreditControlCommunication(models.Model):

    _inherit = 'credit.control.communication'

    @job
    @api.model
    def _generate_emails_in_jobs(self, datas):
        comms = self.create(datas)
        comms._generate_emails()
