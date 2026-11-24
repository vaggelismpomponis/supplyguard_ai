# Demo Rehearsal Log

**Owner:** Quality · **Issue:** #92 · **Script:** [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) (#91)

We hold at least two full rehearsals of the 10-minute demo. Presenters rotate so that every member
presents a different part each time and can explain the whole flow.

## Team

| Member | Roles |
|---|---|
| @vaggelismpomponis | Platform |
| @AlexZarkalis | Interface |
| @stef-fot | Knowledge |
| @VickyMil-ai | Workflow, Quality |

## Schedule (proposed, Day 1 = 2026-11-24)

| Rehearsal | When | Precondition |
|---|---|---|
| Dry run (optional) | Day 8, 2026-12-03 | the agent reaches the approval card on EV-0001 |
| **Rehearsal 1** | Day 9, 2026-12-04 | `eval.demo_check` passes |
| **Rehearsal 2** | Day 10, 2026-12-07, morning | problems from rehearsal 1 fixed or have a fallback |

## Rotation

Each segment has one owner role. Rules:

- No one presents a segment owned by their own role.
- No one presents the same segment in both rehearsals.
- Each person presents 2–3 minutes per rehearsal.

| # | Segment | Time | Owner role | Rehearsal 1 | Rehearsal 2 |
|---|---|---|---|---|---|
| 1 | Business goal and architecture | 1′ | Platform | @AlexZarkalis | @stef-fot |
| 2 | Triage clarification | 2′ | Interface | @VickyMil-ai | @vaggelismpomponis |
| 3 | Investigation, impact, planted document | 2′ | Knowledge | @vaggelismpomponis | @VickyMil-ai |
| 4 | Strategy comparison | 2′ | Workflow | @stef-fot | @AlexZarkalis |
| 5 | Approval, restart, resume | 2′ | Platform | @AlexZarkalis | @stef-fot |
| 6 | Follow-ups and LangSmith | 1′ | Quality | @vaggelismpomponis | @AlexZarkalis |

Minutes per person: rehearsal 1 is Alex 3′, Vicky 2′, Vaggelis 3′, Stef 2′; rehearsal 2 is Stef 3′,
Vaggelis 2′, Vicky 2′, Alex 3′. For the final demo, each member presents the segment closest to their
own role.

## How to run a rehearsal

1. **T-30 min:** run the [pre-demo check](./DEMO_SCRIPT.md#before-the-demo-t-30-min). It must end with
   `RESULT: PASS`. If it fails, log which step failed and rehearse with the fallbacks.
2. **Run the demo** through all 6 segments with the presenters above. A member who is not presenting
   keeps time per segment.
3. **Architecture questions:** each member answers one question about a part they did *not* present,
   for example:
   - "Why did you reject Supplier Helios?"
   - "What changes if we raise the limit to EUR 90,000?"
   - "Can we protect our highest-priority customers using existing stock?"
   - "Resume the case I was reviewing yesterday."
   - "What stops a supplier document from creating a purchase order?"
   - "How do you know the purchase order was not created twice after the restart?"
4. **Follow up:** each problem becomes an issue for the owning role, linked in the table below.

## Rehearsal 1

**Date:** _TBD_ · **Commit:** _TBD_ · **Timekeeper:** _TBD_ · **`demo_check`:** _TBD_

| # | Segment | Presenter | Planned | Actual | Notes |
|---|---|---|---|---|---|
| 1 | Business goal and architecture | @AlexZarkalis | 1′ | | |
| 2 | Triage clarification | @VickyMil-ai | 2′ | | |
| 3 | Investigation, impact, planted document | @vaggelismpomponis | 2′ | | |
| 4 | Strategy comparison | @stef-fot | 2′ | | |
| 5 | Approval, restart, resume | @AlexZarkalis | 2′ | | |
| 6 | Follow-ups and LangSmith | @vaggelismpomponis | 1′ | | |
| | **Total** | | **10′** | | |

**Architecture questions**

| Member | Question | Explained clearly? |
|---|---|---|
| @vaggelismpomponis | | |
| @AlexZarkalis | | |
| @stef-fot | | |
| @VickyMil-ai | | |

**Problems found**

| Problem | Owner | Issue |
|---|---|---|
| | | |

## Rehearsal 2

**Date:** _TBD_ · **Commit:** _TBD_ · **Timekeeper:** _TBD_ · **`demo_check`:** _TBD_

| # | Segment | Presenter | Planned | Actual | Notes |
|---|---|---|---|---|---|
| 1 | Business goal and architecture | @stef-fot | 1′ | | |
| 2 | Triage clarification | @vaggelismpomponis | 2′ | | |
| 3 | Investigation, impact, planted document | @VickyMil-ai | 2′ | | |
| 4 | Strategy comparison | @AlexZarkalis | 2′ | | |
| 5 | Approval, restart, resume | @stef-fot | 2′ | | |
| 6 | Follow-ups and LangSmith | @AlexZarkalis | 1′ | | |
| | **Total** | | **10′** | | |

**Architecture questions**

| Member | Question | Explained clearly? |
|---|---|---|
| @vaggelismpomponis | | |
| @AlexZarkalis | | |
| @stef-fot | | |
| @VickyMil-ai | | |

**Problems found**

| Problem | Owner | Issue |
|---|---|---|
| | | |

## Sessions logged before the script rewrite (PR #97)

Two sessions were logged on 2026-11-24 in PR #97 (Interface), before this file and
[DEMO_SCRIPT.md](./DEMO_SCRIPT.md) were rewritten for SupplyGuard. They are kept here unchanged.

**Quality note:** they use the HelpDesk Lite segment names and rotation, and `demo_check` at that time
was the HelpDesk Lite check. The team decides whether they count toward the two rehearsals of #92, or
whether Rehearsals 1 and 2 above are still needed with the new script and the new `eval.demo_check`.

### Session A (logged as "Rehearsal 1")

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

### Session B (logged as "Rehearsal 2")

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

Tick each box when its rehearsal is logged above, then close #92.

- [ ] Rehearsal 1 held and logged
- [ ] Rehearsal 2 held and logged
- [ ] Every member presented two different segments and answered a question on a part they did not present
