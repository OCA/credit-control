This module extends ``sale.order.type`` to integrate with
``sale_financial_risk``.

It adds two independent behaviors to sale order types:

- Exclude orders from financial risk computation
- Allow confirmation bypass for financial risk blocking

This allows implementing flexible commercial workflows while
keeping the standard financial risk framework intact.

Features
========

- Extend ``sale.order.type`` with financial risk options
- Exclude selected order types from risk exposure computation
- Allow selected order types to bypass financial risk blocking
- Keep computation and blocking behaviors independent
- Compatible with ``sale_financial_risk``
- Compatible with multi-company environments

Design Notes
============

This module intentionally keeps the financial risk behavior
directly attached to ``sale.order.type``.

The implementation avoids introducing additional rule or
configuration models in order to:

- keep the behavior simple
- reduce maintenance complexity
- align with the functional nature of sale order types
- avoid unnecessary configuration layers

The module still preserves separation between:

- financial exposure computation
- confirmation blocking behavior
