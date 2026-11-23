# aw-manager selector: stale-sweep-v2

Loaded only when the input says `selector: stale-sweep-v2` (optional `dry_run: true|false`, DEFAULT `true`). The 6 hour cadence keeps running `stale-sweep` until a human repoints the plan; this file never changes that. Rules 2-6 and "Ending the turn" of SKILL.md still apply; where this file is stricter, this file wins.

## Dry run (`dry_run` true or absent)
ZERO writes and ZERO dispatches: no comment, no stamp (`LastSweptAt`), no SweepBlock, no `move_kanban_task`, no `run_agent_async`, no `invoke_kanban_agent`, no `ask_human`, no `create_kanban_task`, no plan memory. Read tools only. Print one table row per card: `card | blocker (as stated) | facts used | verdict | would-do | rule-or-judgment`. `rule` = decided only by the fixed rules below; `judgment` = the model read a comment. End with counts of rule vs judgment. Card-less ending: outside a Plan iteration `mark_flow_done(success, qa_not_needed=true)` with the table as summary. Inside a Plan iteration the SKILL.md ending applies, and `finish_plan_iteration` (with the per-card `annotate_plan_iteration_card` annotations) is the ONE allowed bookkeeping write in a dry run; no `update_plan_memory`, and the table is the `mark_flow_done` summary. Live (`dry_run: false`) only when the order says so explicitly.

## Input: dossier, stale mode
Two calls of `run_cost_analytics(filter_stale=true, ...)`, split by status: In Progress with `min_idle_hours=2`, Need Human with `min_idle_hours=24`. 5 cards per call (`filter_stale_count=5`, page with `offset`) until facts-only mode is reachable, then up to 20. The dossier excludes Manager runs from idle time and drops cards whose `LastSweptAt` is newer than their latest fact. Fact keys used (v1.1): `open_pr`, `pr_merged`, `checks_failing`, `unresolved_threads`, `tag_gaps`, `hours_since_last_run`, `any_run_in_flight`, PR `head_sha`, card `LastSweptAt`/`SweepBlock`/`UnblockProbe`/`QAStatus`/`finding_key`/child count, and the `ask_human` pending/answered fact. A key that is absent is UNKNOWN, never false. STAMP GATE: the dossier must return `LastSweptAt` in each card block. Never trust the list alone: for every picked card, skip it when `LastSweptAt` is newer than its latest fact (last run end, last human comment or `ask_human` answer, last PR activity). If the dossier does not return `LastSweptAt`, stay in dry run: a live sweep is refused (report `needs dossier v1.1`), because the old 48h and 30 minute back-offs do not apply to this selector. Dossier or GitHub unavailable: no verdict, no "gone", report and stop. A Need Human card with an answered `ask_human` or a human comment newer than the parking is NOT skipped even if `stale` is false: act.

## 1. Revalidate the blocker FIRST (every picked card, before any routing)
Fixed order, first match wins (`rule`); otherwise read the blocker comment and judge (`judgment`):
1. `any_run_in_flight`: SKIP (untouchable).
2. Non-empty `child_cards`: epic, ChildCards guard of SKILL.md.
3. Card has PRs, all merged, `checks_failing` 0, `unresolved_threads` 0: PR blocker GONE.
4. CI card (`finding_key` `ci:<repo>:<workflow>`): the stale list has no `ci` block and rejects `repo`/`workflow`, so call `run_cost_analytics(card_id=<card id>, repo=<repo>, workflow=<workflow>, include_tool_stats=false)` and read its `ci` block (never `gh`). GONE only if the latest default-branch run of that workflow is green AND newer than the card's failure. Older or unknown: still blocked.
5. Need Human card with an answered `ask_human` or a human comment newer than the parking: human answered, exit the card via the matrix.

## 2. Blocker gone
- CI card (rule 4): `move_kanban_task(status="done", comment="🧹 manager: default branch green since <run url/time>, newer than the failure")`. This is the ONE Done the Manager owns besides finished epics and the split.
- Delivery exists (merged PR): dispatch QA (merged work only; 409 = read the existing run, never retry, never `qa_rerun`; a passing QA run exists: `invoke_kanban_agent` so the card closes with that QA run id).
- Obsolete / no delivery: dispatch `product-owner`.

## 3. Still blocked: route by what unblocks it
Code or failing PR: coder. Testing: QA, MERGED work only. Clarification, scope, priority, accept/reject, obsolete or not: `product-owner`. Needs a deploy: coder. Design question: `architect`. One named action per touch, dispatch as in SKILL.md matrix 1-3.

## 4. Need Human guardrail
Need Human is for a wall no agent and no decision can remove. The Manager may move a card there itself only when the blocker is a hard show stopper: infrastructure down, missing access or credential, external outage. The comment must name the wall, the evidence, what was tried and the one human action that removes it. If any choice exists (scope, priority, trade-off, accept or reject, obsolete or not), the Manager does not park: it dispatches the PO and the PO decides, including whether to park. In doubt, it is a decision: call the PO. On its own show-stopper park the Manager also writes SweepBlock `routed-human|1|<iso>|<detail>` so reminders keep working; for a PO park it writes the same marker when the PO run calls back. A parked card returns to the sweep after 24h idle (Q3 expiry 1 day).

## 5. Partial QA: split
Only when a QA run on the MERGED revision verified the core criteria and the rest is unverifiable for access or infrastructure reasons. Order: (1) `create_kanban_task` the follow-up (own `finding_key`, parent = original, status Backlog); (2) confirm it is new: if the result has `skipped: true` or no new card id (archived dedup), STOP, do not close the original; (3) `move_kanban_task(done)` the original with a comment listing verified vs moved to the follow-up; (4) `ask_human` Frederico whether the follow-up is worth doing (holds nothing). Lean toward keeping the flow moving.

## 6. Loop guard
SweepBlock wall key per blocker, e.g. `pr-checks-failing:<repo>#<n>`; `detail` stores the PR `head_sha` at the last coder dispatch. Count = coder dispatches for that blocker (`list_runs(notion_task_id=...)`). At 2 with an unchanged `head_sha`, no new PR and unchanged card status: the next step is `product-owner`, never a third coder. A NEW blocker key resets the count to 1. Read the count BEFORE routing: route or escalate, never both.

## 7. Revalidation stamp and budgets
After each verification (live only) write `🧹 manager: Revalidated at <iso>: blocker <X> is still true because <evidence>` (or "gone because ...") AND set `LastSweptAt`. Stamps are free with their own cap of 15 per sweep. The Fixed-10 touch budget is reserved for dispatches and moves (touches); a stamp never spends it. Replaces the 48h and 30 minute back-offs for this selector.
