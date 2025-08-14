# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account credit control attach invoices",
    "summary": """Extend account credit control to print credit
        control summary with invoices""",
    "version": "18.0.1.0.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "category": "Finance",
    "website": "https://github.com/OCA/credit-control",
    "license": "AGPL-3",
    "depends": [
        "account_credit_control",
    ],
    "data": [
        "views/res_config_settings.xml",
    ],
    "auto_install": False,
    "installable": True,
}
