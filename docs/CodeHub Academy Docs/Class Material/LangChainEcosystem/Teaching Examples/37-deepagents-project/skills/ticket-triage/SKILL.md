---
name: ticket-triage
description: CodeHub's specific escalation rules for classifying and routing support tickets
license: MIT
---

# CodeHub Ticket Triage Skill

Triage means: read the incoming ticket, put a **category** and a **priority** on it,
then hand it to the right specialist. You never answer a billing or bug ticket yourself.

Follow the three steps below in order, for every ticket.

## Step 1 - Classify the category

Read the customer's message and pick exactly one category, by looking for these signals:

| Category | Signals in the message |
|---|---|
| `billing` | charge, charged, invoice, refund, subscription, payment, price, plan |
| `bug` | crash, error, broken, can't log in, not working, fails, 500 |
| `general` | anything that matches neither list (questions, feedback, how-to) |

If a message contains signals from both lists, `billing` wins.

## Step 2 - Assign the priority

Apply the first rule that matches, top to bottom:

1. Category is `billing` **and** the message contains "twice" or "duplicate"
   -> priority `critical`. The customer was double-charged: a refund must always be
   offered, without waiting for them to ask.
2. Category is `bug` **and** the message contains "crash" or "can't log in"
   -> priority `high`. The product is unusable for this customer.
3. Anything else -> priority `medium`.

## Step 3 - Route to a subagent

Call the `task` tool to delegate to the subagent that owns this category:

| Category | Subagent |
|---|---|
| `billing` | `billing-specialist` |
| `bug` | `tech-specialist` |
| `general` | none - answer it yourself, briefly |

When you delegate, pass along in the task description:

- the original message from the customer,
- the customer's email if they gave one (the specialist needs it for
  `get_account_status`),
- the category and priority you decided,
- any action the rules require, e.g. "priority critical, offer the refund".

Then return the specialist's answer to the customer. Do not add billing or technical
details of your own on top of it.

## Worked example

> "Hi i am Customer jane@example.com and I was charged twice this month for her
> subscription."

1. "charged", "subscription" -> category `billing`.
2. It is `billing` and contains "twice" -> priority `critical`, refund must be offered.
3. Delegate via `task` to `billing-specialist`, passing jane@example.com, category
   `billing`, priority `critical`, and the instruction to offer a refund.
