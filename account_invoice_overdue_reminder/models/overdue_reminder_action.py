# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class OverdueReminderAction(models.Model):
    _name = "overdue.reminder.action"
    _description = "Overdue Reminder Action History"
    _order = "date desc, id desc"

    commercial_partner_id = fields.Many2one(
        "res.partner",
        readonly=True,
        string="Customer",
        index=True,
        domain=[("parent_id", "=", False)],
    )
    partner_id = fields.Many2one("res.partner", readonly=True, string="Contact")
    date = fields.Date(
        default=fields.Date.context_today, required=True, index=True, readonly=False
    )
    user_id = fields.Many2one(
        "res.users",
        string="Performed by",
        required=True,
        readonly=True,
        ondelete="restrict",
        default=lambda self: self.env.user,
    )
    reminder_type = fields.Selection(
        "_reminder_type_selection",
        default="mail",
        string="Type",
        required=True,
        readonly=True,
    )
    result_id = fields.Many2one(
        "overdue.reminder.result", ondelete="restrict", string="Info/Result"
    )
    result_notes = fields.Text(string="Info/Result Notes")
    mail_id = fields.Many2one("mail.mail", string="Reminder E-mail", readonly=True)
    mail_state = fields.Selection(related="mail_id.state", string="E-mail Status")
    mail_cc = fields.Char(related="mail_id.email_cc", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    reminder_count = fields.Integer(
        compute="_compute_invoice_count", store=True, string="Number of invoices"
    )
    reminder_ids = fields.One2many(
        "account.invoice.overdue.reminder", "action_id", readonly=True
    )

    @api.model
    def _reminder_type_selection(self):
        return [
            ("mail", _("E-mail")),
            ("phone", _("Phone")),
            ("post", _("Letter")),
        ]

    @api.depends("reminder_ids")
    def _compute_invoice_count(self):
        rg_res = self.env["account.invoice.overdue.reminder"].read_group(
            [("action_id", "in", self.ids), ("invoice_id", "!=", False)],
            ["action_id"],
            ["action_id"],
        )
        mapped_data = {x["action_id"][0]: x["action_id_count"] for x in rg_res}
        for rec in self:
            rec.reminder_count = mapped_data.get(rec.id, 0)

    @api.depends("commercial_partner_id", "date")
    def name_get(self):
        res = []
        for action in self:
            name = _("%s, Reminder %s") % (
                action.commercial_partner_id.display_name,
                action.date,
            )
            res.append((action.id, name))
        return res
