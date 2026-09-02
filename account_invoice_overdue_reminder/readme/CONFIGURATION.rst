You should increase the **transient_age_limit** (default value = 1, which means 1 hour) in the Odoo server config file: for example, you can set it to 12 (12 hours). The value must be superior to the duration of the invoicing reminder wizard from the start screen to the end.

Go to the menu *Invoicing > Configuration > Settings* then go to the section *Overdue Invoice Reminder*: you will be able to configure if you want to attach the overdue invoice to the reminder emails and set default values for some parameters.

Then, go to the menu *Settings > Technical > E-mail > Templates* and search for the mail template *Overdue Invoice Reminder*. You can edit the subject and the body of this email template. If you are in a multi-lang setup, don't forget to also update the translations.

Go to the menu *Invoicing > Configuration > Management > Invoice Reminder Results* and customize the list of entries.

If `py3o <https://py3otemplate.readthedocs.io/>`_ is your favorite reporting engine for Odoo (with the module *report_py3o* of the project `OCA/reporting-engine <https://github.com/OCA/reporting-engine>`_), you can use the sample py3o report for the overdue reminder letter available in the module *account_invoice_overdue_reminder_py3o*  of Akretion's `py3o report templates <https://github.com/akretion/odoo-py3o-report-templates/>`_ project.
