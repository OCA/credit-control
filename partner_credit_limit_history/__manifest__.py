# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Partner Credit Limit History",
    "version": "13.0.1.0.0",
    "category": "Credit Control",
    "website": "https://github.com/OCA/credit-control",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["base"],
    "maintainers": ["victoralmau"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/partner_credit_limit_wizard.xml",
        "views/res_partner_view.xml",
    ],
}
