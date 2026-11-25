{
    "name": "Sale Financial Risk Exclude Order Type",
    "summary": "Exclude sale order types from financial risk computation",
    "version": "17.0.1.0.0",
    "category": "Credit Control",
    "author": "Binhex Systems Solutions S.L, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/credit-control",
    "license": "AGPL-3",
    "depends": [
        "sale_financial_risk",
        "sale_order_type",
    ],
    "data": [
        "views/sale_order_type_views.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
    "development_status": "Alpha",
}
