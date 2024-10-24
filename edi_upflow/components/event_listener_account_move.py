# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class AccountMoveUpflowEventListener(Component):
    """Intent of this class is to listen interesting account.move events

    used to create usefull exchange record for followup external system
    with upflow.io in mind (not sure it can be as generic)
    """

    _name = "account.move.upflow.event.listener"
    _inherit = "base.upflow.event.listener"
    _apply_on = ["account.move"]

    def on_post_account_move(self, moves):
        self.send_moves_to_upflow(moves)
