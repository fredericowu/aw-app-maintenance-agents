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
        "do NOT move the card to Need Human", "Read-only with respect to code",
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
                   "`aw_run.labels` has a `devteam:needs-human` or is `null`",
                   "the `devteam:needs-human` PR label is retired under lifecycle v2",
                   "v1-lifecycle caller"):
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


def test_known_author_comes_from_the_verdict_not_a_gh_lookup():
    flat = _flat()
    assert "the verdict's `author_association` OWNER/MEMBER/COLLABORATOR" in flat
    assert "`author_association` null or absent" in flat and "= unknown author: `ask_human`" in flat
    assert "gh api repos/" not in flat
    assert "(reads are fine)" not in flat
    assert "no routing decision may depend on it" in flat


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


def test_awaiting_fixes_and_out_of_repo_have_a_coder_lane():
    flat = _flat()
    for needle in ("`awaiting_fixes`", "fresh coder on the PR's EXISTING branch",
                   "`out_of_repo`", "OWNING repo's worktree",
                   "`blocks_merge: true` at any severity",
                   "`waiting_human` carries a reason and is the only genuine human hold"):
        assert needle in flat, needle
    assert flat.index("`awaiting_fixes`") < flat.index("Per PR by badge")


def test_findings_work_order_defers_rules_to_the_skill():
    flat = _flat()
    assert "load the aw-code-review-response skill and act on PR <url>" in flat
    assert "Never inline the rules" in flat
    assert flat.count("`blocks_merge: true` at any severity") == 1


def test_idle_open_wakes_a_coder_with_the_short_order():
    flat = _flat()
    for needle in ("`idle_open`", "`idle_open:` at the start of ANY `;`-delimited reason",
                   "no run is acting on it", "never skip because the PR is already `devteam:reviewed`",
                   "is in the PR's own diff they are NOT out of repo"):
        assert needle in flat, needle
    assert flat.index("`idle_open`") < flat.index("Per PR by badge")


V2_SKILL = APP_DIR / "skills/aw-manager/stale-sweep-v2.md"


def _v2() -> str:
    return " ".join(V2_SKILL.read_text().split())


def test_v2_selector_is_wired_from_skill_and_old_selector_untouched():
    flat = _flat()
    assert "`stale-sweep-v2`" in flat
    assert "/opt/aw-workspace/skills/aw-manager/stale-sweep-v2.md" in flat
    assert "`selector: stale-sweep` | `github-maintenance`" in flat
    assert "Batch 1 takes `7 - priority`" in flat  # old cadence rules intact
    assert V2_SKILL.exists() and "aw-manager/stale-sweep-v2.md" not in V2_SKILL.read_text()


def test_v2_dry_run_is_default_and_performs_zero_writes():
    v2 = _v2()
    assert "DEFAULT `true`" in v2 and "ZERO writes and ZERO dispatches" in v2
    for tool in ("move_kanban_task", "run_agent_async", "invoke_kanban_agent",
                 "ask_human", "create_kanban_task", "SweepBlock"):
        assert tool in v2.split("## Input")[0], tool
    assert "rule-or-judgment" in v2 and "one table row per card" in v2.lower()
    assert "never changes that" in v2


def test_v2_revalidates_before_routing_with_dossier_split_calls():
    v2 = _v2()
    assert v2.index("## 1. Revalidate the blocker FIRST") < v2.index("## 3. Still blocked")
    assert "min_idle_hours=2`" in v2 and "min_idle_hours=24`" in v2
    assert "`filter_stale_count=5` per call" in v2 and "never `gh`" in v2
    assert "`run_cost_analytics(card_id=<card id>, repo=<repo>, workflow=<workflow>" in v2
    assert "STAMP GATE" in v2 and "`card.last_swept_at` is newer than its latest fact" in v2
    assert "dry run refused inside a Plan iteration" in v2
    assert "`plan_iteration_id` on YOUR OWN run" in v2 and "Its only call is `finish_plan_iteration`" in v2
    assert "`facts.unresolved_threads` == 0" in v2 and "unresolved_threads_open` alone" in v2
    assert "min_idle_hours=0, honor_stamp=false" in v2 and "`latest_answered_at` newer than" in v2
    for key in ("`card.last_swept_at`", "`card.child_count`", "`facts.all_prs_merged`",
                "`facts.merged_checks_failing` == 0", "`facts.discovery_complete`"):
        assert key in v2, key
    assert "`statuses=in_progress, min_idle_hours=2`" in v2 and "`statuses=need_human, min_idle_hours=24`" in v2
    assert "`green_after_since`" in v2
    assert "latest default-branch run of that workflow is green AND newer than" in v2


def test_v2_routing_lanes_and_qa_merged_only():
    v2 = _v2()
    for needle in ("coder", "QA, MERGED work only", "`product-owner`", "`architect`",
                   "Needs a deploy: coder", "never `qa_rerun`"):
        assert needle in v2, needle


def test_v2_need_human_only_for_show_stopper_next_to_the_condition():
    v2 = _v2()
    assert ("Need Human is for a wall no agent and no decision can remove. The Manager may "
            "move a card there itself only when the blocker is a hard show stopper") in v2
    assert "In doubt, it is a decision: call the PO." in v2
    # every Need Human move sits in the guardrail section; no other section parks
    assert v2.count("status=\"need_human\"") == 0
    assert "routed-human|1|<iso>|<detail>" in v2


def test_v2_loop_guard_split_and_stamp_budgets():
    v2 = _v2()
    assert "At 2 with an unchanged `head_sha`" in v2 and "never a third coder" in v2
    assert "A NEW blocker key resets the count to 1" in v2
    assert "`skipped: true`" in v2 and v2.index("create_kanban_task") < v2.index("(3) `move_kanban_task(done)`")
    assert "15 per sweep" in v2 and "a stamp never spends it" in v2
    assert "`LastSweptAt`" in v2
