
Based on OCA EDI Frameworks this modules aims to integrate
Odoo and Upflow.io.

# Trigger

Here is the list of event that generate exchange that push data to upflow:

* When account entry of the following type are posted
  out invoice / out refund / invoice payment or refund payment, then
  the customer will be synchronised if no ufpflow id present in the database.

* When full reconcile line is created it will create missing account entry if any
  (backend statement reconcile can works without account payment in odoo) and send reconcile
  info to upflow.

* any change on synchronized information to a customer or a contact will update all customers
  informations to upflow.


# Multi-company

A customer and sales accounting entries are linked to only one backend.

Backend are linked to a company, but once a customer has been synchronised
for a given backend (first sale accounting entry), next accounting entries
will be linked to the same backend (upflow organisation) what ever the current
backend set on the current company.

# Asynchrone tasks

Data are send asynchronously, according your configuration tasks can take few minutes
to be handle and send to upflow.

On each relevent form views you will see an EDI smart button
that let you check the state of the reletated exchange synchronizations.

This module is based on EDI Frameworks maintain by OCA which depends on the `queue_job`
module you should also monitor queue job tasks.
