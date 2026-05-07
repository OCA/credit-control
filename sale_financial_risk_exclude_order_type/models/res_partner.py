from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_risk_sale_order_domain(self):
        """
        Extend the domain used by sale_financial_risk to compute
        sale order exposure.
        Since the base computation runs on sale.order.line, the related
        field path used here is:
            order_id.type_id
        """
        domain = super()._get_risk_sale_order_domain()
        excluded_types = self.env["sale.order.type"].search(
            [
                ("exclude_from_risk", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ]
        )

        if excluded_types:
            domain += [("order_id.type_id", "not in", excluded_types.ids)]

        return domain
