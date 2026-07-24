# Copyright 2026 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("post_install", "-at_install")
class TestCreditControlCommunicationTranslation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))

        # Activate Dutch language
        cls.env["res.lang"]._activate_lang("nl_NL")

        # Create partner with Dutch language set
        cls.partner_nl = cls.env["res.partner"].create(
            {
                "name": "Dutch Test Partner",
                "lang": "nl_NL",
            }
        )

        # Setup policy and communication record
        cls.policy = cls.env.ref("account_credit_control.credit_control_3_time")
        cls.policy_level = cls.env.ref("account_credit_control.3_time_1")
        cls.policy_level.mail_show_invoice_detail = True

        cls.communication = cls.env["credit.control.communication"].create(
            {
                "partner_id": cls.partner_nl.id,
                "contact_address_id": cls.partner_nl.id,
                "policy_level_id": cls.policy_level.id,
                "currency_id": cls.env.company.currency_id.id,
                "company_id": cls.env.company.id,
            }
        )

    def test_communication_table_language_propagation(self):
        """Verify _get_credit_control_communication_table uses partner's lang."""
        # Generate table
        table_html = self.communication._get_credit_control_communication_table()

        # Check headers that are reliably translated in the standard nl_NL locale
        self.assertIn(
            "Factuurnummer",
            table_html,
            "The context switch failed: 'Invoice number' was not translated.",
        )
        self.assertIn(
            "Vervaldatum",
            table_html,
            "The context switch failed: 'Due date' was not translated.",
        )

    def test_communication_table_fallback_lang(self):
        """Verify table falls back gracefully when contact has no lang set."""
        self.partner_nl.lang = False
        table_html = self.communication._get_credit_control_communication_table()

        # Fallback to source English strings
        self.assertIn("Invoices summary", table_html)
