from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    report_to_attach_id = fields.Many2one(
        "ir.actions.report", string="Report to attach"
    )
