from odoo import models, exceptions, _


class Template(models.Model):
    _inherit = "mail.template"

    def unlink(self):
        reminder = self.env.ref(
            "account_invoice_overdue_reminder.overdue_invoice_reminder_mail_template")
        for template in self:
            if template.id == reminder.id:
                raise exceptions.UserError(_(
                    "You can't delete Overdue Invoice Reminder, it is needed by the"
                    " module"
                ))
        return super(Template, self).unlink()
