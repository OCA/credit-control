import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-credit-control",
    description="Meta package for oca-credit-control Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-account_credit_control',
        'odoo14-addon-account_financial_risk',
        'odoo14-addon-account_invoice_overdue_reminder',
        'odoo14-addon-account_invoice_overdue_warn',
        'odoo14-addon-account_invoice_overdue_warn_sale',
        'odoo14-addon-account_payment_return_financial_risk',
        'odoo14-addon-partner_risk_insurance',
        'odoo14-addon-sale_financial_risk',
        'odoo14-addon-stock_financial_risk',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
