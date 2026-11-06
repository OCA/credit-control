Delivery, discount and reward lines are not invoiced alone: Odoo does not
set an order to invoice when only those lines are left. When the rest of the
order has nothing left to invoice, for instance because the customer finally
does not want the goods and their delivery is cancelled, those lines keep
their amount in the sales orders risk of *Sale Financial Risk* forever.

This module removes the risk of such lines when the other lines of the order
have none. An order with only such lines keeps their risk, as Odoo invoices
them.

When delivery lines are added only once the picking is done, the case
hardly happens and this module is not needed.
