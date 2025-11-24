This module extends customer credit management by introducing an
automatic credit check based on the average age of all open customer
invoices.

## Key Features

- Adds the following fields to partners:
  - **Apply credit limit validation** — enables or disables checks.
  - **Credit Limit (Days)** — maximum allowed average invoice age.
  - **Average Credit Days** — computed field representing the average age
    of outstanding posted customer invoices.

- Enhances **Sale Order** confirmation:
  - Blocks confirmation when:
    - The user is *not* in the **Credit Manager** group,
    - The partner has validation enabled,
    - The partner’s average invoice age exceeds the configured limit.
  - Shows a detailed list of open invoices when blocking.

- Provides a **Credit Manager** group to bypass the rules.

This module helps organizations enforce stricter credit control before
allowing further sales to customers with aged outstanding invoices.
