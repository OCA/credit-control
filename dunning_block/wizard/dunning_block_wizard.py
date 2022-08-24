# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo import _, api, fields, models


class DunningBlockWizard(models.TransientModel):
    _name = "dunning.block.wizard"
    _description = "Dunning block Wizard"

    is_dunning_block_active = fields.Boolean()
    dunning_block_end_date = fields.Date(required=True)
    dunning_block_reason_id = fields.Many2one("dunning.block.reason", required=True)
    dunning_block_note = fields.Text(required=True)

    @api.model
    def default_get(self, fields):
        res = super(DunningBlockWizard, self).default_get(fields)
        move = self._get_active_invoice()
        if move.dunning_block_active:
            res["is_dunning_block_active"] = True
            res["dunning_block_end_date"] = move.dunning_block_end_date
            res["dunning_block_reason_id"] = move.dunning_block_reason_id.id
            res["dunning_block_note"] = move.dunning_block_note
        return res

    def _get_active_invoice(self):
        return self.env["account.move"].browse(self._context.get("active_id"))

    def set_dunning_block_action(self):
        self._update_dunning_block()

    def remove_dunning_block_action(self):
        self._update_dunning_block(no_remove=False)

    def _update_dunning_block(self, no_remove=True):
        move = self._get_active_invoice()
        vals = {
            "dunning_block_active": True if no_remove else False,
            "dunning_block_end_date": self.dunning_block_end_date
            if no_remove
            else False,
            "dunning_block_reason_id": self.dunning_block_reason_id.id
            if no_remove
            else False,
            "dunning_block_note": self.dunning_block_note if no_remove else False,
        }
        move.write(vals)
        self._dunning_block_history(move, vals, no_remove)

    def _dunning_block_history(self, move, vals, no_remove):
        if not self.is_dunning_block_active:
            self._start_dunning_block_history(move, vals)
        else:
            self._update_or_stop_dunning_block_history(move, vals, no_remove)

    def _start_dunning_block_history(self, move, vals):
        move.write({"dunning_block_history_ids": [(0, 0, vals)]})

    def _update_or_stop_dunning_block_history(self, move, vals, no_remove):
        dunning_block_history_id = move.dunning_block_history_ids.filtered(
            lambda x: x.dunning_block_active
        ).id
        if not no_remove:
            self._stop_dunning_block_history(move, dunning_block_history_id)
        else:
            self._update_dunning_block_history(move, vals, dunning_block_history_id)

    def _stop_dunning_block_history(self, move, dunning_block_history_id):
        vals = {
            "dunning_block_active": False,
            "dunning_block_end_date": datetime.date.today(),
            "status": "interrupted",
        }
        move.write({"dunning_block_history_ids": [(1, dunning_block_history_id, vals)]})
        self._log_message_when_removed(move)

    def _log_message_when_removed(self, move):
        move._message_log(
            body=_(
                "Dunning block was interrupted and canceled by "
                f"<u>{self.env.user.name}</u>"
            )
        )

    def _update_dunning_block_history(self, move, vals, dunning_block_history_id):
        move.write({"dunning_block_history_ids": [(1, dunning_block_history_id, vals)]})
