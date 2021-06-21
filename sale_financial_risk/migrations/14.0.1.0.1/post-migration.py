from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env["sale.order.line"].search(
        [
            ("state", "=", "done"),
        ]
    )._compute_risk_amount()
