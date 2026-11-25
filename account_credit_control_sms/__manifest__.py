# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Account Credit Control SMS",
    "summary": "Add SMS channel to credit control policy levels",
    "version": "16.0.1.0.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainer": "Camptocamp",
    "category": "Finance",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account_credit_control", "sms"],
    "data": [
        "data/ir_actions_server.xml",
        "data/sms_template.xml",
        "views/credit_control_line.xml",
        "views/credit_control_policy.xml",
        "views/credit_control_policy_level.xml",
    ],
    "installable": True,
    "license": "AGPL-3",
}
