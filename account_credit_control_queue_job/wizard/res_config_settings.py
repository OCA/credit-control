# Copyright 2025 360ERP (https://360erp.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    credit_control_batch_size = fields.Integer(
        "Batch Size for Credit Control",
        default=1,
        config_parameter="account_credit_control_queue_job.batch_size",
    )
