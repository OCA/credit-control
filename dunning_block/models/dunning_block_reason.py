# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class DunningBlockReason(models.Model):
    _name = "dunning.block.reason"
    _description = "Dunning Block Reason"

    name = fields.Char(required=True, translate=True)

    _sql_constraints = [
        ("dunning_block_reason_unique_name", "UNIQUE (name)", "Name must be unique!")
    ]
