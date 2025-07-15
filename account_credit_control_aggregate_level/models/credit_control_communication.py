# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class CreditControlCommunication(models.Model):
    _inherit = "credit.control.communication"

    @api.model
    def _get_credit_lines(
        self, line_ids, partner_id, level_id, currency_id, company_id
    ):
        # Handle case when no policy_level is provided.
        if level_id:
            return super()._get_credit_lines(
                line_ids, partner_id, level_id, currency_id, company_id
            )
        cr_line_obj = self.env["credit.control.line"]
        domain = [
            ("id", "in", line_ids),
            ("partner_id", "=", partner_id),
            ("currency_id", "=", currency_id),
            ("company_id", "=", company_id),
        ]
        return cr_line_obj.search(domain, order="level DESC")

    @api.model
    def _sql_credit_lines_groups(self):
        # Remove level when aggregation is enabled on policy
        # returns NULL instead of an ID for the level
        return (
            "SELECT DISTINCT"
            " partner_id,"
            " CASE"
            "   WHEN policy.aggregate_levels"
            "    THEN NULL"
            "    ELSE policy_level.id"
            "   END AS policy_level_id,"
            " line.currency_id,"
            " line.company_id"
            " FROM credit_control_line AS line"
            " JOIN credit_control_policy_level as policy_level"
            "   ON (line.policy_level_id = policy_level.id)"
            " JOIN credit_control_policy as policy"
            "   ON (policy_level.policy_id = policy.id)"
            " WHERE line.id in %s"
        )

    @api.model
    def _prepare_communication_data(self, cr_lines):
        # Redefine policy_level to ensure it's the highest
        res = super()._prepare_communication_data(cr_lines)
        highest_policy_lvl = cr_lines.mapped("policy_level_id").sorted("level")[0]
        res["policy_level_id"] = highest_policy_lvl.id
        return res
