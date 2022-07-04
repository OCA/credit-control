# Copyright 2019 ACSONE SA/NV
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, tools


class AccountCreditControlAnalysis(models.Model):
    _name = "credit.control.analysis"
    _description = "Credit Control Analysis"
    _auto = False
    _rec_name = "partner_id"

    partner_id = fields.Many2one(comodel_name="res.partner", readonly=True)
    partner_ref = fields.Char(readonly=True)
    policy_id = fields.Many2one(comodel_name="credit.control.policy", readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", readonly=True)
    policy_level_id = fields.Many2one(
        comodel_name="credit.control.policy.level",
        string="Overdue Level",
        readonly=True,
    )
    level = fields.Integer(string="Max Level", readonly=True)
    open_balance = fields.Float(
        string="Overdue Balance",
        readonly=True,
        help="Open balance on credit control lines"
        "of same partner, policy and currency",
    )
    company_id = fields.Many2one(comodel_name="res.company", readonly=True)

    def _distinct_fields(self):
        return """
            partner.id, ccl.policy_id, ccl.currency_id
            """

    def _fields_to_select(self):
        return """
            ccl.id                                   AS id,
            partner.id                               AS partner_id,
            partner.ref                              AS partner_ref,
            ccl.policy_id                            AS policy_id,
            ccl.currency_id                          AS currency_id,
            ccl.policy_level_id                      AS policy_level_id,
            ccl.company_id                           AS company_id,
            ccpl.level                               AS level,
            (SELECT sum(amount_residual)
                FROM account_move_line AS aml
                WHERE NOT aml.reconciled
                AND aml.id IN
                    (SELECT move_line_id
                    FROM credit_control_line AS ccl2
                    WHERE ccl2.commercial_partner_id=partner.id
                        AND ccl2.policy_id=ccl.policy_id
                        AND (
                            (ccl.currency_id IS NULL
                            AND ccl2.currency_id IS NULL)
                        OR ccl2.currency_id=ccl.currency_id
                        )
                    )
                ) AS open_balance
            """

    def _from_tables(self):
        return """
            FROM credit_control_line AS ccl
            LEFT JOIN credit_control_policy_level AS ccpl
            ON ccpl.id=ccl.policy_level_id
            INNER JOIN account_move_line AS aml
            ON aml.id=ccl.move_line_id AND NOT aml.reconciled
            LEFT JOIN res_partner AS partner
            ON partner.id=ccl.commercial_partner_id
            """

    def _order_by(self):
        return """
            partner.id, ccl.policy_id, ccl.currency_id, ccpl.level DESC, ccl.id
            """

    def _get_sql_query(self):
        return """
            CREATE VIEW credit_control_analysis
            AS
            (SELECT DISTINCT ON ({}) {}
            {}
            ORDER BY {})
            """.format(
            self._distinct_fields(),
            self._fields_to_select(),
            self._from_tables(),
            self._order_by(),
        )

    def init(self):
        tools.drop_view_if_exists(self._cr, "credit_control_analysis")
        query = self._get_sql_query()
        self._cr.execute(query)
