This Odoo module is designed to send overdue invoice reminders to customers. It handles reminders by e-mail, letter and phone.

This module is an alternative to the OCA module *account_credit_control*. Why another module for invoice reminders ? Because the module *account_credit_control* is quite complex (we experienced that some users find it too complex and eventually stop using it) and its interface is designed to send massive volume of reminders.

This module has been designed from the start with the following priorities:

* **keep control**: you must keep tight control on the overdue invoice reminders that you send. Overdue invoice reminders are part of the communication with your customers, and this is very important to keep a good relation with your customers.
* **usability**: the module is easy to configure and easy to use.
* **no accounting skills needed**: the module can be used by users without accounting skills. It can even be used by salesman!
* **multi-currency**: if you invoice your customer in another currency that your company currency, the invoice reminders only mention the currency of the invoices. And if you invoice a customer with different currencies, the reminder is clear and easy-to-understand by your customer, with a total residual per currency.
* **multi-channel**: supports overdue invoice reminders by e-mail (default), phone and letter.
* **simplicity**: for the developers, the code is small and easy to understand.

The specifications written before starting the development of this module are written in this `document <https://docs.google.com/document/d/1JIIAP5QsItbJ1zLiaGHuR0RAQplEGv3diOl-d4mS__I/edit?usp=sharing>`_ (in French).

The module has one important limitation: it sends a reminder for an invoice when it has past it's *Due Date* (which is in fact the *Final Due Date*): if the invoice has a payment term with several lines, it won't send a reminder before the last term is overdue.

An overdue reminder for a customer always include all the overdue invoices of that customer.

The module supports a clever per-invoice reminder counter mechanism:

* the reminder counter is a property of an invoice,
* the reminder counter of each overdue invoice is incremented when sending a reminder by email or by post. It is not incremented for reminders by phone.
* in an email or a letter, the subject will be *Overdue invoice reminder n°N* where N is the maximum value of the counter of the overdue invoices plus one.

There are two user interfaces to send reminders:

* the **one-by-one** interface, which displays one screen for each customer that has overdue invoices, one after the other. You should use this interface when you have a reasonable volume of reminders to send (less than 100 overdue reminders for example). It gives you a tight control on the reminders and the possibility to easily and rapidly customize the reminder e-mails.
* the **mass** interface, which displays a list view of all customers that have overdue invoices, and you can process several reminders at the same time (via the *Actions* menu).

This video tutorial in English will show you how to configure and use the module: `Youtube link <https://www.youtube.com/watch?v=MaOoVAi7Tc0>`_.
