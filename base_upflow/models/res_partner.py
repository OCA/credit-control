# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class Partner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "upflow.mixin"]

    upflow_position_id = fields.Many2one(
        "res.partner.upflow.position",
        string="Position (Upflow)",
        help="Position of the contact in the company",
    )
    main_contact_id = fields.Many2one(
        comodel_name="res.partner",
        string="Main contact",
        domain="[('parent_id', '=', id),('email', '!=', False)]",
    )

    def _prepare_customer_custom_field_payloads(self):
        """Return a list of custom fields to be send in customer payloads:

        `id`: upflow uuid the custom field reference
        `value`: the value of the custom field for the current customer
        "customFields": [
            {
                "id": "00a70b35-2be3-4c43-aefb-397190134655",
                "value": None,
            }
        ],
        """
        return []

    def get_upflow_api_post_customers_payload(self):
        customer_company = self.commercial_partner_id
        payload = customer_company.prepare_base_payload()
        payload.update(
            {
                "name": customer_company.name,
                "vatNumber": customer_company.vat or "",
                # "accountingRef": "UPFL",
                "externalId": str(customer_company.id),
                # "accountManagerId": "00a70b35-2be3-4c43-aefb-397190134655",
                # "dunningPlanId": "7a6c91dc-3580-4c43-aefb-397190134655",
                "address": {
                    "address": (
                        f"{customer_company.street or ''} "
                        f"{customer_company.street2 or ''}".strip()
                    ),
                    "zipcode": customer_company.zip or "",
                    "city": customer_company.city or "",
                    "state": customer_company.state_id.name or "",
                    "country": customer_company.country_id.name or "",
                },
                # "parent": {
                #     "id": "00a70b35-2be3-4c43-aefb-397190134655",
                #     "externalId": "1a2c3b",
                # },
                # "paymentMethods": {
                #     "card": {"enabled": False},
                #     "check": {"enabled": False},
                #     "achDebit": {"enabled": False},
                #     "sepaDebit": {"enabled": False},
                #     "goCardless": {"enabled": False},
                #     "wireTransfer": {
                #         "enabled": False,
                #         "bankAccount": {"id": "00a70b35-2be3-4c43-aefb-397190134655"},
                #         "bankAccounts": [{"id": "00a70b35-2be3-4c43-aefb-397190134655"}],
                #     },
                # },
                "customFields": customer_company._prepare_customer_custom_field_payloads(),
                "contacts": [
                    contact.get_upflow_api_post_contacts_payload()
                    for contact in customer_company.child_ids
                    if contact.email
                ],
            }
        )
        return payload

    def get_upflow_api_post_contacts_payload(self):
        payload = self.prepare_base_payload()
        payload.update(
            {
                "firstName": self.name,
                # "lastName": "",
                "phone": self.mobile or "",
                "email": self.email,
                "externalId": str(self.id),
                "isMain": self.commercial_partner_id
                and self.commercial_partner_id.main_contact_id == self,
                # "id": "00a70b35-2be3-4c43-aefb-397190134655",
            }
        )
        if self.upflow_position_id:
            payload["position"] = self.upflow_position_id.code
        return payload
