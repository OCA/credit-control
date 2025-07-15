# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class CreditControlLine(models.Model):
    _inherit = "credit.control.line"

    aggregation = fields.Selection(
        selection=[
            ("no", "No aggregation"),
            ("low", "Low level"),
            ("highest", "Highest level"),
        ],
        help="`No aggregation` lines are not automatically aggregated "
        "with other lines.\n"
        "'Low level' lines are attached under higher level lines.\n"
        "'Highest level' indicates that all 'Low level' lines for this "
        "line's partner-policy combination will be attached to it.",
        default="no",
        readonly=True,
    )

    def _update_aggregation(self, exclude_ids=None):
        self.ensure_one()
        if not self.policy_id.aggregate_levels:
            return
        highest_related_line = self._get_highest_related_line(exclude_ids=exclude_ids)
        highest_related_line.write({"aggregation": "highest"})
        self._get_related_lines(
            exclude_ids=((exclude_ids or []) + highest_related_line.ids)
        ).write({"aggregation": "low"})

    def unlink(self):
        for line in self:
            line._update_aggregation(exclude_ids=line.ids)
        return super().unlink()

    def write(self, values):
        res = super().write(values)
        for line in self:
            if "state" in values and values.get("state") == "sent":
                line.write({"aggregation": "no"})
            if "aggregation" not in values:
                line._update_aggregation()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.state == "sent":
                line.write({"aggregation": "no"})
            else:
                line._update_aggregation()
        return lines

    def _get_highest_related_line(self, exclude_ids=None):
        self.ensure_one()
        return self._get_related_lines(exclude_ids=exclude_ids, limit=1)

    def _get_related_lines_domain(self, exclude_ids=None, level=None):
        domain = [
            ("partner_id", "=", self.partner_id.id),
            ("currency_id", "=", self.currency_id.id),
            ("policy_id", "=", self.policy_id.id),
            ("state", "in", ("draft", "to_be_sent")),
        ]
        if exclude_ids:
            domain.append(("id", "not in", exclude_ids))
        if level:
            domain.append(("level", "<=", level))
        return domain

    def _get_related_lines(self, exclude_ids=None, limit=None, level=None):
        """
        Return lines from the same group if grouped
        (ie with same partner, policy and currency).

        The most important line (ie the one to display to the user)
        is the first one of the returned recordset.
        """
        self.ensure_one()
        if self.policy_id.aggregate_levels:
            return self.search(
                self._get_related_lines_domain(exclude_ids, level),
                limit=limit,
                order="level DESC, date_due ASC",
            )
        else:
            return self

    def _get_lower_related_lines(self):
        """
        Return lines that will receive the same treatment
        (ie lines of lower level from the same group if grouped).
        """
        self.ensure_one()
        if self.policy_id.aggregate_levels:
            return self._get_related_lines(level=self.level)
        else:
            return self

    def button_schedule_activity(self):
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_res_id": self.ids[0],
                "default_res_model": self._name,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Schedule activity"),
            "res_model": "mail.activity",
            "view_type": "form",
            "view_mode": "form",
            "res_id": self.activity_ids and self.activity_ids.ids[0] or False,
            "views": [[False, "form"]],
            "context": ctx,
            "target": "new",
        }

    def button_credit_control_line_form(self):
        self.ensure_one()
        action = self.env.ref("account_credit_control.credit_control_line_action")
        form = self.env.ref("account_credit_control.credit_control_line_form")
        action = action.read()[0]
        action["views"] = [(form.id, "form")]
        action["res_id"] = self.id
        return action

    def act_show_aggregated_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Credit Control Lines"),
            "res_model": "credit.control.line",
            "domain": [("id", "in", self._get_lower_related_lines().ids)],
            "view_mode": "list,form",
            "context": self.env.context,
        }
