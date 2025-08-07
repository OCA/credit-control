# Copyright 2025 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Credit Control",
    "version": "18.0.2.0.0",
    "author": "360 ERP, Odoo Community Association (OCA)",
    "category": "Finance",
    "depends": [
        "account_credit_control",
        "queue_job_batch",
    ],
    "website": "https://github.com/OCA/credit-control",
    "data": ["wizard/res_config_settings.xml"],
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
    "application": True,
}
