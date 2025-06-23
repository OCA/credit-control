# Copyright 2025 Akretion (http://www.akretion.com).
# @author Mathieu Delva <mathieu.delva@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Invoice Overdue Crm Team",
    "summary": "Account Invoice Overdue Crm Team",
    "version": "14.0.0.1.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["mathieu-delva"],
    "website": "https://github.com/OCA/credit-control",
    "application": True,
    "installable": True,
    "external_dependencies": {"python": [], "bin": []},
    "depends": ["account_invoice_overdue_reminder"],
    "data": [
        "wizard/overdue_reminder_wizard_view.xml",
    ],
    "demo": [],
}
