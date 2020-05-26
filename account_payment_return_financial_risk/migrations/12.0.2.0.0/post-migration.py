# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    # Remove old stored computed fields db columns
    openupgrade.drop_columns(env.cr, [
        ('res_partner', 'risk_payment_return'),
    ])
