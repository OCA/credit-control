# Copyright 2026 KEIGHT LLC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Finance Charges on Past-Due Invoices",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Review every potential late charge and bill the ones you select",
    "author": "Allodi.us,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "security/account_finance_charge_security.xml",
        "views/res_config_settings_views.xml",
        "wizards/account_finance_charge_wizard_views.xml",
    ],
    "installable": True,
}
