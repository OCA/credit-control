# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from datetime import datetime
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCreditControlLine(TransactionCase):

    def test_auto_process(self):
        account_type_rec = self.env.ref('account.data_account_type_receivable')
        account = self.env['account.account'].create({
            'code': '400001',
            'name': 'Customers (test)',
            'user_type_id': account_type_rec.id,
            'reconcile': True,
        })

        journal = self.env['account.invoice']._default_journal()

        move = self.env["account.move"].create({
            'name': 'Test move',
            'date': datetime.today(),
            'journal_id': journal.id,
            'state': 'draft',
        })

        move_line = self.env['account.move.line'].create({
            'account_id': account.id,
            'move_id': move.id,
        })

        policy = self.env.ref('account_credit_control.credit_control_3_time')
        policy.write({
            'account_ids': [(6, 0, [account.id])],
            'auto_process_lower_levels': True,
        })

        policy_level_1 = self.env['credit.control.policy.level'].create({
            'name': 'Test Level 1',
            'policy_id': policy.id,
            'level': 1,
            'computation_mode': 'net_days',
            'delay_days': 1,
            'email_template_id': self.env.ref(
                'account_credit_control.email_template_credit_control_base'
            ).id,
            'channel': 'email',
            'custom_text': 'Test',
            'custom_mail_text': 'Test',
        })

        policy_level_2 = self.env['credit.control.policy.level'].create({
            'name': 'Test Level 2',
            'policy_id': policy.id,
            'level': 2,
            'computation_mode': 'net_days',
            'delay_days': 1,
            'email_template_id': self.env.ref(
                'account_credit_control.email_template_credit_control_base'
            ).id,
            'channel': 'email',
            'custom_text': 'Test',
            'custom_mail_text': 'Test',
        })

        policy_level_3 = self.env['credit.control.policy.level'].create({
            'name': 'Test Level 3',
            'policy_id': policy.id,
            'level': 3,
            'computation_mode': 'net_days',
            'delay_days': 1,
            'email_template_id': self.env.ref(
                'account_credit_control.email_template_credit_control_base'
            ).id,
            'channel': 'email',
            'custom_text': 'Test',
            'custom_mail_text': 'Test',
        })

        partner = self.env['res.partner'].create({
            'name': 'Partner',
            'property_account_receivable_id': account.id,
        })
        partner.credit_policy_id = policy.id

        ccl_1 = self.env['credit.control.line'].create({
            'date': datetime.today(),
            'date_due': datetime.today(),
            'state': 'draft',
            'partner_id': partner.id,
            'account_id': account.id,
            'policy_level_id': policy_level_1.id,
            'channel': 'email',
            'amount_due': 100,
            'balance_due': 100,
            'move_line_id': move_line.id,
        })

        self.assertEqual(ccl_1.auto_process, 'highest_level')

        ccl_2 = self.env['credit.control.line'].create({
            'date': datetime.today(),
            'date_due': datetime.today(),
            'state': 'draft',
            'partner_id': partner.id,
            'account_id': account.id,
            'policy_level_id': policy_level_2.id,
            'channel': 'email',
            'amount_due': 100,
            'balance_due': 100,
            'move_line_id': move_line.id,
        })

        self.assertEqual(ccl_1.auto_process, 'low_level')
        self.assertEqual(ccl_2.auto_process, 'highest_level')
        self.assertTrue(ccl_1 in ccl_2.get_lower_related_lines())

        ccl_1.write({'policy_level_id': policy_level_3.id})

        self.assertEqual(ccl_1.auto_process, 'highest_level')
        self.assertEqual(ccl_2.auto_process, 'low_level')
        self.assertTrue(ccl_2 in ccl_1.get_lower_related_lines())

        policy.write({'auto_process_lower_levels': False})

        self.assertEqual(ccl_1.auto_process, 'no_auto_process')
        self.assertEqual(ccl_2.auto_process, 'no_auto_process')

        policy.write({'auto_process_lower_levels': True})

        self.assertEqual(ccl_1.auto_process, 'highest_level')
        self.assertEqual(ccl_2.auto_process, 'low_level')
        self.assertTrue(ccl_2 in ccl_1.get_lower_related_lines())

        ccl_1.unlink()

        self.assertEqual(ccl_2.auto_process, 'highest_level')
