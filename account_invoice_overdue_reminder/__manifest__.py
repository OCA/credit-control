# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Overdue Invoice Reminder",
    "version": "14.0.1.2.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Simple mail/letter/phone overdue customer invoice reminder ",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "wizard/overdue_reminder_wizard_view.xml",
        "views/res_partner.xml",
        "views/report.xml",
        "views/report_overdue_reminder.xml",
        "views/account_move.xml",
        "views/account_invoice_overdue_reminder.xml",
        "views/overdue_reminder_result.xml",
        "views/overdue_reminder_action.xml",
        "wizard/res_config_settings_view.xml",
        "data/overdue_reminder_result.xml",
        "data/mail_template.xml",
    ],
    "installable": True,
    "application": True,
    "pre_init_hook": "pre_init_hook",
}
