# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    # Remove old cron
    openupgrade.delete_records_safely_by_xml_id(env, [
        'account_financial_risk.ir_cron_due_invoice_every_day',
    ])
    # Remove old stored computed fields db columns
    openupgrade.drop_columns(env.cr, [
        ('res_partner', 'risk_invoice_draft'),
        ('res_partner', 'risk_invoice_open'),
        ('res_partner', 'risk_invoice_unpaid'),
        ('res_partner', 'risk_account_amount'),
        ('res_partner', 'risk_account_amount_unpaid'),
    ])
