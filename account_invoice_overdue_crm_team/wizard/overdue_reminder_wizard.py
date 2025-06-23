# Copyright 2025 Akretion France (http://www.akretion.com/)
# @author: Mathieu Delva <mathieu.delva@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OverdueReminderStart(models.TransientModel):
    _inherit = "overdue.reminder.start"

    team_id = fields.Many2one("crm.team")

    def _prepare_base_domain(self):
        res = super()._prepare_base_domain()
        if self.team_id:
            res.append(("team_id", "=", self.team_id.id))
        return res
