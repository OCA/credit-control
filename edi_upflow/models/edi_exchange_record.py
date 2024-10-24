# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class EDIExchangeRecord(models.Model):

    _inherit = "edi.exchange.record"

    # TODO: considering to move that in edi_oca:
    # https://github.com/OCA/edi/issues/782
    dependent_exchange_ids = fields.Many2many(
        comodel_name="edi.exchange.record",
        relation="edi_exchange_record_dependent_rel",
        column1="exchange_id",
        column2="dependent_exchange_id",
        string="Depends on",
        help="Following exchanges have to be processed before be able to run the current one.",
    )
