# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _

from odoo.addons.component.core import Component
from odoo.addons.queue_job.exception import RetryableJobError


class BaseUpflowEDIOutputGenerate(Component):
    _name = "base.upflow.edi.output.generate"
    _inherit = "edi.component.output.mixin"
    _usage = "output.generate"
    _backend_type = "upflow"

    _action = "generate"

    def generate(self):
        raise NotImplementedError(
            _(
                "You should implement generate method "
                "to create the payload or fix the exchange type. "
                "(Received exchange type code: %s)"
            )
            % self.exchange_record.type_id.code
        )

    def _wait_related_exchange_to_be_sent_and_processed(self):
        # while moving this to edi_oca
        # https://github.com/OCA/edi/issues/782
        # consider to gives a way to make list of states configurable
        # I belives in some case we wan't to generate the event event
        # depends one is in error but manually fix it (an other way)
        # in the mean time is to remove the dependence to force the event
        if not all(
            self.exchange_record.dependent_exchange_ids.mapped(
                lambda rel_exch: rel_exch.edi_exchange_state
                == "output_sent_and_processed"
            )
        ):
            raise RetryableJobError(
                "Waiting related exchanges to be done before generate...",
            )
