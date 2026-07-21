from __future__ import annotations

from pathlib import Path

from scripts.validation import validate_handoff_policy as policy


BASE_FRONTMATTER = """---
task_key: sprint_flow_test
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 99
milestone_id: M99
status: READY_FOR_CODEX_MERGE
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/sprint_flow_test_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: planner_only
experiment_adequacy_gate: controller_verified
route_negative_gate: planner_only
scientific_completion_gate: planner_only
diagnostic_publication_gate: planner_only
diagnostic_publication_scope: local_lightweight_packet
blocked_after_diagnostic_publication: true
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
---
"""

BODY = """
## Execution Contract
```yaml
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/sprint_flow_test_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_required: false
review_mode: none
reviewer: none
```
minimum_effective_training: required
controller_context.json required
controller_report.md required
"""


def messages(findings: list[policy.Finding]) -> list[str]:
    return [finding.message for finding in findings]


def high_risk_candidate_text(**overrides: str) -> str:
    text = BASE_FRONTMATTER
    for key, value in overrides.items():
        text = text.replace(f"{key}: {policy.normalized_scalar(policy.parse_frontmatter(text).get(key))}", f"{key}: {value}")
    return text + BODY


def write_verified_packet(root: Path, *, review_required: bool = False, monitor: str = "") -> None:
    (root / "subagents").mkdir(parents=True, exist_ok=True)
    for name in (
        "result.md",
        "controller_context.json",
        "controller_ledger.csv",
        "controller_bootstrap_snapshot.md",
        "implementation_snapshot.md",
        "validator_report.md",
        "MANIFEST.md",
    ):
        (root / name).write_text("{}\n" if name.endswith(".json") else "ok\n", encoding="utf-8")
    (root / "finalizer_state.json").write_text(
        '{"task_key":"sprint_flow_test","final_state":"VERIFIED_COMPLETE","git_commit_decision":"COMMIT_LOCAL_PACKET","precommit_head":"abc","tracked_paths":["results/x/controller_report.md"],"manifest_sha256":"sha","job_states":{"1":"COMPLETED"}}\n',
        encoding="utf-8",
    )
    completion = f"""controller_verification_decision: VERIFIED_COMPLETE
review_required: {'true' if review_required else 'false'}
operational_completion_status: COMPLETE
experiment_adequacy_decision: PASS
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
next_required_action: RETURN_TO_PLANNER
{monitor}
"""
    report = f"""controller_run_status: COMPLETE
{completion}route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: PLANNER_DECISION_REQUIRED
diagnostic_publication_decision: LOCAL_PACKET_COMMITTED
published_files:
  - results/sprint_flow_test/controller_report.md
blocked_actions:
  - validation upload remains blocked
reason_if_not_published: none
reason_if_no_route_promotion: not authorized by controller task
"""
    (root / "completion_check.md").write_text(completion, encoding="utf-8")
    (root / "controller_report.md").write_text(report, encoding="utf-8")


def test_high_risk_system_slurm_task_does_not_require_default_planning_critic() -> None:
    findings = policy.validate_task_file(Path("prompts/shared/M99_sprint_flow.md"), high_risk_candidate_text(), strict=True)
    assert not [msg for msg in messages(findings) if "planning_review" in msg or "critic" in msg]


def test_missing_planning_review_file_does_not_block_when_planning_review_false() -> None:
    findings = policy.validate_planning_review_for_candidate(
        Path.cwd(),
        Path("prompts/shared/M99_sprint_flow.md"),
        policy.parse_frontmatter(high_risk_candidate_text()),
    )
    assert findings == []


def test_explicit_planning_review_true_keeps_legacy_critic_gate() -> None:
    text = high_risk_candidate_text(
        planning_review_required="true",
        planning_reviewer="separate_gpt_thread",
        planning_review_path="prompts/tasks/missing_planning_review.md",
        planning_review_token="null",
        planning_reviewed_commit="null",
    )
    findings = policy.validate_task_file(Path("prompts/shared/M99_sprint_flow.md"), text, strict=True)
    assert any("planning_review_token" in msg for msg in messages(findings))
    assert any("planning_reviewed_commit" in msg for msg in messages(findings))


def test_review_false_packet_does_not_need_review_md_or_reviewer_handoff(tmp_path: Path) -> None:
    write_verified_packet(tmp_path, review_required=False)
    findings = policy.validate_paths([tmp_path], strict_tasks=True)
    assert not [msg for msg in messages(findings) if "review" in msg.lower()]


def test_missing_review_md_does_not_block_next_planner_task_when_review_false(tmp_path: Path) -> None:
    write_verified_packet(tmp_path, review_required=False)
    assert not (tmp_path / "review.md").exists()
    findings = policy.validate_packet(Path.cwd(), tmp_path)
    assert not [msg for msg in messages(findings) if "review.md" in msg]


def test_explicit_review_required_keeps_independent_reviewer_handoff(tmp_path: Path) -> None:
    write_verified_packet(tmp_path, review_required=True)
    findings = policy.validate_packet(Path.cwd(), tmp_path)
    assert any("reviewer handoff" in msg for msg in messages(findings))
    (tmp_path / "review_request.md").write_text("review requested\n", encoding="utf-8")
    (tmp_path / "subagents" / "reviewer_prompt.md").write_text("read-only reviewer\n", encoding="utf-8")
    findings = policy.validate_packet(Path.cwd(), tmp_path)
    assert not [msg for msg in messages(findings) if "reviewer handoff" in msg]


def test_verified_complete_requires_outputs_terminal_jobs_aggregation_and_validators(tmp_path: Path) -> None:
    write_verified_packet(tmp_path, review_required=False)
    completion = (tmp_path / "completion_check.md").read_text(encoding="utf-8")
    (tmp_path / "completion_check.md").write_text(completion.replace("required_outputs_complete: true", "required_outputs_complete: false"), encoding="utf-8")
    findings = policy.validate_packet(Path.cwd(), tmp_path)
    assert any("required outputs are incomplete" in msg for msg in messages(findings))


def test_submitted_pending_running_monitor_states_cannot_pass_completion_gate(tmp_path: Path) -> None:
    write_verified_packet(tmp_path, review_required=False, monitor="NEEDS_MONITOR RUNNING SUBMITTED AWAITING_SACCT\n")
    findings = policy.validate_packet(Path.cwd(), tmp_path)
    assert any("monitor state" in msg for msg in messages(findings))


def test_batch4_planning_review_receipt_is_still_recognized() -> None:
    review = Path("prompts/tasks/20260721_srr_batch4_forced_fold0_training_planning_review.md")
    text = review.read_text(encoding="utf-8")
    assert "planning_review_decision: AUDITED_GO" in text
    assert "planning_review_token: BATCH4_PLANNING_AUDITED_GO" in text
    assert "reviewed_prompt_path: prompts/tasks/20260721_srr_batch4_forced_fold0_training_controller.md" in text


def test_known_bad_terminal_packet_missing_real_outputs_still_fails(tmp_path: Path) -> None:
    (tmp_path / "completion_check.md").write_text(
        """controller_verification_decision: VERIFIED_COMPLETE
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
contract_compliance_status: PASS
experiment_adequacy_decision: PASS
next_required_action: RETURN_TO_PLANNER
""",
        encoding="utf-8",
    )
    findings = policy.validate_packet(Path.cwd(), tmp_path)
    assert any("missing required files" in msg for msg in messages(findings))
