# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Base Upflow.io",
    "summary": "Base module to generate Upflow.io API payloads format from odoo object",
    "version": "14.0.1.1.0",
    "development_status": "Alpha",
    "category": "EDI",
    "website": "https://github.com/OCA/credit-control",
    "author": "Pierre Verkest, Odoo Community Association (OCA)",
    "maintainers": ["petrus-v"],
    "license": "AGPL-3",
    "application": True,
    "depends": [
        "contacts",
        "account",
    ],
    # I'm not sure for test depencies we shoud declared them here
    "external_dependencies": {"python": ["jsonschema"]},
    "data": [
        "views/account_journal.xml",
        "views/account_move.xml",
        "views/res_partner.xml",
        "views/menu.xml",
        "datas/res_partner_position.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [],
    "installable": True,
}
