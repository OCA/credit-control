Menu entries are located in ``Invoicing > Adviser > Credit Control``.

Create a new "run" in the ``Credit Control Run`` menu with the controlling date.
Then, use the ``Compute Credit Lines`` button. All the credit control lines will
be generated. You can find them in the ``Credit Control Lines`` menu.

On each generated line, you have many choices:
 * Send a email
 * Print a letter
 * Change the state (so you can ignore or reopen lines)
 * Mark a line as Manually Overridden. The line will get the ignored state when
   a second credit control run is done.
 * Mark one line as Manual followup will also mark all the lines of the
   partner. The partner will be visible in "Do Manual Follow-ups".

The option ``Auto Process Lower Levels`` on ``Credit Control Policy`` helps to
manage high credit control line generation rates (e.g. if you are selling
monthly subscriptions).
In such situation you may want to avoid spamming reminders to customers with
several credit control lines of different levels, and only take action for the
highest level. Thus, an email sent for a high level will also contain the lower
level lines.
Plus, you can use the filter ``Group Lines`` in the ``Credit Control Lines``
menu to hide lines that will be auto-processed when a highest level line is.
