This module is used to prevent confirming a Sale Order when a customer's
open invoices have an average age higher than a configured limit.

### 1. Configure the Partner
1. Go to **Contacts → Customers**.
2. Open a customer.
3. Set:
   - **Apply credit limit validation** = enabled
   - **Credit Limit (Days)** = the maximum allowed average age
4. The computed **Average Credit Days** will display automatically.

### 2. Create or Review Open Invoices
1. Create customer invoices (or leave existing ones).
2. Post the invoices.
3. Ensure some invoices remain unpaid (residual > 0).

### 3. Create a Sale Order
1. Create a new Sale Order for this customer.
2. Add products and confirm.

### 4. Resulting Behavior
- If the customer exceeds the allowed average credit age:
  - **Non-Credit Manager users** → confirmation is **blocked**.
  - A popup error shows:
    - Customer name
    - Average invoice age
    - Allowed limit
    - List of open invoices with dates, residuals, and ages

- If the user belongs to **Credit Manager**, the sale confirms normally.
