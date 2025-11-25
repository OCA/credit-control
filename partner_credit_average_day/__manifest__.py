# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Partner Credit Average Day",
    "version": "18.0.1.0.0",
    "summary": """Block sale confirmation when partner average
    open invoice age exceeds configured days""",
    "category": "Accounting",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "maintainer": "Open Source Integrators",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["sale", "account"],
    "data": [
        "security/groups.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
}
