# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import api, models
from odoo.tools.mail import is_html_empty


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.depends_context("inject_credit_control_communication_table")
    def _compute_body(self):
        bodies_before_super = {
            composer.id: composer.body
            for composer in self
            if not is_html_empty(composer.body)
        }
        res = super()._compute_body()
        if self.env.context.get("inject_credit_control_communication_table"):
            for composer in self:
                res_ids = composer._evaluate_res_ids()
                if composer.model and len(res_ids) == 1:
                    record = self.env[composer.model].browse(res_ids)
                    credit_control_communication = Markup(
                        record._get_credit_control_communication_table()
                    )
                    base_body = composer.body
                    if is_html_empty(base_body) and composer.id in bodies_before_super:
                        base_body = bodies_before_super[composer.id]

                    if not is_html_empty(base_body):
                        composer.body = base_body + credit_control_communication
                    else:
                        composer.body = credit_control_communication
        return res
