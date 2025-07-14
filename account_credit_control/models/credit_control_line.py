# Copyright 2012-2017 Camptocamp SA
# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .credit_control_policy import CHANNEL_LIST


class CreditControlLine(models.Model):
    """A credit control line describes an amount due by a customer
    for a due date.

    A line is created once the due date of the payment is exceeded.
    It is created in "draft" and some actions are available (send by email,
    print, ...)
    """

    _name = "credit.control.line"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "A credit control line"
    _rec_name = "id"
    _order = "date DESC"

    date = fields.Date(
        string="Controlling date",
        required=True,
        index=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    # maturity date of related move line we do not use
    # a related field in order to
    # allow manual changes
    date_due = fields.Date(
        string="Due date",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_entry = fields.Date(
        string="Entry date", related="move_line_id.date", store=True
    )
    date_sent = fields.Date(
        string="Reminded date", readonly=True, states={"draft": [("readonly", False)]}
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("ignored", "Ignored"),
            ("queued", "Queued"),
            ("to_be_sent", "To Do"),
            ("sent", "Done"),
            ("error", "Error"),
            ("email_error", "Emailing Error"),
        ],
        required=True,
        readonly=True,
        default="draft",
        tracking=True,
        help="Draft lines need to be triaged.\n"
        "Ignored lines are lines for which we do "
        "not want to send something.\n"
        "Draft and ignored lines will be "
        "generated again on the next run.",
    )
    channel = fields.Selection(
        selection=CHANNEL_LIST,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    invoice_id = fields.Many2one(comodel_name="account.move", readonly=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Commercial Entity",
        compute_sudo=True,
        related="partner_id.commercial_partner_id",
        index=True,
        store=True,
    )
    communication_id = fields.Many2one(
        comodel_name="credit.control.communication",
        string="Communication process",
        help="Credit control communication process where this line belongs",
    )
    amount_due = fields.Float(
        string="Due Amount Tax incl.", required=True, readonly=True
    )
    balance_due = fields.Float(string="Due balance", required=True, readonly=True)
    move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Move line",
        required=True,
        readonly=True,
        index=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account", related="move_line_id.account_id", store=True
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency", related="move_line_id.currency_id", store=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company", related="move_line_id.company_id", store=True
    )
    # we can allow a manual change of policy in draft state
    policy_level_id = fields.Many2one(
        comodel_name="credit.control.policy.level",
        string="Overdue Level",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    policy_id = fields.Many2one(
        comodel_name="credit.control.policy",
        related="policy_level_id.policy_id",
        store=True,
    )
    level = fields.Integer(
        related="policy_level_id.level", group_operator="max", store=True
    )
    manually_overridden = fields.Boolean()
    run_id = fields.Many2one(comodel_name="credit.control.run", string="Source")
    manual_followup = fields.Boolean()
    partner_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        # Use compute instead of related because it raises access error if the
        # user is in other company even using related_sudo
        compute="_compute_partner_user_id",
        store=True,
    )

    @api.depends("partner_id.user_id")
    def _compute_partner_user_id(self):
        for line in self:
            line.partner_user_id = line.partner_id.user_id

    @api.model
    def _prepare_from_move_line(
        self, move_line, level, controlling_date, open_amount, default_lines_vals
    ):
        """Create credit control line"""
        channel = level.channel
        partner = move_line.partner_id
        # Fallback to letter
        if channel == "email" and partner and not partner.email:
            channel = "letter"
        data = default_lines_vals.copy()
        data.update(
            {
                "date": controlling_date,
                "date_due": move_line.date_maturity,
                "state": "draft",
                "channel": channel,
                "invoice_id": (move_line.move_id.id if move_line.move_id else False),
                "partner_id": partner.id,
                "amount_due": (
                    move_line.amount_currency or move_line.debit or move_line.credit
                ),
                "balance_due": open_amount,
                "policy_level_id": level.id,
                "move_line_id": move_line.id,
                "manual_followup": partner.manual_followup,
            }
        )
        return data

    @api.model
    def create_or_update_from_mv_lines(
        self,
        lines,
        level,
        controlling_date,
        company,
        check_tolerance=True,
        default_lines_vals=None,
    ):
        """Create or update line based on levels

        if check_tolerance is true credit line will not be
        created if open amount is too small.
        eg. we do not want to send a letter for 10 cents
        of open amount.

        :param lines: move.line id recordset
        :param level: credit.control.policy.level record
        :param controlling_date: date string of the credit controlling date.
                                 Generally it should be the same
                                 as create date
        :param company: res.company
        :param default_lines_vals: default values to create new credit control
                                   lines with
        :param check_tolerance: boolean if True credit line
                                will not be generated if open amount
                                is smaller than company defined
                                tolerance

        :returns: recordset of created credit lines
        """
        currency_obj = self.env["res.currency"]
        currencies = currency_obj.search([])

        tolerance = {}
        tolerance_base = company.credit_control_tolerance
        user_currency = company.currency_id
        for currency in currencies:
            tolerance[currency.id] = currency._convert(
                tolerance_base,
                user_currency,
                company,
                controlling_date or fields.Date.today(),
            )

        lines_to_create = []
        lines_to_write = self.browse()
        new_lines = self.browse()
        for move_line in lines:
            ml_currency = move_line.currency_id
            if ml_currency and ml_currency != user_currency:
                open_amount = move_line.amount_residual_currency
            else:
                open_amount = move_line.amount_residual
            cur_tolerance = tolerance.get(move_line.currency_id.id, tolerance_base)
            if check_tolerance and open_amount < cur_tolerance:
                continue
            vals = self._prepare_from_move_line(
                move_line,
                level,
                controlling_date,
                open_amount,
                default_lines_vals or {},
            )
            lines_to_create.append(vals)

            # when we have lines generated earlier in draft
            # or to_be_sent on the same level, it means that
            # we have left them, so they are to be considered
            # as ignored
            previous_drafts = self.search(
                [
                    ("move_line_id", "=", move_line.id),
                    ("policy_level_id", "=", level.id),
                    ("state", "in", ["draft", "to_be_sent"]),
                ]
            )
            lines_to_write = lines_to_write | previous_drafts

        new_lines = self.create(lines_to_create)
        lines_to_write.write({"state": "ignored"})

        return new_lines

    def unlink(self):
        for line in self:
            if line.state != "draft":
                raise UserError(
                    _(
                        "You are not allowed to delete a credit control "
                        "line that is not in draft state."
                    )
                )
        return super().unlink()

    def write(self, values):
        res = super().write(values)
        if "manual_followup" in values:
            self.partner_id.write({"manual_followup": values.get("manual_followup")})
        return res

    def button_schedule_activity(self):
        ctx = self.env.context.copy()
        ctx.update({"default_res_id": self.ids[0], "default_res_model": self._name})
        return {
            "type": "ir.actions.act_window",
            "name": _("Schedule activity"),
            "res_model": "mail.activity",
            "binding_view_types": "form",
            "view_mode": "form",
            "res_id": self.activity_ids and self.activity_ids.ids[0] or False,
            "views": [[False, "form"]],
            "context": ctx,
            "target": "new",
        }

    def button_credit_control_line_form(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account_credit_control.credit_control_line_action"
        )
        form = self.env.ref("account_credit_control.credit_control_line_form")
        action["views"] = [(form.id, "form")]
        action["res_id"] = self.id
        return action
