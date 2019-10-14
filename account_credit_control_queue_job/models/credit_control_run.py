# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditControlRun(models.Model):

    _inherit = 'credit.control.run'

    run_in_jobs = fields.Boolean(
        help='The generation of credit control lines may take some time' 
             'to process, running it in jobs may be needed in case'
             'of high volumes.' 
    )

    def _create_lines(self, level_lines, level, ccl_model, group_size=100):
        if self.run_in_jobs:
            offset = 0
            while offset <= len(level_lines):
                sub_level_lines = level_lines.search(
                    [], limit=group_size, offset=offset
                )
                ccl_model.with_delay().create_or_update_from_mv_lines(
                    sub_level_lines, level, self.date, run_id=self.id
                )
                offset += group_size
            return ccl_model
        else:
            return super(CreditControlRun, self)._create_lines(
                self, level_lines, level, ccl_model
            )

    def _process_report(policy_lines_generated, policy
        if self.run_in_jobs:
            return ""
        else:
            return super(CreditControlRun, self)._process_report(
                policy_lines_generated, policy
            )
