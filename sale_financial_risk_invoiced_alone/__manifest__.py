# Copyright 2026 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Financial Risk Invoiced Alone",
    "summary": "No sales orders risk for lines only invoiced with others",
    "version": "18.0.1.0.0",
    "category": "Sales Management",
    "license": "AGPL-3",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["carlosdauden"],
    "website": "https://github.com/OCA/credit-control",
    "depends": ["sale_financial_risk"],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
