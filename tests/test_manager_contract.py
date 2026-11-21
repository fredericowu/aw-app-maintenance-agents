"""Contract guards for the ``aw-manager`` skill and prompt.

``aw-manager`` is a pure-markdown agent contract, so regressions in subtle
ordering or truncation rules only surface in production unless the invariants
pinned in code review are asserted directly against the shipped text.
"""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
MANAGER_SKILL = APP_DIR / "skills/aw-manager/SKILL.md"
MANAGER_PROMPT = APP_DIR / "prompts/manager.md"


def _skill_text() -> str:
    return MANAGER_SKILL.read_text()


def _flat(text: str) -> str:
    return " ".join(text.split())


def _section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    return text[a : text.index(end, a)]


def test_manager_bootstrap_loads_the_skill_that_declares_childcards_guard():
    prompt = MANAGER_PROMPT.read_text()
    assert "/opt/aw-workspace/skills/aw-manager/SKILL.md" in prompt
    assert "## ChildCards guard (4th exception)" in _skill_text()


def test_skill_stays_compact():
    """The skill was compacted from 3148 lines; keep it from regrowing."""
    assert len(_skill_text().splitlines()) < 500
    # PO-approved ceiling for card 41e5bf3b (was 7645 words at a5e6433; 25652 at 8dac4a6)
    assert len(_skill_text().split()) <= 6548


def test_pr_row_is_gone_from_the_known_gap_and_routes_to_pr_write_routing():
    sec = _section(_skill_text(), "## Input contract", "## Per-card pipeline")
    assert "documented gap" not in sec
    assert "PR write routing" in sec and "suggested_action` (advisory)" in sec


def test_mode_b_requires_get_kanban_card_before_following_suggested_action():
    """work_loop work_orders omit child_cards and emit resume suggested_action
    for finished Architect/PO runs on epic parents; Mode B must look up the
    card first and let ChildCards guard override suggested_action."""
    sec = _section(_skill_text(), "## Input contract", "## Per-card pipeline")
    assert "get_kanban_card(page_id)" in sec
    assert "child_cards" in sec and "suggested_action" in sec
    assert "ChildCards guard overrides `suggested_action`" in sec


def test_batch2_childcards_guard_checks_backoff_before_resolving():
    """Need Human epic parents must respect LastSweptAt back-off before the
    ChildCards guard skips/comments, avoiding repeat comments every sweep."""
    skill = _skill_text()
    guard = _section(skill, "## ChildCards guard", "## Batch 1")
    assert "after the LastSweptAt back-off" in guard
    assert "a backed-off card is skipped before reading children or commenting" in guard
    b2 = _section(skill, "## Batch 2", "## Deferred stamp")
    assert "ChildCards guard** runs after liveness + back-off, before Layer A" in b2


def test_childcards_guard_withholds_autocomplete_on_25_relation_truncation():
    """Notion truncates page-object relation arrays at 25 items and strips
    has_more in aw-app-notion; never auto-complete to Done when >= 25 without
    has_more=false confirmation."""
    guard = _section(_skill_text(), "## ChildCards guard", "## Batch 1")
    assert "len(child_cards) < 25" in guard
    assert "len(child_cards) >= 25" in guard
    assert "has_more" in guard
    assert "Done`, `Self-closed`, `Archived" in guard


def test_batch1_probe_cap_distinguishes_backoff_from_run_check():
    b1 = _section(_skill_text(), "## Batch 1", "### Run check")
    assert "25 run-check probes" in b1
    assert "Back-off or ChildCards-resolved candidates don't count against it" in b1


# --- card 41d5bf3b: resumed agents continue known work -----------------------

def test_no_template_forbids_continuing_known_work():
    text = _skill_text() + MANAGER_PROMPT.read_text()
    for banned in ("Do not redo or extend", "do not redo or extend",
                   "not to redo or extend"):
        assert banned not in text, banned


def test_resume_contract_has_three_outcomes_and_qa_rules():
    skill = _skill_text()
    block = _section(skill, "### Acting on a qualifying card", "`run_id` pins")
    assert "COMPLETE AND VERIFIED" in block
    assert "KNOWN REMAINING WORK" in block
    assert "OPEN QUESTION" in block
    assert "never closed with qa_not_needed" in block
    assert "never qa_rerun" in block
    assert "human-only allowlist" in block


