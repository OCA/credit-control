/*
    Copyright 2022 Jarsa
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
*/
odoo.define("pos_financial_risk.models", function (require) {
    "use strict";

    const models = require("point_of_sale.models");

    models.load_fields("res.partner", [
        "risk_exception",
        "risk_total",
        "credit_limit",
        "commercial_partner_id",
    ]);

    return models;
});
