# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Property of commercial partner, applies for the whole entity
    no_overdue_reminder = fields.Boolean(
        string="Disable Overdue Invoice Reminder", company_dependent=True
    )
