# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    dunning_block_active = fields.Boolean(
        string="Dunning Block",
        default=False,
        readonly=True,
        store=True,
        tracking=True,
        copy=False,
    )
    dunning_block_end_date = fields.Date(
        readonly=True, store=True, tracking=True, copy=False
    )
    dunning_block_note = fields.Text(
        readonly=True, store=True, tracking=True, copy=False
    )
    dunning_block_history_ids = fields.One2many(
        "dunning.block.history", "move_id", readonly=True, copy=False
    )
    dunning_block_days_left = fields.Integer(compute="_compute_dunning_block_days_left")
    dunning_block_reason_id = fields.Many2one(
        "dunning.block.reason", readonly=True, store=True, tracking=True, copy=False
    )

    @api.constrains("dunning_block_end_date")
    def _check_dunning_block_date_valid(self):
        for rec in self:
            if (
                rec.dunning_block_active
                and rec.dunning_block_end_date <= fields.Date.today()
            ):
                raise UserError(_("Dunning block end date must be later than today!"))

    def _compute_dunning_block_days_left(self):
        today = fields.Date.today()
        for rec in self:
            if rec.dunning_block_active and rec.dunning_block_end_date:
                rec.dunning_block_days_left = (rec.dunning_block_end_date - today).days
            else:
                rec.dunning_block_days_left = False

    def _cron_dunning_block_disable(self):
        moves = self.search(
            [
                ("dunning_block_active", "=", True),
                ("dunning_block_end_date", "<=", fields.Date.today()),
            ]
        )
        for move in moves:
            move._remove_dunning_block()
        _logger.info(
            f'Successfully finished dunning block for {moves if moves else "0"} entries'
        )

    def _remove_dunning_block(self):
        active_history_ids = self.dunning_block_history_ids.filtered(
            lambda x: x.dunning_block_active
        )
        vals = {
            "dunning_block_active": False,
            "dunning_block_end_date": False,
            "dunning_block_reason_id": False,
            "dunning_block_note": False,
        }
        if active_history_ids:
            lines = []
            history_vals = {
                "dunning_block_active": False,
                "dunning_block_end_date": datetime.date.today(),
                "status": "done",
            }
            for line in active_history_ids:
                lines.append((1, line.id, history_vals))
            vals["dunning_block_history_ids"] = lines
        self.write(vals)
        dates = (
            ", ".join([str(x.date()) for x in active_history_ids.mapped("create_date")])
            if active_history_ids
            else ""
        )
        self._message_log(
            body=_(
                "The <b>dunning block</b> was completed and deactivated"
                f" <b><i>({dates} - {datetime.date.today()})</i></b>"
            )
        )
