# Copyright 2021 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Financial Risk Info",
    "summary": "Adds risk consumption info in sales orders.",
    "version": "14.0.1.0.0",
    "category": "Sales Management",
    "license": "AGPL-3",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["sale", "account_financial_risk"],
    "data": ["views/res_partner_view.xml", "views/sale_order_view.xml"],
    "installable": True,
}
