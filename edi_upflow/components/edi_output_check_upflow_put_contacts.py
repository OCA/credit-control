# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component


class EdiOutputCheckUpflowPutContacts(Component):
    _name = "edi.output.check.upflow_put_contacts"
    _inherit = "base.upflow.edi.output.check"
    _exchange_type = "upflow_put_contacts"

    def _check_and_process(self):
        self._upflow_check_and_process()
