# Copyright 2026 360ERP (<https://www.360erp.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Unset email template's use_default_to on new installations in 19.0.

    The default changed in https://github.com/odoo/odoo/commit/5e88a2f1b545,
    but this is not a suitable setting for templates that want to see their
    `partner_to` evaluated.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    xmlid = "account_credit_control.email_template_credit_control_base"
    template = env.ref(xmlid, raise_if_not_found=False)
    if template and template.use_default_to:
        _logger.info("Disabling 'Default Recipients' on mail template %s", xmlid)
        template.use_default_to = False
