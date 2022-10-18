/*
    Copyright 2022 Jarsa
    License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
*/
odoo.define("pos_financial_risk.PaymentScreen", function (require) {
    "use strict";

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");

    const PosDeResPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            // @Override
            // eslint-disable-next-line no-unused-vars
            async validateOrder(isForceValidate) {
                var commercialPartnerId =
                    this.currentOrder.get_client().commercial_partner_id[0];
                var customer =
                    this.currentOrder.pos.db.get_partner_by_id(commercialPartnerId);
                var custPaymentLines = this.paymentLines.filter(
                    (payment) => payment.payment_method.type === "pay_later"
                );
                var custAmount = custPaymentLines
                    .map((line) => line.amount)
                    .filter((x) => x > 0)
                    .reduce((prev, next) => prev + next, 0);
                if (
                    customer.risk_exception ||
                    customer.risk_total + custAmount > customer.credit_limit
                ) {
                    this.showPopup("ErrorPopup", {
                        title: this.env._t("Financial Risk Exceeded"),
                        body: this.env._t(
                            "The amount exceeds the credit limit of the customer. Please select another payment method."
                        ),
                    });
                    return false;
                }
                await super.validateOrder(...arguments);
            }
        };

    Registries.Component.extend(PaymentScreen, PosDeResPaymentScreen);

    return PosDeResPaymentScreen;
});
