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


def test_manager_bootstrap_loads_the_skill_that_declares_childcards_guard():
    prompt = MANAGER_PROMPT.read_text()
    skill = _skill_text()
    assert "/opt/aw-workspace/skills/aw-manager/SKILL.md" in prompt
    assert "## ChildCards guard — epic containers are never resumed" in skill


def test_mode_b_requires_get_kanban_card_before_following_suggested_action():
    """work_loop work_orders omit child_cards and emit resume suggested_action
    for finished Architect/PO runs on epic parents; Mode B must look up the
    card first and let ChildCards guard override suggested_action."""
    skill = _skill_text()
    mode_b_start = skill.index("## Input contract")
    mode_b_end = skill.index("## Selectors (Mode A)")
    mode_b_section = skill[mode_b_start:mode_b_end]

    assert "get_kanban_card(page_id)" in mode_b_section
    assert "child_cards" in mode_b_section
    assert "suggested_action" in mode_b_section
    assert "ChildCards guard" in mode_b_section


def test_batch2_childcards_guard_checks_backoff_before_resolving():
    """Need Human epic parents must respect LastSweptAt back-off before the
    ChildCards guard skips/comments, avoiding repeat comments every sweep."""
    skill = _skill_text()
    b2_start = skill.index("## Batch 2")
    b2_end = skill.index("### Layer B", b2_start)
    b2_section = skill[b2_start:b2_end]

    guard_pos = b2_section.index("**ChildCards guard")
    layer_a_pos = b2_section.index("**Layer A")
    guard_block = b2_section[guard_pos:layer_a_pos]

    assert "LastSweptAt" in guard_block
    assert "back-off" in guard_block
    assert "after the liveness probe and back-off" in guard_block


def test_childcards_guard_withholds_autocomplete_on_25_relation_truncation():
    """Notion truncates page-object relation arrays at 25 items and strips
    has_more in aw-app-notion; never auto-complete to Done when >= 25 without
    has_more=false confirmation."""
    skill = _skill_text()
    guard_start = skill.index("## ChildCards guard — epic containers are never resumed")
    guard_end = skill.index("## Batch 1", guard_start)
    guard_section = skill[guard_start:guard_end]

    assert "len(child_cards) < 25" in guard_section
    assert "len(child_cards) >= 25" in guard_section
    assert "has_more" in guard_section


def test_batch1_probe_cap_distinguishes_backoff_from_run_check():
    """Candidates resolved by ChildCards guard pass back-off without reaching
    the run check, so the 25-probe cap must not equate the two."""
    skill = _skill_text()
    b1_start = skill.index("## Batch 1")
    b1_end = skill.index("### Back-off check", b1_start)
    b1_section = skill[b1_start:b1_end]

    assert "passed back-off and had empty `child_cards`" in b1_section
    assert "resolved by the ChildCards\n   guard" in b1_section


# --- card 41d5bf3b: resumed agents continue known work -----------------------

def test_no_template_forbids_continuing_known_work():
    text = _skill_text() + MANAGER_PROMPT.read_text()
    for banned in ("Do not redo or extend", "do not redo or extend",
                   "not to redo or extend"):
        assert banned not in text, banned


def test_resume_contract_has_three_outcomes_and_qa_rules():
    skill = _skill_text()
    start = skill.index("### Acting on a qualifying card")
    block = skill[start:skill.index("`run_id` names the exact qualifying row")]
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
    assert "applies **only to cards\nalready judged human-only**" in skill
    assert "_reping_human_judged" in skill


def test_signal_a_uses_flow_needs_human_filter_and_ledger_v2_documented():
    skill = _skill_text()
    assert "list_runs(limit=300, flow_needs_human=true)" in skill
    assert "### Ledger write (ring schema v2)" in skill
    assert "beyond_window" in skill


def test_ledger_annotations_are_written_inside_the_iterations_entry():
    """The AP-MT ledger reads annotations from iterations[].items[] matched on
    iteration_id; a top-level ring key would never surface in PlanDetail."""
    skill = _skill_text()
    assert "`iterations[]` — the entry\nwhose `iteration_id`" in skill
    assert '"action": "skipped"' in skill and '"why"' in skill


def _section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    return text[a : text.index(end, a)]


def test_signal_a_verifies_latest_unfiltered_run_before_acting():
    """A filtered scan hides newer unflagged runs, so a candidate must be
    re-checked against the card's latest UNFILTERED run (superseded or active
    newer run => drop) before any Need Human move."""
    sec = _section(_skill_text(), "### Signal A", "**Back-off — applies to Signal A only")
    assert "candidate discovery" in sec
    assert "list_runs(notion_task_id=page_id, limit=1)" in sec
    assert "superseded" in sec and "non-terminal" in sec
    # the unfiltered verification must precede the Status read
    assert sec.index("Verify against the card's latest UNFILTERED run") < sec.index(
        "get_kanban_properties"
    )
    # the old "first row per card is the latest" claim must be gone
    assert "that is each card's most-recently-dispatched run" not in sec


def test_plan_memory_canonical_recipe_is_v2_and_workflow_identity_aware():
    sec = _section(_skill_text(), "## Plan memory — read first, write last", "## Why last_edited_time")
    assert '"schema_version": 2' in sec
    assert '"schema_version": 1' not in sec
    assert "Resolve the iteration identity" in sec
    assert "initiator_kind=plan_cadence" in sec and "initiator_id" in sec
    assert "selector: stale-sweep" in sec
    # canonical example carries the v2 item fields and beyond_window
    for field in ('"action"', '"why"', '"disposition"', '"beyond_window"'):
        assert field in sec
    # the write recipe must not source identity only from the prompt
    assert "Plan-iteration-prompt fields" not in sec


def test_wakeup_annotations_use_the_per_card_server_tool():
    """Concurrent wake-ups must not overwrite each other: the wake-up path
    names the server-side per-card tool and forbids a whole-subtree write."""
    sec = _section(_skill_text(), "## Plan memory — read first, write last", "## Why last_edited_time")
    assert 'annotate_plan_iteration_card(slug="kanban-sweep"' in sec
    assert "Never write a whole-subtree `value` from a wake-up." in sec
    assert "read-modify-write with a re-read" not in sec


def test_batch2_liveness_step_keeps_age_check_for_unjudged_need_human():
    skill = _skill_text()
    a = skill.index("call ①, liveness only")
    sec = skill[a : a + 1600]
    assert "judged human-only" in sec
    assert "NOT waived" in sec and "STALE_RUN_MINUTES" in sec
    assert "recent run activity" in sec
    assert "does not apply here" not in sec
