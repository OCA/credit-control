# Copyright 2016-2018 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Account Financial Risk',
    'summary': 'Manage customer risk',
    'version': '12.0.3.1.0',
    'category': 'Accounting',
    'license': 'AGPL-3',
    'author': 'Tecnativa, Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/credit-control',
    'depends': [
        'account',
    ],
    'data': [
        'security/security.xml',
        'views/account_financial_risk_view.xml',
        'views/res_config_view.xml',
        'views/res_partner_view.xml',
        'wizards/account_invoice_state_view.xml',
        'wizards/partner_risk_exceeded_view.xml',
        'templates/assets.xml',
    ],
    'installable': True,
    'pre_init_hook': 'pre_init_hook',
}
