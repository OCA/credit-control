import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-credit-control",
    description="Meta package for oca-credit-control Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_credit_control>=16.0dev,<16.1dev',
        'odoo-addon-account_invoice_overdue_reminder>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
