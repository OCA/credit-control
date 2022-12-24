import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-credit-control",
    description="Meta package for oca-credit-control Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_credit_control>=15.0dev,<15.1dev',
        'odoo-addon-account_financial_risk>=15.0dev,<15.1dev',
        'odoo-addon-account_invoice_overdue_reminder>=15.0dev,<15.1dev',
        'odoo-addon-partner_risk_insurance>=15.0dev,<15.1dev',
        'odoo-addon-sale_financial_risk>=15.0dev,<15.1dev',
        'odoo-addon-sale_financial_risk_info>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
