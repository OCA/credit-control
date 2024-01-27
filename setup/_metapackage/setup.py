import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-credit-control",
    description="Meta package for oca-credit-control Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_credit_control>=16.0dev,<16.1dev',
        'odoo-addon-account_credit_control_dunning_fees>=16.0dev,<16.1dev',
        'odoo-addon-account_financial_risk>=16.0dev,<16.1dev',
        'odoo-addon-account_invoice_overdue_reminder>=16.0dev,<16.1dev',
        'odoo-addon-account_invoice_overdue_warn>=16.0dev,<16.1dev',
        'odoo-addon-account_invoice_overdue_warn_sale>=16.0dev,<16.1dev',
        'odoo-addon-account_payment_return_financial_risk>=16.0dev,<16.1dev',
        'odoo-addon-partner_risk_insurance>=16.0dev,<16.1dev',
        'odoo-addon-sale_financial_risk>=16.0dev,<16.1dev',
        'odoo-addon-sale_financial_risk_info>=16.0dev,<16.1dev',
        'odoo-addon-sale_payment_sheet_financial_risk>=16.0dev,<16.1dev',
        'odoo-addon-stock_financial_risk>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
