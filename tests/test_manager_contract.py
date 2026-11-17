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
