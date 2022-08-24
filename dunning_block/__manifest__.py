# Copyright 2022 Solvti (http://www.solvti.pl).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Dunning Block",
    "summary": "The dunning block temporarily suspends the dunning process",
    "version": "15.0.1.0.0",
    "author": "Jakub Wiselka - Solvti, Odoo Community Association (OCA)",
    "category": "Finance",
    "website": "https://github.com/OCA/credit-control",
    "depends": ["account_credit_control"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "data/cron_data.xml",
        "wizard/dunning_block_wizard_view.xml",
        "views/account_move.xml",
        "views/dunning_block_reason.xml",
    ],
    "installable": True,
}
