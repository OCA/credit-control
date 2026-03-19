# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import Form, TransactionCase, new_test_user, tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("post_install", "-at_install")
class TestPurchaseFinancialRisk(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.env.user.groups_id |= cls.env.ref(
            "purchase_financial_risk.group_purchase_risk_manager"
        )
        cls.env.user.groups_id |= cls.env.ref("purchase.group_purchase_manager")
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Test Vendor",
                "supplier_rank": 1,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "purchase_ok": True,
                "standard_price": 100.0,
            }
        )
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.account_purchase = cls.env["account.account"].create(
            {
                "name": "Purchase",
                "code": "XX600",
                "account_type": "expense",
            }
        )
        cls.journal_purchase = cls.env["account.journal"].create(
            {
                "name": "Test Vendor Bills",
                "type": "purchase",
                "code": "TPUR",
                "company_id": cls.env.company.id,
            }
        )
        # Activate secondary currencies for multi-currency tests
        (cls.env.ref("base.USD") | cls.env.ref("base.EUR")).active = True
        cls.company_currency = cls.env.company.currency_id
        cls.usd = cls.env.ref("base.USD")
        cls.eur = cls.env.ref("base.EUR")
        # Pick a risk currency different from the company currency
        cls.alt_currency = cls.eur if cls.company_currency == cls.usd else cls.usd

    def _create_purchase_order(self, vendor, price_unit=100.0, qty=1.0):
        return self.env["purchase.order"].create(
            {
                "partner_id": vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_qty": qty,
                            "product_uom": self.uom_unit.id,
                            "price_unit": price_unit,
                            "taxes_id": [],
                            "date_planned": "2026-01-01",
                        },
                    )
                ],
            }
        )

    def _create_vendor_bill(self, vendor, amount=100.0, post=False):
        bill = self.env["account.move"].create(
            {
                "partner_id": vendor.id,
                "move_type": "in_invoice",
                "invoice_date": "2026-01-01",
                "journal_id": self.journal_purchase.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test service",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.account_purchase.id,
                        },
                    )
                ],
            }
        )
        if post:
            bill.action_post()
        return bill

    def test_partner_purchase_risk_no_limit(self):
        """Vendor with risk_limit=0 confirms PO without any block."""
        self.vendor.purchase_risk_limit = 0.0
        order = self._create_purchase_order(self.vendor, price_unit=500.0)
        result = order.button_confirm()
        self.assertTrue(result)
        self.assertEqual(order.state, "purchase")

    def test_purchase_risk_computed_from_po(self):
        """Confirmed PO increases vendor purchase_risk correctly."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor PO Risk", "supplier_rank": 1}
        )
        order = self._create_purchase_order(vendor, price_unit=200.0, qty=1.0)
        order.button_confirm()
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_po"])
        self.assertAlmostEqual(vendor.purchase_risk, 200.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_po, 200.0, places=2)

    def test_purchase_risk_computed_from_bill(self):
        """Unpaid vendor bill increases vendor purchase_risk."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Bill Risk", "supplier_rank": 1}
        )
        self._create_vendor_bill(vendor, amount=150.0, post=True)
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_bill_open"])
        self.assertAlmostEqual(vendor.purchase_risk, 150.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_bill_open, 150.0, places=2)

    def test_purchase_risk_computed_from_draft_bill(self):
        """Draft vendor bill increases vendor purchase_risk."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Draft Bill Risk", "supplier_rank": 1}
        )
        self._create_vendor_bill(vendor, amount=120.0, post=False)
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_bill_draft"])
        self.assertAlmostEqual(vendor.purchase_risk, 120.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_bill_draft, 120.0, places=2)

    def test_purchase_risk_paid_bill_excluded(self):
        """Paid vendor bill is NOT counted in purchase_risk."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Paid Bill", "supplier_rank": 1}
        )
        bill = self._create_vendor_bill(vendor, amount=100.0, post=True)
        # Register payment to fully pay the bill
        journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.env.company.id)], limit=1
        )
        if not journal:
            journal = self.env["account.journal"].create(
                {
                    "name": "Test Bank",
                    "type": "bank",
                    "code": "TBNK",
                    "company_id": self.env.company.id,
                }
            )
        bill.action_register_payment()
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create({"journal_id": journal.id})
        )
        payment.action_create_payments()
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_bill_open"])
        self.assertAlmostEqual(vendor.purchase_risk, 0.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_bill_open, 0.0, places=2)

    def test_purchase_order_blocked_on_confirm(self):
        """PO confirmation returns wizard when risk > limit."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Blocked", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 100.0
        order = self._create_purchase_order(vendor, price_unit=200.0)
        result = order.button_confirm()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("res_model"), "purchase.risk.exception")
        # Order should remain in draft
        self.assertEqual(order.state, "draft")

    def test_purchase_order_exception_bypasses_block(self):
        """With purchase_risk_exception=True on partner, PO confirms even over limit."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Exception", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 100.0
        vendor.purchase_risk_exception = True
        order = self._create_purchase_order(vendor, price_unit=200.0)
        result = order.button_confirm()
        self.assertTrue(result)
        self.assertEqual(order.state, "purchase")

    def test_vendor_bill_blocked_on_post(self):
        """Vendor bill posting returns wizard when risk > limit."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Bill Blocked", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 100.0
        bill = self._create_vendor_bill(vendor, amount=200.0, post=False)
        result = bill.action_post()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("res_model"), "purchase.risk.exception")
        # Bill should remain in draft
        self.assertEqual(bill.state, "draft")

    def test_vendor_bill_exception_bypasses_block(self):
        """With purchase_risk_exception=True on partner, Bill posts even over limit."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Bill Exception", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 100.0
        vendor.purchase_risk_exception = True
        bill = self._create_vendor_bill(vendor, amount=200.0, post=False)
        result = bill.action_post()
        self.assertTrue(result or bill.state == "posted")
        self.assertEqual(bill.state, "posted")

    def test_risk_manager_can_force_confirm(self):
        """User in group_purchase_risk_manager can confirm via the wizard."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Force Confirm", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 50.0
        order = self._create_purchase_order(vendor, price_unit=200.0)
        result = order.button_confirm()
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("res_model"), "purchase.risk.exception")
        # Risk manager confirms via wizard
        risk_manager = new_test_user(
            self.env,
            login="test-purchase-risk-manager",
            groups=(
                "base.group_user,"
                "purchase.group_purchase_user,"
                "purchase_financial_risk.group_purchase_risk_manager"
            ),
        )
        wizard = self.env["purchase.risk.exception"].browse(result["res_id"])
        wizard.with_user(risk_manager).button_confirm()
        self.assertEqual(order.state, "purchase")

    def test_risk_manager_can_force_post_bill(self):
        """User in group_purchase_risk_manager can post bill via the wizard."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Force Post", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 100.0
        bill = self._create_vendor_bill(vendor, amount=200.0, post=False)
        # Create a risk manager user for this test
        self.risk_manager = new_test_user(
            self.env,
            login="test-purchase-risk-manager-bill",
            groups=(
                "base.group_user,"
                "purchase.group_purchase_user,"
                "account.group_account_invoice,"
                "purchase_financial_risk.group_purchase_risk_manager"
            ),
        )
        wizard_action = bill.with_user(self.risk_manager).action_post()
        wizard_id = wizard_action.get("res_id")
        wizard = self.env["purchase.risk.exception"].browse(wizard_id)
        # Confirming through wizard posts the bill
        wizard.with_user(self.risk_manager).button_confirm()
        self.assertEqual(bill.state, "posted")

    def test_purchase_risk_percent_calculation(self):
        """purchase_risk_percent is computed correctly."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Percent", "supplier_rank": 1}
        )
        vendor.purchase_risk_limit = 200.0
        # Create a confirmed PO worth 50
        order = self._create_purchase_order(vendor, price_unit=50.0, qty=1.0)
        order.button_confirm()
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_percent"])
        self.assertAlmostEqual(vendor.purchase_risk, 50.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_percent, 25.0, places=2)

    def _create_currency_rate(self, currency, rate_per_company_unit):
        """Set exchange rate: 1 company_currency = rate_per_company_unit alt_currency.

        In Odoo, res.currency.rate.rate stores units of the currency per 1 unit of the
        company currency. So rate=0.05 for USD in an MXN company means 1 MXN = 0.05 USD
        (i.e. 1 USD = 20 MXN).
        """
        self.env["res.currency.rate"].search(
            [
                ("currency_id", "=", currency.id),
                ("company_id", "=", self.env.company.id),
            ]
        ).unlink()
        self.env["res.currency.rate"].create(
            {
                "currency_id": currency.id,
                "name": fields.Date.today(),
                "rate": rate_per_company_unit,
                "company_id": self.env.company.id,
            }
        )

    def test_purchase_risk_currency_po_conversion(self):
        """PO in company currency is converted to a different vendor risk currency."""
        # 1 alt_currency = 20 company_currency  →  rate stored = 1/20 = 0.05
        self._create_currency_rate(self.alt_currency, 1.0 / 20.0)
        vendor = self.env["res.partner"].create(
            {"name": "Vendor FX PO", "supplier_rank": 1}
        )
        vendor.purchase_risk_currency_id = self.alt_currency
        # Limit: 100 in alt_currency
        vendor.purchase_risk_limit = 100.0
        # PO in company currency for 1000 → equals 50 alt_currency (1000 × 0.05)
        order = self._create_purchase_order(vendor, price_unit=1000.0)
        # Should confirm without blocking (50 < 100)
        result = order.button_confirm()
        self.assertEqual(order.state, "purchase")
        self.assertTrue(result)
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_po"])
        self.assertAlmostEqual(vendor.purchase_risk, 50.0, places=1)
        self.assertAlmostEqual(vendor.purchase_risk_po, 50.0, places=1)

    def test_purchase_risk_currency_bill_conversion(self):
        """Vendor bill residual is converted to the vendor's risk currency."""
        # 1 alt_currency = 20 company_currency  →  rate stored = 1/20 = 0.05
        self._create_currency_rate(self.alt_currency, 1.0 / 20.0)
        vendor = self.env["res.partner"].create(
            {"name": "Vendor FX Bill", "supplier_rank": 1}
        )
        vendor.purchase_risk_currency_id = self.alt_currency
        # Bill in company currency for 1500 → equals 75 alt_currency (1500 × 0.05)
        self._create_vendor_bill(vendor, amount=1500.0, post=True)
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_bill_open"])
        self.assertAlmostEqual(vendor.purchase_risk, 75.0, places=1)
        self.assertAlmostEqual(vendor.purchase_risk_bill_open, 75.0, places=1)

    def test_purchase_risk_percent_after_currency_conversion(self):
        """purchase_risk_percent is correct after currency conversion."""
        # 1 alt_currency = 20 company_currency  →  rate stored = 1/20 = 0.05
        self._create_currency_rate(self.alt_currency, 1.0 / 20.0)
        vendor = self.env["res.partner"].create(
            {"name": "Vendor FX Percent", "supplier_rank": 1}
        )
        vendor.purchase_risk_currency_id = self.alt_currency
        # Limit: 200 in alt_currency
        vendor.purchase_risk_limit = 200.0
        # PO in company currency for 1000 → equals 50 alt_currency (1000 × 0.05)
        order = self._create_purchase_order(vendor, price_unit=1000.0)
        order.button_confirm()
        vendor.invalidate_recordset(["purchase_risk", "purchase_risk_percent"])
        # purchase_risk = 50 alt_currency, limit = 200 → 25%
        self.assertAlmostEqual(vendor.purchase_risk, 50.0, places=1)
        self.assertAlmostEqual(vendor.purchase_risk_percent, 25.0, places=1)

    def test_open_purchase_risk_pivot_info(self):
        """Clicking on a risk amount opens the pivot view."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Pivot Click", "supplier_rank": 1}
        )
        self._create_vendor_bill(vendor, amount=100.0, post=True)
        # Check that it returns an action for open bills
        action = vendor.with_context(
            open_risk_field="purchase_risk_bill_open"
        ).open_purchase_risk_pivot_info()
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["view_mode"], "pivot")

        # Check that it returns an action for open POs
        action_po = vendor.with_context(
            open_risk_field="purchase_risk_po"
        ).open_purchase_risk_pivot_info()
        self.assertEqual(action_po["res_model"], "purchase.order.line")
        self.assertEqual(action_po["view_mode"], "pivot")

    def test_draft_bill_moves_to_open_on_post(self):
        """Confirming a draft bill moves risk from bill_draft to bill_open.

        Regression test: the @api.depends must include move_line_ids.parent_state
        so that the ORM recomputes when invoice state changes draft→posted.
        """
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Draft To Open", "supplier_rank": 1}
        )
        bill = self._create_vendor_bill(vendor, amount=300.0, post=False)
        # Draft bill must be counted in bill_draft, not bill_open
        self.assertAlmostEqual(vendor.purchase_risk_bill_draft, 300.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_bill_open, 0.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk, 300.0, places=2)
        # Post the bill — no manual invalidate_recordset should be needed
        bill.with_context(bypass_risk=True).action_post()
        self.assertEqual(bill.state, "posted")
        # Risk must have migrated automatically to bill_open
        self.assertAlmostEqual(vendor.purchase_risk_bill_draft, 0.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk_bill_open, 300.0, places=2)
        self.assertAlmostEqual(vendor.purchase_risk, 300.0, places=2)

    def test_purchase_risk_onchange_form(self):
        """Test onchange behavior to avoid KeyError on NewId records."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Form Risk", "supplier_rank": 1}
        )
        self._create_vendor_bill(vendor, amount=150.0, post=True)
        # We use Form to simulate UI onchange where record is passed as NewId
        with Form(vendor) as vendor_form:
            vendor_form.purchase_risk_limit = 500.0
            # Reading the fields should trigger the compute
            # method and not raise KeyError
            self.assertEqual(vendor_form.purchase_risk_bill_open, 150.0)
            self.assertEqual(vendor_form.purchase_risk, 150.0)
