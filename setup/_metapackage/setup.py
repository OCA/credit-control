import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-credit-control",
    description="Meta package for oca-credit-control Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-account_credit_control',
        'odoo13-addon-account_financial_risk',
        'odoo13-addon-account_payment_return_financial_risk',
        'odoo13-addon-partner_risk_insurance',
        'odoo13-addon-sale_financial_risk',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
