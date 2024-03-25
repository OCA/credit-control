# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "EDI UPFLOW",
    "summary": "Odoo Upflow.io connector",
    "version": "14.0.2.0.0",
    "development_status": "Alpha",
    "category": "EDI",
    "website": "https://github.com/OCA/credit-control",
    "author": "Pierre Verkest, Odoo Community Association (OCA)",
    "maintainers": ["petrus-v"],
    "license": "AGPL-3",
    "application": True,
    "depends": [
        "account",
        "base_upflow",
        "edi_oca",
        "webservice",
        "edi_webservice_oca",
        "edi_account_oca",
    ],
    "data": [
        "data/cron.xml",
        "data/edi.xml",
        "views/account_full_reconcile.xml",
        "views/account_partial_reconcile.xml",
        "views/edi_exchange_record.xml",
        "views/res_config_settings.xml",
        "views/res_partner.xml",
        "views/webservice_backend.xml",
    ],
    "external_dependencies": {"python": ["responses"]},
    "demo": [],
    "installable": True,
}
