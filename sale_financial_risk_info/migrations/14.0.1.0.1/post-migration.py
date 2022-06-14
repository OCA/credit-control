# Copyright 2022 Digital5 - Enrique Martín
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env["ir.config_parameter"]
    info_pattern = ICP.get_param("sale_financial_risk_info.info_pattern", False)
    if info_pattern:
        ICP.set_param(
            "sale_financial_risk_info.info_pattern",
            info_pattern.replace("{symbol}", ""),
        )
