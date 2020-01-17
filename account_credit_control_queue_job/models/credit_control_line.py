# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class CreditControlLine(models.Model):

    _inherit = 'credit.control.line'

    state = fields.Selection(selection_add=[('sending', 'Sending')])
