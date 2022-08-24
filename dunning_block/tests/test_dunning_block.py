# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import datetime

from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class DunningBlock(AccountTestInvoicingCommon):
    def setUp(self):
        super(DunningBlock, self).setUp()
        self.env.user.groups_id |= self.env.ref(
            "account_credit_control.group_account_credit_control_manager"
        )

        time = datetime.date.today()
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": 1,
            "invoice_date": time,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.ref("product.product_product_2"),
                        "price_unit": 642.0,
                        "quantity": 1,
                    },
                )
            ],
        }
        self.inv = self.env["account.move"].create(invoice_vals)
        self.inv.action_post()
        self.dunning_reason_id = self.env["dunning.block.reason"].create(
            {"name": "Dunning Reason"}
        )

        self.wizard_vals = {
            "dunning_block_end_date": datetime.date.today()
            + datetime.timedelta(days=2),
            "dunning_block_reason_id": self.dunning_reason_id.id,
            "dunning_block_note": "Dunning block note!",
        }
        self.wizard = (
            self.env["dunning.block.wizard"]
            .with_context(active_id=self.inv.id)
            .create(self.wizard_vals)
        )

    def test_01_set_dunning_block_action(self):
        self.wizard.set_dunning_block_action()

        self.assertTrue(self.inv.dunning_block_active)
        self.assertTrue(self.inv.dunning_block_end_date)
        self.assertTrue(self.inv.dunning_block_reason_id)
        self.assertTrue(self.inv.dunning_block_note)

    def test_02_update_dunning_block_action(self):
        self.wizard.set_dunning_block_action()

        update_vals = {
            "dunning_block_end_date": datetime.date.today()
            + datetime.timedelta(days=10),
            "dunning_block_reason_id": self.env["dunning.block.reason"]
            .create({"name": "Dunning Reason 2"})
            .id,
            "dunning_block_note": "Updated dunning block!",
        }
        wizard = (
            self.env["dunning.block.wizard"]
            .with_context(active_id=self.inv.id)
            .create(update_vals)
        )
        wizard.set_dunning_block_action()

        self.assertTrue(self.inv.dunning_block_active)
        self.assertEqual(
            self.inv.dunning_block_end_date, update_vals["dunning_block_end_date"]
        )
        self.assertEqual(
            self.inv.dunning_block_reason_id.id, update_vals["dunning_block_reason_id"]
        )
        self.assertEqual(self.inv.dunning_block_note, update_vals["dunning_block_note"])

    def test_03_remove_dunning_block_action(self):
        self.wizard.set_dunning_block_action()

        wizard = (
            self.env["dunning.block.wizard"]
            .with_context(active_id=self.inv.id)
            .create(self.wizard_vals)
        )
        wizard.remove_dunning_block_action()

        self.assertFalse(self.inv.dunning_block_active)
        self.assertFalse(self.inv.dunning_block_end_date)
        self.assertFalse(self.inv.dunning_block_reason_id)
        self.assertFalse(self.inv.dunning_block_note)

    def test_04_dunning_block_history_create(self):
        self.wizard.set_dunning_block_action()

        self.assertEqual(self.inv.dunning_block_history_ids.move_id, self.inv)
        self.assertTrue(self.inv.dunning_block_history_ids.dunning_block_active)
        self.assertTrue(self.inv.dunning_block_history_ids.dunning_block_end_date)
        self.assertTrue(self.inv.dunning_block_history_ids.dunning_block_reason_id)
        self.assertTrue(self.inv.dunning_block_history_ids.dunning_block_note)
        self.assertEqual(self.inv.dunning_block_history_ids.status, "active")

    def test_05_dunning_block_history_update(self):
        self.wizard.set_dunning_block_action()

        update_vals = {
            "dunning_block_end_date": datetime.date.today()
            + datetime.timedelta(days=20),
            "dunning_block_reason_id": self.env["dunning.block.reason"]
            .create({"name": "Dunning Reason 3"})
            .id,
            "dunning_block_note": "Updated dunning block history!",
        }
        wizard = (
            self.env["dunning.block.wizard"]
            .with_context(active_id=self.inv.id)
            .create(update_vals)
        )
        wizard.set_dunning_block_action()
        line = self.inv.dunning_block_history_ids

        self.assertEqual(len(line), 1)
        self.assertTrue(line.dunning_block_active)
        self.assertEqual(
            line.dunning_block_end_date, update_vals["dunning_block_end_date"]
        )
        self.assertEqual(
            line.dunning_block_reason_id.id, update_vals["dunning_block_reason_id"]
        ),
        self.assertEqual(self.inv.dunning_block_note, update_vals["dunning_block_note"])

    def test_06_dunning_block_history_interrupted(self):
        self.wizard.set_dunning_block_action()

        wizard = (
            self.env["dunning.block.wizard"]
            .with_context(active_id=self.inv.id)
            .create(self.wizard_vals)
        )
        wizard.remove_dunning_block_action()

        self.assertEqual(len(self.inv.dunning_block_history_ids), 1)
        self.assertFalse(self.inv.dunning_block_history_ids.dunning_block_active)
        self.assertEqual(self.inv.dunning_block_history_ids.status, "interrupted")

    def test_07_dunning_block_history_stop(self):
        self.wizard.set_dunning_block_action()
        self.inv._remove_dunning_block()

        self.assertEqual(len(self.inv.dunning_block_history_ids), 1)
        self.assertFalse(self.inv.dunning_block_history_ids.dunning_block_active)
        self.assertEqual(
            self.inv.dunning_block_history_ids.dunning_block_end_date,
            datetime.date.today(),
        )
        self.assertEqual(self.inv.dunning_block_history_ids.status, "done")

    def test_08_dunning_block_history_stop_multiple(self):
        self.wizard.set_dunning_block_action()
        self.inv._remove_dunning_block()
        self.wizard.set_dunning_block_action()
        self.inv._remove_dunning_block()

        self.assertEqual(len(self.inv.dunning_block_history_ids), 2)
        self.assertEqual(
            set(self.inv.dunning_block_history_ids.mapped("dunning_block_active")),
            {False},
        )
        self.assertEqual(
            set(self.inv.dunning_block_history_ids.mapped("status")), {"done"}
        )

    def test_09_dunning_block_run(self):
        """Invoices with active dunning block mustn't be in credit control run"""
        vals = {
            # set dunning block 100 days ahead
            "dunning_block_end_date": datetime.date.today()
            + datetime.timedelta(days=100),
            "dunning_block_reason_id": self.dunning_reason_id.id,
            "dunning_block_note": "Dunning block note!",
        }
        wizard = (
            self.env["dunning.block.wizard"]
            .with_context(active_id=self.inv.id)
            .create(vals)
        )
        wizard.set_dunning_block_action()

        policy = self.env.ref("account_credit_control.credit_control_3_time")
        self.inv.company_id.credit_policy_id = policy
        policy.write({"account_ids": [(6, 0, self.inv.line_ids.account_id.ids)]})

        # Create run 90 days ahead. Dunning block should be
        # still active and mustn't be in the run
        run_date = datetime.date.today() + datetime.timedelta(days=90)
        control_run = self.env["credit.control.run"].create(
            {"date": run_date, "policy_ids": [(6, 0, [policy.id])]}
        )
        control_run.generate_credit_lines()

        self.assertFalse(
            bool(control_run.line_ids.search([("invoice_id", "=", self.inv.id)]))
        )
