# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        res = super()._onchange_template_id(
            template_id=template_id,
            composition_mode=composition_mode,
            model=model,
            res_id=res_id,
        )
        if self.env.context.get("inject_credit_control_communication_table"):
            record = self.env[model].browse(res_id)
            res["value"]["body"] += Markup(
                record._get_credit_control_communication_table()
            )
        return res
