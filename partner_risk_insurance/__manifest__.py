# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Partner Risk Insurance",
    "version": "15.0.3.0.1",
    "development_status": "Production/Stable",
    "summary": "Risk insurance partner information",
    "author": "AvanzOSC,"
    "Tecnativa,"
    "Factor Libre S.L,"
    "NaN·tic,"
    "Moduon,"
    "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "website": "https://github.com/OCA/credit-control",
    "depends": ["mail", "account"],  # required for tracking=True attribute
    "category": "Credit Control",
    "data": [
        "security/ir.model.access.csv",
        "views/credit_policy_company_view.xml",
        "views/res_partner_view.xml",
        "views/account_move_view.xml",
        "wizard/invoice_risk_insurance_wizard.xml",
        "templates/invoice_risk_insurance_template.xml",
    ],
    "installable": True,
    "maintainers": ["Daniel-CA", "sergio-teruel", "omar7r", "Tardo", "Shide"],
    "pre_init_hook": "pre_init_hook",
}
