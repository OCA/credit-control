This module introduces partner-level configuration options that determine
whether a customer is allowed to confirm a sale order based on the
average age of their open invoices.

To configure the feature:

1. Go to **Contacts → Customers** and open any customer record.
2. Under the **Credit Control** section, configure:
   - **Apply credit limit validation**  
     Enable this option to activate the credit rules for this customer.
   - **Credit Limit (Days)**  
     Set the maximum allowed average age (in days) of all posted customer invoices
     that still have a residual amount.
3. Ensure that the **Credit Manager** group contains the users
   who should be allowed to bypass this credit check.
