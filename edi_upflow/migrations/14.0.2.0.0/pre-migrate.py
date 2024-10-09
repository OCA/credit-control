from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    openupgrade.rename_xmlids(
        env.cr,
        [
            (
                "edi_upflow.account_move_form_view",
                "edi_upflow.view_full_reconcile_form",
            ),
        ],
    )
