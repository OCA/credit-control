# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class CreditControlChannelMixin(models.AbstractModel):
    """Channels used to send a credit control reminder.

    Shared by the policy level (configuration) and the credit control line
    (copied from the level, editable in draft).

    To add a channel ``K``, a module must:

    * add a boolean field ``use_channel_K`` on this mixin,
    * add ``K`` to the list returned by ``_get_channels``.
    """

    _name = "credit.control.channel.mixin"
    _description = "Credit Control Channels"

    use_channel_letter = fields.Boolean(string="Letter")
    use_channel_email = fields.Boolean(string="Email")
    use_channel_phone = fields.Boolean(string="Phone")

    @api.model
    def _get_channels(self):
        """Return the channel keys."""
        return ["letter", "email", "phone"]

    @api.model
    def _get_channel_field_names(self):
        return [f"use_channel_{channel}" for channel in self._get_channels()]

    def _get_channel_values(self):
        """Return the channel booleans of the record, as a dict of values."""
        self.ensure_one()
        return {fname: self[fname] for fname in self._get_channel_field_names()}
