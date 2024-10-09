# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "edi.exchange.consumer.mixin"]

    upflow_edi_backend_id = fields.Many2one(
        "edi.backend",
        help=(
            "Backend used to synchronised this partner to upflow. "
            "Technical field as while updating existing customer we are "
            "not able to determine which upflow backend to use. "
            "There are some limitation, a customer can't be synchronized "
            "in two different backends. "
            "A customer used by 2 different company (multi-company odoo feature) "
            "manage in two upflow organisations is not support today. "
            "So we direct link upflow backend here !"
        ),
    )

    @api.model
    def get_upflow_customer_fields(self):
        """used in order to limit the number exchange record to
        generate while communicate with upflow.io"""
        # do not add upflow_uuid to avoid send exchange twice!
        return [
            "name",
            "ref",
            "vat",
            "street",
            "street2",
            "zip",
            "city",
            "state_id",
            "country_id",
            "child_ids",
        ]

    @api.model
    def get_upflow_customer_fields_to_update_contacts(self):
        """used in order to limit the number exchange record to
        generate while communicate with upflow.io

        @return a list of Many2one fields that needed to update contacts
        """
        # do not add upflow_uuid to avoid send exchange twice!
        return [
            "main_contact_id",
        ]

    @api.model
    def get_upflow_contact_fields_to_update_customer(self):
        return ["parent_id", "commercial_partner_id"]

    @api.model
    def get_upflow_contact_fields(self):
        """used in order to limit the number exchange record to
        generate while communicate with upflow.io"""
        return [
            "name",
            "mobile",
            "email",
            "upflow_position_id",
        ]

    def write(self, vals):
        """in case a contact change from one parent to an other we needs to synchronized both

        so emit an extra on_record_write on previous parent if set (before write)
        """
        if "parent_id" in vals:
            for rec in self:
                if rec.parent_id:
                    self._event("on_record_write").notify(
                        rec.parent_id, fields=["child_ids"]
                    )
        return super().write(vals)
