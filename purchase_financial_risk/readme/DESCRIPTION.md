Extends Partner Financial Risk to manage vendor exposure in purchases.

Adds a **Purchase Risk** page on the vendor form to track and control how
much financial exposure a company has with a given supplier. The exposure
is computed from:

- Confirmed purchase orders not yet fully invoiced (uninvoiced amount).
- Vendor bills in draft or posted state that have not been fully paid.

When a purchase order is confirmed and would cause the vendor's purchase
risk to exceed the configured limit, a warning wizard is shown. Users with
the **Purchase Risk Manager** role can override the block and confirm the
order anyway.
