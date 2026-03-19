# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _evaluate_purchase_risk(self, partner):
        """Return exception message if this bill exceeds the vendor risk limit."""
        self.ensure_one()
        if not partner.purchase_risk_limit or partner.purchase_risk_exception:
            return ""
        # The sum already includes draft bills (`purchase_risk_bill_draft`).
        # By the time of posting, if total risk exceeds limit, we can block it.
        if partner.purchase_risk > partner.purchase_risk_limit:
            return _("This document exceeds the vendor's purchase risk limit.\n")
        return ""

    def action_post(self):
        if not self.env.context.get("bypass_risk", False):
            for move in self.filtered(lambda m: m.move_type == "in_invoice"):
                partner = move.partner_id.commercial_partner_id
                exception_msg = move._evaluate_purchase_risk(partner)
                if exception_msg:
                    return (
                        self.env["purchase.risk.exception"]
                        .create(
                            {
                                "exception_msg": exception_msg,
                                "partner_id": partner.id,
                                "move_id": move.id,
                            }
                        )
                        .action_show()
                    )
        return super().action_post()
