# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditControlRun(models.Model):

    _inherit = 'credit.control.run'

    run_in_jobs = fields.Boolean(
        help='The generation of credit control lines may take some time'
             'to process, running it in jobs may be needed in case'
             'of high volumes.',
    )
