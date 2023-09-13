# Copyright 2021 Tecnativa - Carlos Dauden
# Copyright 2023 Tecnativa - Carolina Fernandez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Payment Sheet Financial Risk",
    "summary": "Manage partner risk in sale payment sheet",
    "version": "16.0.1.0.0",
    "category": "Account",
    "license": "AGPL-3",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account_financial_risk", "sale_payment_sheet"],
    "data": [
        "views/res_partner_view.xml",
        "views/sale_payment_sheet_financial_risk_view.xml",
    ],
    "installable": True,
}
