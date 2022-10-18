# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "POS Financial Risk",
    "version": "15.0.1.0.0",
    "development_status": "Production/Stable",
    "summary": "Manage partner risk in pos orders",
    "author": "Jarsa,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "website": "https://github.com/OCA/credit-control",
    "depends": ["point_of_sale", "account_financial_risk"],
    "assets": {
        "point_of_sale.assets": [
            "pos_financial_risk/static/src/js/*.js",
        ],
    },
    "category": "Credit Control",
    "installable": True,
    "maintainers": ["alan196"],
}
