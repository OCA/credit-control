# Copyright 2012-2017 Camptocamp SA
# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2020 Manuel Calero - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

CHANNEL_STATES = [("queued", "Queued"), ("sent", "Done"), ("error", "Error")]


class CreditControlLine(models.Model):
    """A credit control line describes an amount due by a customer
    for a due date.

    A line is created once the due date of the payment is exceeded.
    It is created in "draft" and some actions are available (send by email,
    print, ...)
    """

    _name = "credit.control.line"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "credit.control.channel.mixin",
    ]
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
    # editable in draft only, like the other fields copied from the level
    use_channel_letter = fields.Boolean(
        readonly=True, states={"draft": [("readonly", False)]}
    )
    use_channel_email = fields.Boolean(
        readonly=True, states={"draft": [("readonly", False)]}
    )
    use_channel_phone = fields.Boolean(
        readonly=True, states={"draft": [("readonly", False)]}
    )
    # one state per channel sent automatically: 2 channels can finish at
    # different times (e.g. email and SMS), each one keeps its own result
    state_channel_letter = fields.Selection(
        selection=CHANNEL_STATES, string="Letter status", readonly=True, copy=False
    )
    state_channel_email = fields.Selection(
        selection=CHANNEL_STATES, string="Email status", readonly=True, copy=False
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
        partner = move_line.partner_id
        channel_values = level._get_channel_values()
        # Fallback to letter
        if channel_values["use_channel_email"] and partner and not partner.email:
            channel_values.update(use_channel_email=False, use_channel_letter=True)
        data = default_lines_vals.copy()
        data.update(channel_values)
        data.update(
            {
                "date": controlling_date,
                "date_due": move_line.date_maturity,
                "state": "draft",
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

    def _run_channel_action(self, channels=None):
        """Send the lines in "To Do" on each of their channels.

        The lines are first grouped into communications (one per partner,
        level, currency, company and set of channels). Then, for each channel,
        the lines having this channel are given to ``_run_channel_action_<channel>``.
        Manual channels (see ``_get_manual_channels``) are skipped.

        :param channels: channel keys to run, all channels if not set
        :return: the first action returned by a channel (e.g. letter report)
        """
        manual_channels = self._get_manual_channels()
        channels = [
            channel
            for channel in self._get_channels()
            if channel not in manual_channels and (not channels or channel in channels)
        ]
        lines_per_channel = {
            channel: self.filtered(
                lambda line, channel=channel: line.state == "to_be_sent"
                and line._is_channel_to_send(channel)
            )
            for channel in channels
        }
        lines = self.browse().union(*lines_per_channel.values())
        if not lines:
            return None
        # a line already sent on another channel keeps its communication:
        # the result of its email is reported to the lines of this communication
        self.env["credit.control.communication"]._generate_comm_from_credit_lines(
            lines.filtered(lambda line: not line.communication_id)
        )
        action = None
        for channel, channel_lines in lines_per_channel.items():
            if not channel_lines:
                continue
            channel_action = getattr(channel_lines, f"_run_channel_action_{channel}")()
            action = action or channel_action
        return action

    def _is_channel_to_send(self, channel):
        """The line uses the channel and was not sent on it yet (or failed)."""
        self.ensure_one()
        return self[f"use_channel_{channel}"] and self[f"state_channel_{channel}"] in (
            False,
            "error",
        )

    def _set_channel_state(self, channel, state):
        """Write the state of one channel, then the line state from all channels."""
        self.write({f"state_channel_{channel}": state})
        for line in self:
            new_state = line._get_state_from_channels()
            if new_state and new_state != line.state:
                line.state = new_state

    def _get_state_from_channels(self):
        """Return the line state from the states of its channels.

        * a channel in error: the line is in error,
        * a channel not sent yet (or a manual channel): the line stays as is,
        * a channel queued: the line is queued,
        * all channels done: the line is done.
        """
        self.ensure_one()
        manual_channels = self._get_manual_channels()
        states = {
            channel: self[f"state_channel_{channel}"]
            if channel not in manual_channels
            else False
            for channel in self._get_channels()
            if self[f"use_channel_{channel}"]
        }
        if "error" in states.values():
            return "email_error" if states.get("email") == "error" else "error"
        if not all(states.values()):
            return None
        if "queued" in states.values():
            return "queued"
        return "sent"

    def _run_channel_action_letter(self):
        """Print the letters of the communications and mark the lines as done."""
        self._set_channel_state("letter", "sent")
        return self.communication_id._print_letters()

    def _run_channel_action_email(self):
        """Queue the emails of the communications.

        The lines are marked as done or in error when the email is sent
        (see ``mail.mail._postprocess_sent_message``).
        """
        self._set_channel_state("email", "queued")
        self.communication_id._generate_emails()

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