def test_fresh_fallback_and_destination_one_carry_the_contract():
    skill = _skill_text()
    assert "never \"no work has been done\"" in skill
    assert "never close merged code with qa_not_needed" in skill


def test_wakeup_routes_a_card_the_agent_moved_to_need_human():
    skill = _skill_text()
    assert "moved the card to `Need Human`" in skill
    assert "One recovery hop per card per iteration" in skill


def test_batch2_twelve_hour_filter_only_for_human_judged_cards():
    skill = _skill_text()
    assert "applies **only to cards already judged human-only**" in _flat(skill)
    assert "_reping_human_judged" in skill


def test_signal_a_uses_flow_needs_human_filter():
    skill = _skill_text()
    assert "list_runs(limit=300, flow_needs_human=true)" in skill
    assert "beyond_window" in skill


def test_ledger_annotations_are_written_inside_the_iterations_entry():
    """Annotations belong in iterations[].items[] matched on iteration_id."""
    skill = _skill_text()
    assert '"iterations": [{"seq": 9, "iteration_id"' in skill
    assert '"action"' in skill and '"why"' in skill and '"disposition"' in skill


def test_signal_a_verifies_latest_unfiltered_run_before_acting():
    """A filtered scan hides newer unflagged runs, so a candidate must be
    re-checked against the card's latest UNFILTERED run before any move."""
    sec = _section(_skill_text(), "**Signal A:", "**Back-off applies to Signal A only")
    assert "Candidate discovery only" in sec
    assert "list_runs(notion_task_id=page_id, limit=1)" in sec
    assert "superseded" in sec and "non-terminal" in sec
    assert sec.index("Verify against the card's latest UNFILTERED run") < sec.index(
        "get_kanban_properties"
    )


def test_signal_a_verifies_escalation_reason_and_does_not_read_300_rows():
    sec = _section(_skill_text(), "**Signal A:", "**Back-off applies to Signal A only")
    assert "Verify the escalation reason before moving the card" in sec
    assert "human-only allowlist" in sec
    assert "Do not read the response into context" in sec


def test_plan_memory_canonical_recipe_is_v2_and_workflow_identity_aware():
    sec = _section(_skill_text(), "## Plan memory", "## Back-off: LastSweptAt")
    assert '"schema_version": 2' in sec
    assert '"schema_version": 1' not in sec
    assert "initiator_kind=plan_cadence" in sec and "initiator_id" in sec
    for field in ('"action"', '"why"', '"disposition"', '"beyond_window"'):
        assert field in sec


def test_wakeup_annotations_use_the_per_card_server_tool():
    """Concurrent wake-ups must not overwrite each other."""
    sec = _section(_skill_text(), "## Plan memory", "## Back-off: LastSweptAt")
    assert 'annotate_plan_iteration_card(slug="kanban-sweep"' in sec
    assert "Never write a whole-subtree `value` from a wake-up." in sec


def test_batch2_liveness_step_keeps_age_check_for_unjudged_need_human():
    b2 = _section(_skill_text(), "**Liveness (call", "**ChildCards guard** runs after")
    assert "judged human-only" in b2
    assert "NOT waived" in b2 and "STALE_RUN_MINUTES" in b2
    assert "recent run activity" in b2


def test_plan_iteration_is_resolved_by_tool_call_not_prompt_text():
    """Sweep #66: the Manager concluded 'Not a plan iteration' from the prompt
    alone and declared nothing, leaving 9/10 gate candidates UNACCOUNTED."""
    skill = _skill_text()
    core = _section(skill, "## Core rules", "## Ending the turn")
    assert "get_run(<your own run id>)" in core
    assert "annotate_plan_iteration_card" in core
    assert "never from prompt text" in core
    assert "never call `get_plan_memory`/`update_plan_memory`" in _section(
        skill, "## Plan memory", "**READ once**")


def test_every_gate_candidate_is_declared_including_deferred():
    sec = _section(_skill_text(), "## Plan memory", "## Back-off: LastSweptAt")
    assert "**Per-card declaration (every pass, every gate candidate):**" in sec
    assert '`action="deferred"`' in sec
    assert "UNACCOUNTED" in sec and "MISMATCH" in sec


def test_skips_and_human_routed_restamps_do_not_spend_touch_budget():
    sec = _section(_skill_text(), "## Touch budget", "## Feeders")
    assert "Does NOT spend" in sec
    assert "routed-human" in sec and "skip" in sec
    assert "Deferred is recorded, never silent" in sec


