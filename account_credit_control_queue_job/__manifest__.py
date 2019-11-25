# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Credit Control Queue Job",
    "summary": """
        This addon adds the opportunity to run
        some credit control tasks in jobs""",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://acsone.eu",
    "depends": ["account_credit_control", "queue_job_batch"],
    "data": [
        "views/credit_control_run.xml",
        "wizard/credit_control_emailer_view.xml",
    ],
    "demo": [],
}
