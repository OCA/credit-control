# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.queue_job.job import job


class CreditControlLine(models.Model):

    _inherit = 'credit.control.line'

    state = fields.Selection(selection_add=[('sending', 'Sending')])

    @job
    @api.model
    def create_or_update_from_mv_lines(self, lines, level, controlling_date,
                                       run_id=None, check_tolerance=True):
        return super(CreditControlLine, self).create_or_update_from_mv_lines(
            lines,
            level,
            controlling_date,
            run_id,
            check_tolerance,
        )
