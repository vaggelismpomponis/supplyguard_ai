---
name: ticket-triage
description: CodeHub's specific escalation rules for classifying and routing support tickets
license: MIT
---

# CodeHub Ticket Triage Skill

## When to Use

Use this whenever a message describes a customer-facing problem that needs
a category and a priority before it can be routed.

## Escalation Rules

- **billing** + the word "twice"/"duplicate" -> priority `critical`. Read
  `refund_policy.md` (in this same skill folder) for the exact refund steps
  before replying.
- **bug** + "crash"/"can't log in" -> priority `high`.
- Anything else -> priority `medium`, category `general`.

## Output Format

Always answer with exactly two lines:

```
category: <billing|bug|general>
priority: <critical|high|medium>
```
