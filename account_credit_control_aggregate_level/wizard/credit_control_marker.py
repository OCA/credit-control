# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class CreditControlMarker(models.TransientModel):
    _inherit = "credit.control.marker"

    @api.model
    def _filter_lines(self, lines):
        # Add lower related lines
        lines_and_related = lines.mapped(lambda line: line._get_lower_related_lines())
        return super()._filter_lines(lines_and_related)
