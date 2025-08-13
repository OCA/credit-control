from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    credit_control_report_to_attach_id = fields.Many2one(
        "ir.actions.report", string="Report to attach to credit control summary"
    )
