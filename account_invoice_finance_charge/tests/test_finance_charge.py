# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, timedelta
from unittest.mock import patch

from psycopg2 import IntegrityError
from psycopg2.errors import UniqueViolation

from odoo import Command, fields
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFinanceCharge(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.revenue = cls.company_data["default_account_revenue"]
        cls.company.write(
            {
                "finance_charge_rate": 18.0,
                "finance_charge_grace_days": 0,
                "finance_charge_interval_days": 30,
                "finance_charge_account_id": cls.revenue.id,
            }
        )
        cls.invoice_a = cls._make_invoice(cls.partner_a, date(2026, 1, 31), 1000.0)
        cls.invoice_b = cls._make_invoice(cls.partner_b, date(2026, 2, 28), 500.0)

    @classmethod
    def _make_invoice(cls, partner, due, amount):
        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": due,
                "invoice_date_due": due,
                "invoice_payment_term_id": False,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "goods",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": cls.revenue.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _wizard(self, on_date):
        wizard = self.env["account.finance.charge.wizard"].create({"date": on_date})
        wizard._load_lines()
        return wizard

    def _line(self, wizard, invoice):
        return wizard.line_ids.filtered(lambda line: line.move_id == invoice)

    def _pay(self, invoice, amount):
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create(
            {"amount": amount, "payment_date": date(2026, 3, 1)}
        )._create_payments()

    def test_lists_every_past_due_invoice_unselected(self):
        wizard = self._wizard(date(2026, 3, 31))
        self.assertEqual(wizard.line_ids.move_id, self.invoice_a | self.invoice_b)
        self.assertFalse(wizard.line_ids.filtered("selected"))
        self.assertEqual(wizard.selected_count, 0)

    def test_amount_is_daily_simple_interest(self):
        line = self._line(self._wizard(date(2026, 3, 31)), self.invoice_a)
        self.assertEqual(line.days, 59)
        self.assertEqual(line.days_past_due, 59)
        self.assertAlmostEqual(line.amount, 29.10)
        self.assertEqual(line.date_from, date(2026, 2, 1))

    def test_select_all_and_none(self):
        wizard = self._wizard(date(2026, 3, 31))
        wizard.action_select_all()
        self.assertEqual(wizard.selected_count, 2)
        wizard.action_select_none()
        self.assertEqual(wizard.selected_count, 0)

    def test_requires_a_selection(self):
        with self.assertRaises(UserError):
            self._wizard(date(2026, 3, 31)).action_create_charges()

    def test_requires_configuration(self):
        self.company.finance_charge_rate = 0
        is_admin = self.env.user.has_group(
            "base.group_system"
        ) and self.env.user.has_group("account.group_account_manager")
        with self.assertRaises(RedirectWarning if is_admin else UserError):
            self.env["account.finance.charge.wizard"].action_open()

    def test_only_selected_are_billed_as_untaxed_drafts(self):
        wizard = self._wizard(date(2026, 3, 31))
        line = self._line(wizard, self.invoice_a)
        line.selected = True
        amount = line.amount
        mails_before = self.env["mail.mail"].sudo().search_count([])
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        self.assertEqual(len(charge), 1)
        self.assertEqual(charge.state, "draft")
        self.assertTrue(charge.is_finance_charge)
        self.assertEqual(charge.partner_id, self.partner_a.commercial_partner_id)
        self.assertEqual(charge.invoice_line_ids.account_id, self.revenue)
        self.assertFalse(charge.invoice_line_ids.tax_ids)
        self.assertAlmostEqual(charge.amount_total, amount)
        self.assertIn(self.invoice_a.name, charge.invoice_line_ids.name)
        self.assertEqual(self.env["mail.mail"].sudo().search_count([]), mails_before)
        remaining = self._wizard(date(2026, 3, 31))
        self.assertEqual(remaining.line_ids.move_id, self.invoice_b)

    def test_one_charge_invoice_per_customer(self):
        second = self._make_invoice(self.partner_a, date(2026, 2, 10), 200.0)
        wizard = self._wizard(date(2026, 3, 31))
        wizard.action_select_all()
        action = wizard.action_create_charges()
        charges = self.env["account.move"].search(action["domain"])
        self.assertEqual(len(charges), 2)
        charge_a = charges.filtered(lambda c: c.partner_id == self.partner_a)
        self.assertEqual(len(charge_a.invoice_line_ids), 2)
        history = self.env["account.finance.charge.line"].search(
            [("source_move_id", "=", second.id)]
        )
        self.assertEqual(history.charge_move_id, charge_a)
        self.assertIn(second.name, history.charge_line_id.name)

    def test_next_charge_starts_after_last_period(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        wizard.action_create_charges()
        too_soon = self._wizard(date(2026, 4, 10))
        self.assertFalse(self._line(too_soon, self.invoice_a))
        later = self._wizard(date(2026, 4, 30))
        line = self._line(later, self.invoice_a)
        self.assertEqual(line.days, 30)
        self.assertEqual(line.date_from, date(2026, 4, 1))
        self.assertAlmostEqual(line.amount, 14.79)

    def test_cancelled_or_deleted_charge_frees_the_period(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        charge.button_cancel()
        again = self._wizard(date(2026, 3, 31))
        line = self._line(again, self.invoice_a)
        self.assertEqual(line.days, 59)
        line.selected = True
        action = again.action_create_charges()
        self.env["account.move"].search(action["domain"]).unlink()
        third = self._wizard(date(2026, 3, 31))
        self.assertEqual(self._line(third, self.invoice_a).days, 59)

    def test_a_period_cannot_be_billed_twice(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charges = self.env["account.move"].search(action["domain"])
        existing = self.env["account.finance.charge.line"].search(
            [("charge_move_id", "in", charges.ids)]
        )
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                existing.sudo().copy({"date_to": date(2026, 4, 30)})

    def test_finance_charges_earn_no_interest(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        charge.invoice_date_due = date(2026, 3, 31)
        charge.action_post()
        later = self._wizard(date(2026, 6, 30))
        self.assertNotIn(charge, later.line_ids.move_id)

    def test_paid_invoice_is_excluded_and_partial_uses_balance(self):
        self._pay(self.invoice_a, 400.0)
        self._pay(self.invoice_b, 500.0)
        wizard = self._wizard(date(2026, 3, 31))
        self.assertEqual(wizard.line_ids.move_id, self.invoice_a)
        self.assertAlmostEqual(wizard.line_ids.residual, 600.0)
        self.assertAlmostEqual(wizard.line_ids.amount, 17.46)

    def test_grace_days_delay_interest(self):
        self.company.finance_charge_grace_days = 10
        line = self._line(self._wizard(date(2026, 3, 31)), self.invoice_a)
        self.assertEqual(line.days, 49)
        self.assertEqual(line.days_past_due, 59)
        inside = self._wizard(date(2026, 2, 5))
        self.assertFalse(self._line(inside, self.invoice_a))

    def test_minimum_and_cap(self):
        self.company.finance_charge_min_amount = 50.0
        line = self._line(self._wizard(date(2026, 3, 31)), self.invoice_a)
        self.assertAlmostEqual(line.amount, 50.0)
        self.assertEqual(line.note, "Minimum applied")
        self.company.finance_charge_min_amount = 0.0
        self.company.finance_charge_cap_percent = 2.0
        wizard = self._wizard(date(2026, 3, 31))
        line = self._line(wizard, self.invoice_a)
        self.assertAlmostEqual(line.amount, 20.0)
        self.assertEqual(line.note, "Cap applied")
        line.selected = True
        wizard.action_create_charges()
        later = self._wizard(date(2026, 6, 30))
        self.assertFalse(self._line(later, self.invoice_a))

    def test_stale_screen_is_refused(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        self._pay(self.invoice_a, 400.0)
        with self.assertRaises(UserError):
            wizard.action_create_charges()
        wizard.action_recalculate()
        line = self._line(wizard, self.invoice_a)
        self.assertTrue(line.selected)
        self.assertAlmostEqual(line.residual, 600.0)

    def test_changed_date_is_refused_when_amount_is_unchanged(self):
        self.company.finance_charge_min_amount = 50.0
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        wizard.date = date(2026, 4, 5)
        with self.assertRaises(UserError):
            wizard.action_create_charges()

    def test_edited_customer_is_refused(self):
        wizard = self._wizard(date(2026, 3, 31))
        line = self._line(wizard, self.invoice_a)
        line.write({"selected": True, "partner_id": self.partner_b.id})
        with self.assertRaises(UserError):
            wizard.action_create_charges()

    def test_future_date_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["account.finance.charge.wizard"].create(
                {"date": fields.Date.today() + timedelta(days=1)}
            )

    def test_unapplied_credit_is_flagged_and_skipped_by_select_all(self):
        credit = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner_a.id,
                "invoice_date": date(2026, 1, 28),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "credit",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.revenue.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        credit.action_post()
        wizard = self._wizard(date(2026, 3, 31))
        line = self._line(wizard, self.invoice_a)
        self.assertTrue(line.review_note)
        wizard.action_select_all()
        self.assertFalse(line.selected)
        self.assertTrue(self._line(wizard, self.invoice_b).selected)

    def test_payment_in_process_is_listed_and_flagged(self):
        self.invoice_a.payment_state = "in_payment"
        line = self._line(self._wizard(date(2026, 3, 31)), self.invoice_a)
        self.assertTrue(line.review_note)

    def test_minimum_never_applies_to_a_smaller_balance(self):
        self.company.finance_charge_min_amount = 50.0
        self._pay(self.invoice_a, 980.0)
        line = self._line(self._wizard(date(2026, 3, 31)), self.invoice_a)
        self.assertAlmostEqual(line.amount, 0.58)
        self.assertFalse(line.note)

    def test_label_explains_a_minimum(self):
        self.company.finance_charge_min_amount = 50.0
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        self.assertIn("Minimum applied", charge.invoice_line_ids.name)

    def test_duplicated_charge_stays_a_finance_charge(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        self.assertTrue(charge.copy().is_finance_charge)

    def test_cancelled_charge_cannot_return_over_a_newer_charge(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        first = self.env["account.move"].search(action["domain"])
        first.button_cancel()
        wizard = self._wizard(date(2026, 4, 30))
        self._line(wizard, self.invoice_a).selected = True
        wizard.action_create_charges()
        with self.assertRaises(UserError):
            first.button_draft()

    def test_edited_draft_amount_counts_toward_the_cap(self):
        self.company.finance_charge_cap_percent = 5.0
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        charge.invoice_line_ids.price_unit = 10.0
        later = self._wizard(date(2026, 6, 30))
        self.assertAlmostEqual(self._line(later, self.invoice_a).amount, 40.0)

    def test_child_contact_bills_the_company(self):
        contact = self.env["res.partner"].create(
            {"name": "Buyer", "parent_id": self.partner_a.id}
        )
        invoice = self._make_invoice(contact, date(2026, 2, 1), 100.0)
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, invoice).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        self.assertEqual(charge.partner_id, self.partner_a)

    def test_product_is_used_without_adding_tax(self):
        product = self.env["product.product"].create({"name": "Finance charge"})
        self.company.finance_charge_product_id = product
        wizard = self._wizard(date(2026, 3, 31))
        line = self._line(wizard, self.invoice_a)
        line.selected = True
        amount = line.amount
        action = wizard.action_create_charges()
        charge_line = self.env["account.move"].search(action["domain"]).invoice_line_ids
        self.assertEqual(charge_line.product_id, product)
        self.assertEqual(charge_line.account_id, self.revenue)
        self.assertFalse(charge_line.tax_ids)
        self.assertAlmostEqual(charge_line.price_unit, amount)

    def test_review_screens_are_private_to_their_user(self):
        wizard = self._wizard(date(2026, 3, 31))
        other = new_test_user(
            self.env,
            login="finance_charge_other",
            groups="base.group_user,account.group_account_invoice",
            company_id=self.company.id,
            company_ids=[Command.set(self.company.ids)],
        )
        found = self.env["account.finance.charge.wizard"].with_user(other).search([])
        self.assertNotIn(wizard.id, found.ids)

    def test_billing_users_cannot_write_history(self):
        other = new_test_user(
            self.env,
            login="finance_charge_billing",
            groups="base.group_user,account.group_account_invoice",
            company_id=self.company.id,
            company_ids=[Command.set(self.company.ids)],
        )
        history = self.env["account.finance.charge.line"].with_user(other)
        with self.assertRaises(AccessError):
            history.create({})

    def test_interval_must_be_at_least_one_day(self):
        with self.assertRaises(ValidationError):
            self.company.finance_charge_interval_days = 0

    def _post_credit(self, partner, amount):
        credit = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": partner.id,
                "invoice_date": date(2026, 3, 1),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "credit",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.revenue.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        credit.action_post()
        self.env.invalidate_all()
        return credit

    def test_payment_after_the_list_was_built_is_refused(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        self._post_credit(self.partner_a, 1000.0)
        with self.assertRaises(UserError):
            wizard.action_create_charges()

    def test_recalculate_unticks_a_row_that_turned_red(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        self._post_credit(self.partner_a, 1000.0)
        wizard.action_recalculate()
        self.assertFalse(self._line(wizard, self.invoice_a).selected)

    def test_select_all_unticks_a_hand_ticked_red_row(self):
        self._post_credit(self.partner_a, 1000.0)
        wizard = self._wizard(date(2026, 3, 31))
        line = self._line(wizard, self.invoice_a)
        line.selected = True
        wizard.action_select_all()
        self.assertFalse(line.selected)

    def test_payment_without_journal_entry_flags_the_customer(self):
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 1000.0,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.flush_recordset()
        self.env.cr.execute(
            "UPDATE account_payment SET move_id = NULL, state = 'in_process' "
            "WHERE id = %s",
            (payment.id,),
        )
        self.env.invalidate_all()
        wizard = self._wizard(date(2026, 3, 31))
        self.assertTrue(self._line(wizard, self.invoice_a).review_note)
        self.assertFalse(self._line(wizard, self.invoice_b).review_note)

    def test_hand_ticked_red_row_is_noted_on_the_charge(self):
        self._post_credit(self.partner_a, 1000.0)
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        self.assertIn(self.invoice_a.name, charge.message_ids[0].body)

    def test_cannot_post_a_charge_on_a_cancelled_invoice(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        action = wizard.action_create_charges()
        charge = self.env["account.move"].search(action["domain"])
        self.invoice_a.button_draft()
        self.invoice_a.button_cancel()
        with self.assertRaises(UserError):
            charge.action_post()

    def test_simultaneous_billing_gives_a_plain_message(self):
        wizard = self._wizard(date(2026, 3, 31))
        self._line(wizard, self.invoice_a).selected = True
        with patch.object(
            type(wizard), "_create_charge_invoice", side_effect=UniqueViolation()
        ):
            with self.assertRaises(UserError):
                wizard.action_create_charges()
