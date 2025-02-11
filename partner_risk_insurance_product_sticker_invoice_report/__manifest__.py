# Copyright 2025 Moduon Team S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

{
    "name": "Product Sticker on Invoice Reports with Risk Insurance",
    "summary": "Display a Sticker on Invoice Reports secured with Risk Insurance",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Uncategorized",
    "website": "https://github.com/OCA/credit-control",
    "author": "Moduon, Odoo Community Association (OCA)",
    "maintainers": ["Shide", "rafaelbn"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "auto_install": True,
    "depends": ["partner_risk_insurance", "account_invoice_report_product_sticker"],
    "data": [
        "views/product_sticker_view.xml",
        "views/credit_policy_company_view.xml",
    ],
}
