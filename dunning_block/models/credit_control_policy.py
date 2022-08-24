# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class CreditControlPolicy(models.Model):
    _inherit = "credit.control.policy"

    def _get_move_lines_to_process(self, controlling_date):
        lines = super(CreditControlPolicy, self)._get_move_lines_to_process(
            controlling_date
        )
        lines = self._filter_out_dunning_block_lines(lines, controlling_date)
        return lines

    def _filter_out_dunning_block_lines(self, lines, controlling_date):
        """Filter out active dunning block lines taking into account
        that they might be ended at controlling date"""
        lines_to_remove = lines.filtered(
            lambda x: x.move_id.dunning_block_active
            and x.move_id.dunning_block_end_date > controlling_date.date
        )
        lines -= lines_to_remove
        return lines
