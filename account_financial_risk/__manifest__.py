# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Financial Risk",
    "summary": "Manage customer risk",
    "version": "16.0.1.3.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["carlosdauden"],
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/account_financial_risk_view.xml",
        "views/res_config_view.xml",
        "views/res_partner_view.xml",
        "wizards/partner_risk_exceeded_view.xml",
    ],
    "assets": {
        "web.assets_common": [
            "account_financial_risk/static/src/scss/account_financial_risk_table.scss",
        ],
    },
    "installable": True,
}
