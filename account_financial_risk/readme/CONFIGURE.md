To configure this module, you need to:

1.  Go to User and set group User or Manager Financial Risk
2.  Go to *Invoicing/Accounting \> Configuration \> Settings \>
    Accounting*
3.  In the *Customer Payments* section, fill *Maturity Margin* for
    setting the number of days to last after the due date to consider an
    invoice as unpaid.

(Optional) To display credit information in the customer portal,
go to *Invoicing > Configuration > Settings > Financial Risk* and activate
**Show credit information in portal**.

Credit information can be displayed on the portal if it is enabled globally,
and can be disabled individually for certain contacts.

Odoo core has its own credit limit warning (*Invoicing/Accounting >
Configuration > Settings > Sales Credit Limit*). It shows a banner on draft
invoices and sales orders using the same partner *Credit Limit*, but with
other amounts: the total receivable plus the delivered and not invoiced
sales orders of the user's main company. To show only the financial risk
amounts, disable *Sales Credit Limit* in each company: Odoo then skips the
banner computation. With this module the partner credit limit is edited in
the *Financial Risk* tab, the core *Credit Limits* group of the *Invoicing*
tab is hidden, and the company default credit limit is set in the
*Financial Risk* settings block while *Sales Credit Limit* is disabled.
