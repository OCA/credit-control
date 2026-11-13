- The core sale order credit warning is hidden because `res.partner.risk_exception`
  combines configurable risk components and limits that normally don't match Odoo's
  core credit computation. Showing both results confuses users and disabling the credit
  limit affects `partner_risk_insurance` which relies on the same company flags as that
  warning message visibility relies on.
  
  For the future, it'd be nice to improve `partner_credit_warning` to show the financial
  risk explained in a meaningful way to the user.
