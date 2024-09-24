# Copyright 2024 Tecnativa - Carlos Dauden
# License AGPL-3 - See https://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Sale Financial Risk Confirm Action",
    "summary": "Allow confirm sale order in risk exception but changing several sale"
    " order fields",
    "version": "15.0.1.0.0",
    "development_status": "Beta",
    "category": "Accounting",
    "website": "https://github.com/OCA/credit-control",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["carlosdauden"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "sale_financial_risk",
    ],
    "data": ["data/ir_actions_server.xml", "wizards/partner_risk_exceeded_view.xml"],
}
