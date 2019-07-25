# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Credit Control Analysis",
    "summary": """ This addon adds analysis report for credit control.""",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://www.acsone.eu",
    "depends": ["account_credit_control"],
    "data": [
        "views/res_partner.xml",
        "report/account_credit_control_analysis.xml",
        "security/acl_account_credit_control_analysis.xml",
    ],
    "demo": [],
}
