When ``account_financial_risk`` evaluates a partner's credit risk it restricts
the query to the companies visible in the current user's session. Because the
**credit limit** itself is a single global value on the partner, the per-company
filtering creates a gap: a partner owing amounts across multiple companies may
never trigger a risk exception when viewed from any single company.

This module removes the company filter so that risk totals always reflect the
partner's **full exposure across every company** in the database. The
computation runs with elevated privileges (``sudo``) to ensure cross-company
journal items and sale order lines are visible regardless of the current user's
company access.

No configuration is required — installing the module is sufficient.
