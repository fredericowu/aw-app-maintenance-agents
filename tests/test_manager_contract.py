"""Contract guards for the ``aw-manager`` skill and prompt.

``aw-manager`` is a pure-markdown agent contract. The skill is kept under 100
lines, so these tests pin the invariants that must survive any further edit.
"""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
MANAGER_SKILL = APP_DIR / "skills/aw-manager/SKILL.md"
MANAGER_PROMPT = APP_DIR / "prompts/manager.md"


def _flat() -> str:
    return " ".join(MANAGER_SKILL.read_text().split())


def test_manager_bootstrap_loads_the_skill():
    prompt = MANAGER_PROMPT.read_text()
    assert "/opt/aw-workspace/skills/aw-manager/SKILL.md" in prompt
    assert "## ChildCards guard" in MANAGER_SKILL.read_text()


def test_skill_stays_compact():
    assert len(MANAGER_SKILL.read_text().splitlines()) < 100


def test_core_safety_rules_survive_compaction():
    flat = _flat()
    for needle in (
        "Never merge a PR", "never remove `devteam:awaiting-fixes`", "UNAUTHENTICATED",
        "NEVER call `mark_flow_done`", "qa_not_needed=true",
        "Non-terminal run on the card (running/pending) = untouchable",
        "Fixed 10 per invocation, any mode", "NEVER treat unevaluable as TRUE",
        "Never use the board's literal \"Not Needed\" option",
        "Never default to (a) on uncertainty", "Never merge directly",
        "do NOT move the card to Need Human",
    ):
        assert needle in flat, needle


def test_childcards_guard_and_25_relation_truncation():
    flat = _flat()
    assert "ChildCards guard overrides `suggested_action`" in flat
    assert "`len(child_cards) < 25`" in flat and "`len(child_cards) >= 25`" in flat
    assert "has_more" in flat and "`Done`, `Self-closed`, `Archived`" in flat


def test_resume_contract_has_three_outcomes_and_qa_rules():
    flat = _flat()
    for needle in ("COMPLETE AND VERIFIED", "KNOWN REMAINING WORK", "OPEN QUESTION",
                   "never `qa_rerun`", "human-only-allowlist"):
        assert needle in flat, needle
    assert "Do not redo or extend" not in flat


def test_plan_iteration_is_resolved_by_tool_call_not_prompt_text():
    flat = _flat()
    assert flat.index("get_run(<your own run id>)") < flat.index("`Plan iteration id:` line")
    assert "never from prompt text alone" in flat
    assert "Wake-ups write only per-card annotations" in flat


def test_signal_a_uses_flow_needs_human_and_verifies_latest_run():
    flat = _flat()
    assert "list_runs(limit=300, flow_needs_human=true)" in flat
    assert "latest UNFILTERED run" in flat
    assert "never read the ~1 MB response into context" in flat


def test_aw_run_routing_precedes_badge_matrix():
    flat = _flat()
    assert flat.index("`aw-run:` reasons first") < flat.index("Per PR by badge")
    for needle in ("`needs_human_label`: `ask_human` only, never a coder",
                   "never re-wake the same session", "`ask_unroutable`",
                   "`aw_run.labels` has `devteam:needs-human` or is `null`"):
        assert needle in flat, needle


def test_pr_writes_go_through_an_authorized_coder():
    flat = _flat()
    for needle in ("only when an authorized Coder", "`no-auth`", "`not-authorized`",
                   "`stale-evidence`", "recheck against the CURRENT head",
                   "(2) CI green AND `mergeStateStatus` `CLEAN`", "never touch `devteam:awaiting-fixes`"):
        assert needle in flat, needle
    assert flat.index("remove the label") < flat.index("comment the evidence") < flat.index("comment `/aw-review`")


def test_budget_split_backoff_before_childcards_and_binding_gap_first():
    flat = _flat()
    assert "Batch 1 takes `7 - priority`" in flat and "`10 - priority - batch1`" in flat
    assert flat.index("back-off, ChildCards guard (an epic") > flat.index("Layer A UnblockProbe")
    assert "is checked FIRST: never a `resume-ineffective` hit" in flat
    assert "call `register_callback(run_id)` and keep `(page_id, run_id, status_at_touch)`" in flat


def test_coders_must_attach_pr_to_target():
    assert "Coders must run `attach_pr_to_target`" in _flat()


def test_author_association_uses_rest_field():
    flat = _flat()
    assert "`author_association`" in flat and "gh pr view <url> --json author" not in flat


def test_register_callback_skipped_only_on_call_me_back_true():
    assert "skip only when the result says `call_me_back: true`" in _flat()


def test_needs_human_removal_requires_every_completed_review_clean():
    # Mixed clean + blocking reviews after the last push must NOT qualify.
    flat = _flat()
    assert "EVERY completed review after the last push found nothing blocking" in flat
    assert "one clean review beside a blocking one does not" in flat
    assert "at least one completed review of the current head exists AND EVERY" in flat
    assert "zero reviews never qualifies" in flat
    assert "a skipped or missing review does not count" in flat
    assert "a COMPLETED review of the current head found nothing blocking" not in flat
