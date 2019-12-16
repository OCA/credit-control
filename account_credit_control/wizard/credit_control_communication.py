# Copyright 2012-2017 Camptocamp SA
# Copyright 2017 Okia SPRL (https://okia.be)
# Copyright 2018 Access Bookings Ltd (https://accessbookings.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class CreditControlCommunication(models.TransientModel):
    """Shell class used to provide a base model to email template and reporting
    If used this approach in version 7 a browse record
    will exist even if not saved

    """
    _name = "credit.control.communication"
    _description = "credit control communication"
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        required=True,
    )
    current_policy_level = fields.Many2one(
        comodel_name='credit.control.policy.level',
        string='Level',
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
    )
    credit_control_line_ids = fields.Many2many(
        comodel_name='credit.control.line',
        rel='comm_credit_rel',
        string='Credit Lines',
    )
    contact_address = fields.Many2one(
        comodel_name='res.partner',
        readonly=True,
    )
    report_date = fields.Date(
        default=lambda self: fields.Date.context_today(self),
    )

    @api.model
    def _get_company(self):
        company_obj = self.env['res.company']
        return company_obj._company_default_get('credit.control.policy')

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self._get_company(),
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        default=lambda self: self.env.user,
        string='User',
    )
    total_invoiced = fields.Float(
        compute='_compute_total',
    )
    total_due = fields.Float(
        compute='_compute_total',
    )

    @api.model
    def _get_total(self):
        amount_field = 'credit_control_line_ids.amount_due'
        return sum(self.mapped(amount_field))

    @api.model
    def _get_total_due(self):
        balance_field = 'credit_control_line_ids.balance_due'
        return sum(self.mapped(balance_field))

    @api.multi
    @api.depends('credit_control_line_ids',
                 'credit_control_line_ids.amount_due',
                 'credit_control_line_ids.balance_due')
    def _compute_total(self):
        for communication in self:
            communication.total_invoiced = communication._get_total()
            communication.total_due = communication._get_total_due()

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('partner_id'):
                # the computed field does not work in TransientModel,
                # just set a value on creation
                partner_id = vals['partner_id']
                vals['contact_address'] = \
                    self._get_contact_address(partner_id).id
        return super(CreditControlCommunication, self).create(vals_list)

    @api.multi
    def get_email(self):
        """ Return a valid email for customer """
        self.ensure_one()
        contact = self.contact_address
        email = contact.email
        if not email and contact.commercial_partner_id.email:
            email = contact.commercial_partner_id.email
        return email

    @api.multi
    @api.returns('res.partner')
    def get_contact_address(self):
        """ Compatibility method, please use the contact_address field """
        self.ensure_one()
        return self.contact_address

    @api.model
    @api.returns('res.partner')
    def _get_contact_address(self, partner_id):
        partner_obj = self.env['res.partner']
        partner = partner_obj.browse(partner_id)
        add_ids = partner.address_get(adr_pref=['invoice']) or {}
        add_id = add_ids['invoice']
        return partner_obj.browse(add_id)

    @api.model
    def _group_lines(self, lines):
        ordered_lines = lines.search(
            [("id", "in", lines.ids)],
            order="partner_id, currency_id, policy_id, state, level DESC",
        )
        prev_group = None
        prev_policy_level = None
        group_lines = self.env["credit.control.line"].browse()
        for line in ordered_lines:
            group = (line.partner_id, line.currency_id, line.policy_id)
            policy_level = line.policy_level_id
            if prev_group and (
                group != prev_group
                or (
                    not line.policy_id.auto_process_lower_levels and
                    policy_level != prev_policy_level
                )
            ):
                yield (
                    group_lines[0].partner_id,
                    group_lines[0].currency_id,
                    group_lines[0].policy_level_id,
                    group_lines,
                )
                group_lines = self.env["credit.control.line"].browse()
            if line not in group_lines:
                group_lines |= line.get_lower_related_lines() or line
            prev_group = group
            prev_policy_level = policy_level
        yield (
            group_lines[0].partner_id,
            group_lines[0].currency_id,
            group_lines[0].policy_level_id,
            group_lines,
        )

    @api.model
    def _generate_comm_from_credit_lines(self, lines):
        """ Aggregate credit control line by partner, level, and currency
        It also generate a communication object per aggregation.
        """
        comms = self.browse()
        if not lines:
            return comms
        company_currency = self.env.user.company_id.currency_id
        datas = []
        for (
            partner_id,
            currency_id,
            policy_level_id,
            grouped_lines,
        ) in self._group_lines(lines):
            data = {}
            data['credit_control_line_ids'] = [(6, 0, grouped_lines.ids)]
            data['partner_id'] = partner_id.id
            data['current_policy_level'] = policy_level_id.id
            data['currency_id'] = currency_id.id or company_currency.id
            datas.append(data)
        comms = self.create(datas)
        return comms

    @api.multi
    @api.returns('mail.mail')
    def _generate_emails(self):
        """ Generate email message using template related to level """
        emails = self.env['mail.mail']
        required_fields = [
            'subject',
            'body_html',
            'email_from',
            'email_to',
        ]
        for comm in self:
            template = comm.current_policy_level.email_template_id
            email_values = template.generate_email(comm.id)
            email_values['message_type'] = 'email'
            # model is Transient record (self) removed periodically so no point
            # of storing res_id
            email_values.pop('model', None)
            email_values.pop('res_id', None)
            # Remove when mail.template returns correct format attachments
            attachment_list = email_values.pop('attachments', None)
            email = emails.create(email_values)

            state = 'sent'
            # The mail will not be send, however it will be in the pool, in an
            # error state. So we create it, link it with
            # the credit control line
            # and put this latter in a `email_error` state we not that we have
            # a problem with the email
            if not all(email_values.get(field) for field in required_fields):
                state = 'email_error'
            comm.credit_control_line_ids.write({
                'mail_message_id': email.id,
                'state': state,
            })
            email.attachment_ids = [(0, 0, {
                'name': att[0],
                'datas': att[1],
                'datas_fname': att[0],
                'res_model': 'mail.mail',
                'res_id': email.id,
                'type': 'binary',
            }) for att in attachment_list]
            emails |= email
        return emails

    @api.multi
    @api.returns('credit.control.line')
    def _mark_credit_line_as_sent(self):
        lines = self.env['credit.control.line']
        for comm in self:
            lines |= comm.credit_control_line_ids

        lines.write({'state': 'sent'})
        return lines
