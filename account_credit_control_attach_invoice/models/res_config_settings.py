from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    credit_control_report_to_attach_id = fields.Many2one(
        related="company_id.credit_control_report_to_attach_id",
        readonly=False,
    )
