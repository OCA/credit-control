from odoo.addons.base.tests.common import BaseCommon


class TestSaleFinancialRiskExcludeOrderType(BaseCommon):
    """
    Test suite for sale_financial_risk_exclude_order_type.
    Covers:
    - Blocking bypass behavior
    - Risk computation exclusion
    - Separation between blocking and computation
    - Domain integrity
    - Multi-company behavior
    - Sale order types without flags
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # ---------------------------------------------------------
        # Partner
        # ---------------------------------------------------------
        cls.risk_partner = cls.env["res.partner"].create(
            {
                "name": "Risk Customer",
                "customer_rank": 1,
                "credit_limit": 500.0,
                "risk_sale_order_include": True,
            }
        )
        # ---------------------------------------------------------
        # Sale Order Types
        # ---------------------------------------------------------
        cls.type_excluded = cls.env["sale.order.type"].create(
            {
                "name": "Excluded Type",
                "exclude_from_risk": True,
                "allow_blocking_bypass": True,
            }
        )
        cls.type_bypass_only = cls.env["sale.order.type"].create(
            {
                "name": "Bypass Only",
                "exclude_from_risk": False,
                "allow_blocking_bypass": True,
            }
        )
        cls.type_normal = cls.env["sale.order.type"].create(
            {
                "name": "Normal Type",
                "exclude_from_risk": False,
                "allow_blocking_bypass": False,
            }
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _create_sale_order(self, order_type=False):
        """
        Create a sale order using the provided sale order type.
        """
        vals = {
            "partner_id": self.risk_partner.id,
            "partner_invoice_id": self.risk_partner.id,
            "partner_shipping_id": self.risk_partner.id,
        }
        if order_type:
            vals["type_id"] = order_type.id
        return self.env["sale.order"].create(vals)

    # ---------------------------------------------------------
    # Blocking behavior
    # ---------------------------------------------------------
    def test_bypass_enabled(self):
        """
        Order types configured with allow_blocking_bypass
        must bypass financial risk blocking.
        """
        order = self._create_sale_order(self.type_excluded)
        self.assertTrue(order._allow_financial_risk_blocking_bypass())
        self.assertFalse(order.evaluate_risk_message(self.risk_partner))

    def test_bypass_only_type(self):
        """
        Order types configured only with blocking bypass:
        - must bypass blocking
        - must still contribute to risk computation
        """
        order = self._create_sale_order(self.type_bypass_only)
        self.assertTrue(order._allow_financial_risk_blocking_bypass())
        self.assertFalse(order.evaluate_risk_message(self.risk_partner))

    def test_no_bypass_for_normal_type(self):
        """
        Order types without bypass configuration
        must preserve standard behavior.
        """
        order = self._create_sale_order(self.type_normal)
        self.assertFalse(order._allow_financial_risk_blocking_bypass())

    def test_no_bypass_without_order_type(self):
        """
        Orders without type_id must not bypass risk blocking.
        """
        order = self._create_sale_order()
        self.assertFalse(order._allow_financial_risk_blocking_bypass())

    def test_bypass_disabled(self):
        """
        Order types without bypass enabled
        must not bypass blocking.
        """
        order_type = self.env["sale.order.type"].create(
            {
                "name": "No Bypass Type",
                "exclude_from_risk": True,
                "allow_blocking_bypass": False,
            }
        )
        order = self._create_sale_order(order_type)
        self.assertFalse(order._allow_financial_risk_blocking_bypass())

    # ---------------------------------------------------------
    # Risk computation domain
    # ---------------------------------------------------------
    def test_exclude_from_risk_domain(self):
        """
        Order types configured with exclude_from_risk=True
        must be excluded from the risk computation domain.
        """
        domain = self.risk_partner._get_risk_sale_order_domain()
        self.assertIn(
            ("order_id.type_id", "not in", self.type_excluded.ids),
            domain,
        )

    def test_bypass_only_does_not_affect_domain(self):
        """
        Blocking bypass alone must not affect
        risk computation domain.
        """
        domain = self.risk_partner._get_risk_sale_order_domain()
        self.assertNotIn(
            ("order_id.type_id", "not in", self.type_bypass_only.ids),
            domain,
        )

    def test_normal_type_does_not_affect_domain(self):
        """
        Neutral order types must not affect
        the risk computation domain.
        """
        domain = self.risk_partner._get_risk_sale_order_domain()
        self.assertNotIn(
            ("order_id.type_id", "not in", self.type_normal.ids),
            domain,
        )

    def test_domain_integrity(self):
        """
        The resulting domain must remain list-based.
        """
        domain = self.risk_partner._get_risk_sale_order_domain()
        self.assertIsInstance(domain, list)

    def test_exclusion_clause_present_once(self):
        """
        Exclusion clause must only appear once
        in the resulting domain.
        """
        domain = self.risk_partner._get_risk_sale_order_domain()
        clauses = [
            clause
            for clause in domain
            if clause
            == (
                "order_id.type_id",
                "not in",
                self.type_excluded.ids,
            )
        ]
        self.assertEqual(len(clauses), 1)

    # ---------------------------------------------------------
    # Separation of concerns
    # ---------------------------------------------------------
    def test_computation_and_blocking_are_independent(self):
        """
        Blocking bypass and risk computation exclusion
        must behave independently.
        """
        order = self._create_sale_order(self.type_bypass_only)
        # Blocking bypass enabled
        self.assertFalse(order.evaluate_risk_message(self.risk_partner))
        # Still included in computation
        domain = self.risk_partner._get_risk_sale_order_domain()
        self.assertNotIn(
            ("order_id.type_id", "not in", self.type_bypass_only.ids),
            domain,
        )

    def test_type_with_no_flags(self):
        """
        Order types without any enabled flags
        must not affect behavior.
        """
        order_type = self.env["sale.order.type"].create(
            {
                "name": "Neutral Type",
                "exclude_from_risk": False,
                "allow_blocking_bypass": False,
            }
        )
        order = self._create_sale_order(order_type)
        self.assertFalse(order._allow_financial_risk_blocking_bypass())
        domain = self.risk_partner._get_risk_sale_order_domain()
        self.assertNotIn(
            ("order_id.type_id", "not in", order_type.ids),
            domain,
        )

    # ---------------------------------------------------------
    # Multi-company behavior
    # ---------------------------------------------------------
    def test_company_specific_order_types(self):
        """
        Company-specific order types must remain isolated
        in their respective companies.
        """
        company_2 = self.env["res.company"].create(
            {
                "name": "Company 2",
            }
        )
        partner_2 = self.env["res.partner"].create(
            {
                "name": "Customer Company 2",
                "customer_rank": 1,
                "company_id": company_2.id,
            }
        )
        type_company_2 = self.env["sale.order.type"].create(
            {
                "name": "Company 2 Type",
                "company_id": company_2.id,
                "exclude_from_risk": True,
                "allow_blocking_bypass": True,
            }
        )
        order = (
            self.env["sale.order"]
            .with_company(company_2)
            .create(
                {
                    "partner_id": partner_2.id,
                    "partner_invoice_id": partner_2.id,
                    "partner_shipping_id": partner_2.id,
                    "company_id": company_2.id,
                    "type_id": type_company_2.id,
                }
            )
        )
        self.assertTrue(order._allow_financial_risk_blocking_bypass())
