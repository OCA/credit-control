# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import api, models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.depends_context("inject_credit_control_communication_table")
    def _compute_body(self):
        res = super()._compute_body()
        if self.env.context.get("inject_credit_control_communication_table"):
            for composer in self:
                res_ids = composer._evaluate_res_ids()
                if composer.model and len(res_ids) == 1:
                    record = self.env[composer.model].browse(res_ids)
                    credit_control_communication = Markup(
                        record._get_credit_control_communication_table()
                    )
                    if composer.body:
                        composer.body += credit_control_communication
                    else:
                        composer.body = credit_control_communication
        return res
