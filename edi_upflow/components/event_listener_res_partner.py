# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from odoo.addons.component.core import Component

logger = logging.getLogger(__name__)


class ResPartnerUpflowEventListener(Component):

    _name = "res.partner.upflow.event.listener"
    _inherit = "base.upflow.event.listener"
    _apply_on = ["res.partner"]

    def on_record_create(self, partner, fields=None):
        if (
            partner.commercial_partner_id.upflow_uuid
            and partner.commercial_partner_id.upflow_edi_backend_id
        ):
            self._create_and_generate_upflow_exchange_record(
                partner.commercial_partner_id.upflow_edi_backend_id,
                "upflow_post_customers",
                partner.commercial_partner_id,
            )

    def on_record_write(self, partner, fields=None):
        update_contact_fields = set(self.env["res.partner"].get_upflow_contact_fields())
        update_customer_fields = set(
            self.env["res.partner"].get_upflow_customer_fields()
        )
        update_contact_fields_from_customer = set(
            self.env["res.partner"].get_upflow_customer_fields_to_update_contacts()
        )
        update_customer_fields_from_contact = set(
            self.env["res.partner"].get_upflow_contact_fields_to_update_customer()
        )
        if (
            not partner.commercial_partner_id.upflow_uuid
            or not partner.commercial_partner_id.upflow_edi_backend_id
        ):
            return
        # Creating/Updating customer and Creating contact
        if (
            (not partner.parent_id and set(fields) & update_customer_fields)
            or (partner.parent_id and set(fields) & update_customer_fields_from_contact)
            or (
                partner.parent_id
                and not partner.upflow_uuid
                and set(fields) & update_contact_fields
            )
        ):
            self._create_and_generate_upflow_exchange_record(
                partner.commercial_partner_id.upflow_edi_backend_id,
                "upflow_post_customers",
                partner.commercial_partner_id,
            )
        # Updating contact
        if (
            partner.upflow_uuid
            and partner.parent_id
            and set(fields) & update_contact_fields
        ):
            self._create_and_generate_upflow_exchange_record(
                partner.commercial_partner_id.upflow_edi_backend_id,
                "upflow_put_contacts",
                partner,
            )
        if not partner.parent_id:
            contact_to_update = self.env["res.partner"].browse()
            for child in {  # This only works for many2one fields
                partner[element]
                for element in set(fields) & update_contact_fields_from_customer
            }:
                contact_to_update |= child
            for contact in list(set(contact_to_update)):
                self._create_and_generate_upflow_exchange_record(
                    partner.commercial_partner_id.upflow_edi_backend_id,
                    "upflow_put_contacts",
                    contact,
                )

    def on_record_unlink(self, partner):
        # TODO: manage removing customer (not only a contact)
        if (
            partner.commercial_partner_id.upflow_uuid
            and partner.commercial_partner_id.upflow_edi_backend_id
        ):
            self._create_and_generate_upflow_exchange_record(
                partner.commercial_partner_id.upflow_edi_backend_id,
                "upflow_post_customers",
                partner.commercial_partner_id,
            )
