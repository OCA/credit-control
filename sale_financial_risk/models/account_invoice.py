# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        invoice, exception_msg = self._first_invoice_exception_msg()
        if (
            exception_msg
            and self.env.context.get("active_model", False)
            and self.env.context.get("active_model", False) == "sale.order"
        ):
            # Active active_model is not False if we come from the sales order invoices
            # button.
            return (
                self.env["partner.risk.exceeded.wiz"]
                .create(
                    {
                        "exception_msg": exception_msg,
                        "partner_id": invoice.partner_id.commercial_partner_id.id,
                        "origin_reference": "{},{}".format("account.move", invoice.id),
                        "continue_method": "action_post",
                    }
                )
                .action_show()
            )
        return super().action_post()
