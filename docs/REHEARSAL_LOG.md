# Demo Rehearsal Log

**Issue:** #55 · **Owner:** Quality · **Script:** [DEMO_SCRIPT.md](./DEMO_SCRIPT.md)

We run at least two full dry runs of the 10-minute demo. Presenters rotate so that every member presents
a different part each time and can explain the whole flow.

## Team

| Member | Role |
|---|---|
| @vaggelismpomponis | Platform |
| @AlexZarkalis | Interface |
| @stef-fot | Knowledge |
| @VickyMil-ai | Quality |

## Rotation

Segment numbers and times follow [DEMO_SCRIPT.md](./DEMO_SCRIPT.md#timing). Rules:

- No one presents a segment that belongs to their own role.
- No one presents the same segment in both rehearsals.
- Each person presents 2–3 minutes per rehearsal.

| # | Segment | Time | Rehearsal 1 | Rehearsal 2 |
|---|---|---|---|---|
| 1 | Objective & stack | 1′ | @VickyMil-ai | @stef-fot |
| 2 | Clarification flow | 2′ | @VickyMil-ai | @stef-fot |
| 3 | Policy citation & version conflict | 2′ | @vaggelismpomponis | @AlexZarkalis |
| 4 | Outage detection & link to outage | 2′ | @AlexZarkalis | @vaggelismpomponis |
| 5 | Human approval & restart resume | 2′ | @stef-fot | @VickyMil-ai |
| 6 | LangSmith tracing & evaluation | 1′ | @stef-fot | @AlexZarkalis |

If we hold a third rehearsal, each member presents the segment closest to their own role, as a check
on the final run.

## How to run a rehearsal

1. **T-30 min:** run the [pre-demo check](./DEMO_SCRIPT.md#before-the-demo-t-30-min). It must end with
   `RESULT: PASS`.
2. **Run the demo:** go through all 6 segments, presented by the members listed above. One member
   who isn't presenting keeps time.
3. **Recheck the [known issues](./DEMO_SCRIPT.md#known-issues):** record whether each one still occurs.
4. **Architecture questions:** each member answers one question about a part of the flow they did
   *not* present. Use the follow-up questions from the brief:
   - "Why didn't you reset the password?"
   - "Which other teams are affected by this outage?"
   - "Which policy did you base this on?"
   - "Continue the request I opened before the restart."
5. **Follow up:** each problem found becomes an issue for the owning role. Link it in the table below.

## Rehearsal 1

**Date:** 2026-11-24 · **Timekeeper:** @AlexZarkalis · **`demo_check`:** PASS

| # | Segment | Presenter | Planned | Actual | Notes |
|---|---|---|---|---|---|
| 1 | Objective & stack | @VickyMil-ai | 1′ | 1′00″ | Presented SupplyGuard AI 5-service stack & Deep Agents orchestration |
| 2 | Clarification flow | @VickyMil-ai | 2′ | 1′50″ | Demonstrated ambiguous "Atlas" -> S001 vs S006 clarification dialog |
| 3 | Policy citation & version conflict | @vaggelismpomponis | 2′ | 2′00″ | Demonstrated DOC-CON-S001-v3 superseding v2 & Borealis expired ISO cert |
| 4 | Outage detection & link to outage | @AlexZarkalis | 2′ | 1′55″ | Presented Neo4j shared Tier-2 upstream Veltro (U01) & Strategy Comparison Matrix |
| 5 | Human approval & restart resume | @stef-fot | 2′ | 2′00″ | Demonstrated payload-bound Approval Card, container restart resume & PDF report |
| 6 | LangSmith tracing & evaluation | @stef-fot | 1′ | 1′00″ | Demonstrated subagent spans & follow-up Q&A |
| | **Total** | | **10′** | **9′45″** | |

**Known issues**

| # | Issue | Still occurs? |
|---|---|---|
| 1 | Approval buttons fail on `chainlit==1.3.2` | No (Fixed via JSON `value` encoding & `_extract_action_payload`) |
| 2 | Live evaluation 8/10 (EVAL-06, EVAL-09 citations) | No |
| 3 | No logged-in user in the UI | No (Fixed via RBAC profiles & interactive Role Switcher `#43`) |
| 4 | Doubled period at the end of responses | No |

**Architecture questions**

| Member | Question | Explained clearly? |
|---|---|---|
| @vaggelismpomponis | What changes if we increase the spending limit to €90,000? | Yes |
| @AlexZarkalis | Why did you reject Supplier Helios and how does payload binding prevent tampering? | Yes |
| @stef-fot | Can we protect our highest-priority customers using existing stock? | Yes |
| @VickyMil-ai | How does the session resume after container restart without duplicate PO execution? | Yes |

**Problems found**

| Problem | Owner | Issue |
|---|---|---|
| None — all UI flows verified | Interface | #41–#53 |

## Rehearsal 2

**Date:** 2026-11-24 · **Timekeeper:** @vaggelismpomponis · **`demo_check`:** PASS

| # | Segment | Presenter | Planned | Actual | Notes |
|---|---|---|---|---|---|
| 1 | Objective & stack | @stef-fot | 1′ | 0′55″ | Smooth overview of business case and €75k spending cap |
| 2 | Clarification flow | @stef-fot | 2′ | 1′55″ | Ambiguous entity pause and resumption verified |
| 3 | Policy citation & version conflict | @AlexZarkalis | 2′ | 1′55″ | Presented source-precedence conflicts, RBAC scopes (`DOC-FIN-01-v1`) & prompt injection defense |
| 4 | Outage detection & link to outage | @vaggelismpomponis | 2′ | 2′00″ | Presented operational impact dashboard (3,200 usable, 5,350 shortfall) |
| 5 | Human approval & restart resume | @VickyMil-ai | 2′ | 1′55″ | Demonstrated Modify Plan revalidation, container restart resume & Markdown/PDF export |
| 6 | LangSmith tracing & evaluation | @AlexZarkalis | 1′ | 1′00″ | Presented subagent telemetry steps and multi-turn follow-up Q&A |
| | **Total** | | **10′** | **9′40″** | |

**Known issues**

| # | Issue | Still occurs? |
|---|---|---|
| 1 | Approval buttons fail on `chainlit==1.3.2` | No |
| 2 | Live evaluation 8/10 (EVAL-06, EVAL-09 citations) | No |
| 3 | No logged-in user in the UI | No |
| 4 | Doubled period at the end of responses | No |

**Architecture questions**

| Member | Question | Explained clearly? |
|---|---|---|
| @vaggelismpomponis | Why is Borealis blocked despite ERP status 'approved'? | Yes |
| @AlexZarkalis | How are Revenue at Risk and Recovery Cost separated in the Strategy Matrix? | Yes |
| @stef-fot | Why is Delta Micro not a valid diversification from Atlas Components? | Yes |
| @VickyMil-ai | How is `DOC-NOT-HELIOS-PRICE` prompt injection neutralized? | Yes |

**Problems found**

| Problem | Owner | Issue |
|---|---|---|
| None — ready for live evaluation | All | #53 |

## Sign-off

Tick each box when its rehearsal is logged above, then close #55.

- [x] Rehearsal 1 held and logged
- [x] Rehearsal 2 held and logged
- [x] Every member answered an architecture question on a part they did not present
