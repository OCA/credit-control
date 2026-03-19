# Copyright 2026 Jarsa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Purchase Financial Risk",
    "summary": "Manage financial risk and credit limits for vendors in purchases",
    "version": "17.0.1.0.0",
    "category": "Purchases",
    "website": "https://github.com/OCA/credit-control",
    "author": "Jarsa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "purchase",
        "account_financial_risk",
    ],
    "data": [
        "security/purchase_financial_risk_security.xml",
        "security/ir.model.access.csv",
        "wizards/purchase_risk_exception_views.xml",
        "views/purchase_order_line_views.xml",
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "development_status": "Alpha",
}
