from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _allow_financial_risk_blocking_bypass(self):
        """
        Return whether this order type is configured to bypass
        financial risk blocking.
        """
        self.ensure_one()
        return bool(self.type_id and self.type_id.allow_blocking_bypass)

    def evaluate_risk_message(self, partner):
        """
        Override the blocking decision from sale_financial_risk.
        If the order type is configured with 'Allow Risk Blocking Bypass',
        no blocking message is returned.
        Otherwise, preserve the standard behavior.
        """
        self.ensure_one()

        if self._allow_financial_risk_blocking_bypass():
            return False

        return super().evaluate_risk_message(partner)
