# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class DunningBlockHistory(models.Model):
    _name = "dunning.block.history"
    _description = "Dunning Block History"
    _order = "create_date desc"

    move_id = fields.Many2one("account.move", ondelete="cascade")
    dunning_block_active = fields.Boolean()
    dunning_block_end_date = fields.Date()
    dunning_block_reason_id = fields.Many2one("dunning.block.reason")
    dunning_block_note = fields.Text()
    status = fields.Selection(
        [
            ("active", "Active"),
            ("done", "Done"),
            ("interrupted", "Interrupted"),
        ],
        default="active",
        copy=False,
    )