def test_mark_flow_done_binding_gap_is_routed_to_a_resume():
    skill = _skill_text()
    sec = _flat(_section(skill, "### Closed-but-still-open", "### Acting on a qualifying card"))
    assert "notion_task_id: null" in sec
    assert "The Manager never moves the card itself on this signature" in sec


def test_binding_gap_retry_failure_never_moves_card_to_need_human():
    sec = _flat(_section(_skill_text(), "### Closed-but-still-open", "### Acting on a qualifying card"))
    assert "do NOT move the card to Need Human" in sec
    assert "human-only allowlist" not in sec or "Need Human stays reserved for the allowlist" in sec
    assert "`routed`/`pending`" in sec


def test_binding_gap_skips_failed_retry_and_is_not_a_clean_touch():
    skill = _skill_text()
    sec = _flat(_section(skill, "### Closed-but-still-open", "### Acting on a qualifying card"))
    assert "only if the previous outcome was `success`" in sec
    assert "`failed` or `partial` outcome is never replayed" in sec
    flat = _flat(skill)
    bg = flat.index("**Binding-gap resume, card still In Progress**")
    assert bg < flat.index("**Terminal `error`, or `success` with no new reply comment:**")
    assert bg < flat.index("**`success` with a new reply comment:**")
    assert "never a `resume-ineffective` hit" in flat


def test_binding_gap_classification_is_recorded_at_dispatch_not_read_from_comment():
    flat = _flat(_skill_text())
    assert 'record "binding-gap" beside the `(page_id, run_id, status_at_touch)` triple AT DISPATCH' in flat
    assert "the agent's comment is corroboration, never the test" in flat


def test_manager_skill_documents_aw_run_block_and_reasons():
    text = _skill_text()
    for needle in ("`aw_run` block", "aw-run:", "escalate (woken 3x", "stuck_active", "needs_human_label",
                   "Never re-wake the same session", "3h cadence"):
        assert needle in text, needle


def test_aw_run_routing_precedes_badge_matrix_and_needs_human_goes_to_human():
    text = _skill_text()
    i = text.index("**Check `attention_reason` for the `aw-run:` prefix FIRST**")
    block = text[i : i + 1500]
    assert "badge: null" in block
    line = next(l for l in block.splitlines() if "needs_human_label" in l)
    assert "`ask_human` only" in line and "never a coder" in line
    row = next(l for l in block.splitlines() if "stuck_active" in l)
    assert "fresh coder" in row and "Never re-wake the same session" in row


def test_fallback_tagged_pr_is_never_delegated_on_badge_alone():
    text = _skill_text()
    i = text.index("aw_run: {fallback: true}")
    block = text[i : i + 900]
    assert "Never delegate" in block and "devteam:needs-human" in block and "`ask_human`" in block
    assert "`labels`" in block and "`null`" in block
    assert "replayed verdict" in block and "your `gh` cannot see private PRs" in block


def test_register_callback_is_skipped_only_on_call_me_back_true():
    """A resume that armed its own callback must not be re-registered (resets
    callback_done, double wake); false/absent flags still need registration."""
    skill = _skill_text()
    recipe = _section(skill, "For every outcome that dispatched a run", "Comment first, register second")
    assert "skip ONLY when the invoke_kanban_agent result says call_me_back: true" in recipe
    flat = _flat(skill)
    assert "`false` or an absent key still needs registration" in flat
    pr = _flat(_section(skill, "(3) `register_callback(<run_id>)`", "(4) plan-memory"))
    assert "unless the result says `call_me_back: true`" in pr


def test_manager_skill_covers_deterministic_wake_and_ask_unroutable():
    text = _flat(_skill_text())
    for needle in ("`ask_unroutable`", "request one re-review", "do NOT ask again",
                   "reach you only from an AP-MT that predates the `facts` decision"):
        assert needle in text, needle
    row = next(l for l in _skill_text().splitlines() if l.startswith("| `ask_unroutable`"))
    assert "`ask_human` yourself" in row


def test_safety_net_asks_for_verdicts_seen_only_in_aw_run_verdicts():
    text = _skill_text()
    block = _flat(text[text.index("**Safety net.**"):][:1200])
    for needle in ("ask_failed", "ask_deferred", "ask_unroutable", "handed_off",
                   "NOT already in `prs`", "check no question is pending", "`ask_human` once",
                   "Never dispatch a coder from it", "two consecutive"):
        assert needle in block, needle
    assert "`asked`/`woken` are never part of this net" in block


