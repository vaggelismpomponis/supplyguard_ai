# CodeHub Refund Script

Full steps for the "billing + duplicate charge" case referenced from SKILL.md.
Only read this file when that rule actually fires -- it does not need to sit
in the main skill body or the system prompt.

1. Confirm the two charge dates and amounts match exactly.
2. Refund the newer charge, keep the original subscription active.
3. Tell the customer the refund posts in 3-5 business days.
4. Log the ticket as `billing/duplicate-charge` for the finance weekly report.
