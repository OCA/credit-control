# Copyright 2026 Humanilog GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Credit Control - All Receivable Accounts",
    "summary": "Optionally apply a credit control policy to all receivable "
    "accounts instead of maintaining an explicit account list",
    "version": "14.0.1.0.0",
    "category": "Finance",
    "license": "AGPL-3",
    "author": "Humanilog GmbH, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account_credit_control"],
    "data": ["views/credit_control_policy.xml"],
    "development_status": "Beta",
    "installable": True,
}
