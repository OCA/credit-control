# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Credit Control Queue Job",
    "summary": """
        This addon adds the opportunity to run
        some credit control tasks in jobs""",
    "version": "12.0.2.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account_credit_control", "queue_job_batch"],
    "data": ["wizard/credit_control_emailer_view.xml"],
    "demo": [],
}
