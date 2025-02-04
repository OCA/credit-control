from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    report_to_attach_id = fields.Many2one(
        related="company_id.report_to_attach_id",
        string="Report to attach",
        readonly=False,
        config_parameter="qr_report_id",
    )