def test_core_safety_rules_survive_compaction():
    """Hard rules the Manager must never lose."""
    flat = _flat(_skill_text())
    for needle in (
        "Never merge a PR", "never remove `devteam:awaiting-fixes`",
        "NEVER call `mark_flow_done`", "qa_not_needed=true",
        "Non-terminal run on the card (running/pending) = untouchable",
        "**Fixed 5 per invocation, any mode**",
        "NEVER treat unevaluable as TRUE",
        "Never use the board's literal \"Not Needed\" option",
        "UNAUTHENTICATED",
        "Never default to (a) on uncertainty",
        "Never merge directly",
    ):
        assert needle in flat, needle


# --- card 41e5bf3b rework: PR writes via an authorized Coder, Plan source order --

def _pr_routing() -> str:
    return _flat(_section(_skill_text(), "## PR write routing", "## Plan memory"))


def test_scenario_authorized_pr_write_goes_to_a_coder_with_its_own_gh():
    sec = _pr_routing()
    assert "suggested_action` is advisory" in sec
    assert 'run_agent_async(group_slug="coders"' in sec
    assert "that runner's authenticated `gh` on the target repo" in sec
    assert "recheck the evidence against the CURRENT head" in sec
    assert "Label operations and every other PR write need an authenticated `gh`" in sec


def test_scenario_needs_human_removal_order_and_conditions():
    sec = _pr_routing()
    sec = sec[sec.index("**`devteam:needs-human`:**"):]
    assert "only the resolver of its blocker may remove it" in sec
    assert "dispatched to resolve this PR's blocker" in sec
    for cond in ("(1) the label predates", "(2) CI green AND `mergeStateStatus` `CLEAN`", "(3) every review pass"):
        assert cond in sec, cond
    assert sec.index("remove the label") < sec.index("post a PR comment") < sec.index("comment `/aw-review`")
    assert "all via its authenticated `gh`" in sec
    assert "Never merge directly" in sec and "never touch `devteam:awaiting-fixes`" in sec


def test_scenario_missing_auth_authority_or_stale_evidence_is_skipped_not_claimed():
    sec = _pr_routing()
    for reason in ("`no-auth`", "`not-authorized`", "`stale-evidence`"):
        assert reason in sec, reason
    assert "make no write" in sec and "never as success" in sec
    assert "the label stays and the reason is reported" in sec
    assert "skip, report the reason, claim nothing" in sec


def test_scenario_holds_external_authors_and_gate_labels_are_preserved():
    sec = _pr_routing()
    row = sec[sec.index("| Human hold"):sec.index("| Gate-owned")]
    assert "unknown/external author" in row and "`needs_human_label` verdict" in row
    assert "`ask_human`; no coder" in row
    assert "never touched" in sec
    for gate in ("`devteam:awaiting-fixes`", "`devteam:review-capped`", "`devteam/*`", "`aw-run:*`"):
        assert gate in sec, gate


def test_manager_never_writes_with_its_own_gh_and_no_standing_label_exception():
    text = _flat(_skill_text())
    assert "your `gh` is UNAUTHENTICATED" in text
    assert "never `gh pr merge/close/comment` or a label write" in text
    assert "The Manager may remove" not in text
    assert "one exception" not in text


def test_work_order_skip_reasons_reach_the_report():
    rep = _flat(_section(_skill_text(), "## Report", "Report what is true"))
    assert "`no-auth`, `not-authorized`, `stale-evidence`" in rep
    assert "never a skipped write as done" in rep


def test_plan_iteration_source_order_is_get_run_then_prompt_fallback():
    skill = _skill_text()
    core = _flat(_section(skill, "## Core rules", "## Ending the turn"))
    assert core.index("get_run(<your own run id>)") < core.index("`Plan iteration id:` line")
    assert "only the fallback when `get_run` errors or shows no parent" in core
    mem = _flat(_section(skill, "## Plan memory", "**READ once**"))
    assert mem.index("`get_run` parent `initiator_kind=plan_cadence`") < mem.index(
        "prompt `Plan iteration id:` line as fallback"
    )
    assert "prompt `Plan iteration id:` line, else parent run" not in _flat(skill)
