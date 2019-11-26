# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class CreditControlPolicy(models.Model):

    _inherit = 'credit.control.policy'

    def _create_lines(
        self,
        level_lines,
        level,
        ccl_model,
        controlling_date,
        run_id,
        group_size=100,
    ):
        self.ensure_one()
        run = self.env["credit.control.run"].browse(run_id)
        if run.run_in_jobs:
            offset = 0
            while offset <= len(level_lines):
                sub_level_lines = level_lines.search(
                    [("id", "in", level_lines.ids)],
                    limit=group_size,
                    offset=offset,
                )
                ccl_model.with_delay().create_or_update_from_mv_lines(
                    sub_level_lines, level, controlling_date, run_id=run_id
                )
                offset += group_size
            return ccl_model
        else:
            return super(CreditControlPolicy, self)._create_lines(
                level_lines, level, ccl_model, controlling_date, run_id
            )
