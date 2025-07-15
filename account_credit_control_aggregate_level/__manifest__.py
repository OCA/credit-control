# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Credit Control",
    "version": "18.0.1.0.0",
    "author": "ACSONE SA/NV, Odoo Community Association (OCA)",
    "maintainer": "ACSONE SA/NV",
    "category": "Finance",
    "depends": ["account_credit_control"],
    "website": "https://github.com/OCA/credit-control",
    "data": [
        # Views
        "views/credit_control_line.xml",
        "views/credit_control_policy.xml",
    ],
    "demo": [],
    "installable": True,
    "license": "AGPL-3",
    "application": True,
}
