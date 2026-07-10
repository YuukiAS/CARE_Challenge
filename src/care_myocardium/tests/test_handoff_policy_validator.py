from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


VALIDATOR_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validation" / "validate_handoff_policy.py"
FINALIZER_PATH = Path(__file__).resolve().parents[3] / "scripts" / "ops" / "care_milestone_finalizer.py"
EXECUTOR_PLAN_PATH = Path(__file__).resolve().parents[3] / "scripts" / "ops" / "validate_executor_plan.py"
WATCHER_PATH = Path(__file__).resolve().parents[3] / "scripts" / "ops" / "start_care_tmux_watcher.py"
ARCH_VALIDATOR_PATH = Path(__file__).resolve().parents[3] / "scripts" / "architecture" / "validate_care_architecture_wiki.py"
RECONCILE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "architecture" / "reconcile_review_status.py"
MERGE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "ops" / "merge_care_executor_wave.py"
CREATE_HISTORY_PATH = Path(__file__).resolve().parents[3] / "scripts" / "architecture" / "create_care_history_snapshot.py"
SPEC = importlib.util.spec_from_file_location("validate_handoff_policy", VALIDATOR_PATH)
assert SPEC is not None
validator = importlib.util.module_from_spec(SPEC)
sys.modules["validate_handoff_policy"] = validator
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)
FINALIZER_SPEC = importlib.util.spec_from_file_location("care_milestone_finalizer", FINALIZER_PATH)
assert FINALIZER_SPEC is not None and FINALIZER_SPEC.loader is not None
finalizer = importlib.util.module_from_spec(FINALIZER_SPEC)
sys.modules["care_milestone_finalizer"] = finalizer
FINALIZER_SPEC.loader.exec_module(finalizer)
PLAN_SPEC = importlib.util.spec_from_file_location("validate_executor_plan", EXECUTOR_PLAN_PATH)
assert PLAN_SPEC is not None and PLAN_SPEC.loader is not None
executor_plan = importlib.util.module_from_spec(PLAN_SPEC)
sys.modules["validate_executor_plan"] = executor_plan
PLAN_SPEC.loader.exec_module(executor_plan)
WATCHER_SPEC = importlib.util.spec_from_file_location("start_care_tmux_watcher", WATCHER_PATH)
assert WATCHER_SPEC is not None and WATCHER_SPEC.loader is not None
watcher = importlib.util.module_from_spec(WATCHER_SPEC)
sys.modules["start_care_tmux_watcher"] = watcher
WATCHER_SPEC.loader.exec_module(watcher)
ARCH_SPEC = importlib.util.spec_from_file_location("validate_care_architecture_wiki", ARCH_VALIDATOR_PATH)
assert ARCH_SPEC is not None and ARCH_SPEC.loader is not None
arch_validator = importlib.util.module_from_spec(ARCH_SPEC)
sys.modules["validate_care_architecture_wiki"] = arch_validator
ARCH_SPEC.loader.exec_module(arch_validator)
RECONCILE_SPEC = importlib.util.spec_from_file_location("reconcile_review_status", RECONCILE_PATH)
assert RECONCILE_SPEC is not None and RECONCILE_SPEC.loader is not None
reconcile = importlib.util.module_from_spec(RECONCILE_SPEC)
sys.modules["reconcile_review_status"] = reconcile
RECONCILE_SPEC.loader.exec_module(reconcile)
MERGE_SPEC = importlib.util.spec_from_file_location("merge_care_executor_wave", MERGE_PATH)
assert MERGE_SPEC is not None and MERGE_SPEC.loader is not None
merge_wave = importlib.util.module_from_spec(MERGE_SPEC)
sys.modules["merge_care_executor_wave"] = merge_wave
MERGE_SPEC.loader.exec_module(merge_wave)
CREATE_HISTORY_SPEC = importlib.util.spec_from_file_location("create_care_history_snapshot", CREATE_HISTORY_PATH)
assert CREATE_HISTORY_SPEC is not None and CREATE_HISTORY_SPEC.loader is not None
create_history = importlib.util.module_from_spec(CREATE_HISTORY_SPEC)
sys.modules["create_care_history_snapshot"] = create_history
CREATE_HISTORY_SPEC.loader.exec_module(create_history)


def add_completion_contract(entry: dict[str, object], token: str = "READY_FOR_CONTROLLER_MERGE") -> dict[str, object]:
    entry.setdefault("required_completion_file", f"{entry.get('result_dir', 'results/demo')}/completion_check.md")
    entry.setdefault("required_completion_token", token)
    return entry


class TestHandoffPolicyValidator(unittest.TestCase):
    def test_controller_git_requires_split_gates_in_strict_mode(self) -> None:
        text = """---
task_type: "controller"
controller_mode: true
allow_git_commit: true
allow_git_push: true
promotion_gate: "legacy route gate"
---
# CARE Controller Task: legacy
"""
        findings = validator.validate_task_file(Path("prompts/tasks/legacy.md"), text, strict=True)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("route_promotion_gate", messages)
        self.assertIn("experiment_adequacy_gate", messages)
        self.assertIn("diagnostic_publication_gate", messages)
        self.assertTrue(all(item.severity == "error" for item in findings))

    def test_long_slurm_direct_executor_is_rejected(self) -> None:
        text = """---
task_type: "controller"
controller_mode: true
execution_mode: "direct_executor"
requires_execution_controller: false
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/demo_executor_plan.yaml"
mapper_slots: 0
mapper_required: false
architecture_impact: "none"
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
---
# Overnight long Slurm task
"""
        findings = validator.validate_task_file(Path("prompts/tasks/overnight.md"), text, strict=True)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("cannot use execution_mode: direct_executor", messages)
        self.assertIn("continuity_backend", messages)

    def test_architecture_impact_requires_mapper_and_wiki(self) -> None:
        text = """---
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/demo_executor_plan.yaml"
mapper_slots: 0
mapper_required: false
architecture_impact: "component"
wiki_update_required: false
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
---
# Component architecture task
"""
        findings = validator.validate_task_file(Path("prompts/tasks/architecture.md"), text, strict=True)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("mapper_required: true", messages)
        self.assertIn("wiki_update_required: true", messages)

    def test_auditor_subtasks_are_rejected_for_new_controller_tasks(self) -> None:
        text = """---
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/demo_executor_plan.yaml"
mapper_slots: 1
mapper_required: true
architecture_impact: "component"
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
auditor_subtasks: ["results/demo/subagents/auditor_prompt.md"]
---
# Controller
"""
        findings = validator.validate_task_file(Path("prompts/tasks/controller.md"), text, strict=True)
        self.assertTrue(any("auditor_subtasks" in item.message for item in findings))

    def test_parallel_executor_requires_plan_path(self) -> None:
        text = """---
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
executor_slots: 2
executor_count: 2
parallel_execution_allowed: true
mapper_slots: 1
mapper_required: true
architecture_impact: "component"
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
---
# Controller
"""
        findings = validator.validate_task_file(Path("prompts/tasks/controller.md"), text, strict=True)
        self.assertTrue(any("executor_plan_path" in item.message for item in findings))

    def test_diagnostic_only_controller_report_passes_with_reviewed_packet(self) -> None:
        text = """# Controller Report

route_promotion_decision: NO_PROMOTION
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
git_commit_decision: COMMIT_DIAGNOSTIC_ONLY
git_push_decision: SKIP_PUSH
published_files:
  - results/20260703_demo/controller_report.md
  - results/20260703_demo/execution_plan.md
  - scripts/evaluation/demo_diagnostic.py
blocked_actions:
  - validation packaging/upload/fold expansion/next-stage training remain blocked
next_required_action: GPT planner reviews diagnostic packet
reason_if_not_published: none
reason_if_no_route_promotion: same-split evidence did not support route promotion

diagnostic publication only; no route promotion
"""
        findings = validator.validate_controller_report(Path("results/20260703_demo/controller_report.md"), text)
        self.assertEqual(findings, [])

    def test_controller_report_rejects_push_decision(self) -> None:
        text = """# Controller Report

route_promotion_decision: NOT_REVIEWED
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_PACKET_COMMITTED_FOR_REVIEW
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: PUSH_DIAGNOSTIC_ONLY
published_files:
  - results/demo/controller_report.md
blocked_actions:
  - validation upload remains blocked
next_required_action: separate reviewer writes review.md
reason_if_not_published: none
reason_if_no_route_promotion: awaiting independent review
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("must not push" in item.message for item in findings))

    def test_diagnostic_publication_rejects_forbidden_artifacts(self) -> None:
        text = """# Controller Report

route_promotion_decision: NO_PROMOTION
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
git_commit_decision: COMMIT_DIAGNOSTIC_ONLY
git_push_decision: SKIP_PUSH
published_files:
  - results/20260703_demo/upload_ready/CARE-Myocardium-OrganAgent.zip
blocked_actions:
  - validation upload remains blocked
next_required_action: GPT planner reviews diagnostic packet
reason_if_not_published: none
reason_if_no_route_promotion: no route promoted

diagnostic publication only; no route promotion
"""
        findings = validator.validate_controller_report(Path("results/20260703_demo/controller_report.md"), text)
        self.assertTrue(any("forbidden diagnostic artifact" in item.message for item in findings))

    def test_undertrained_stop_no_signal_is_rejected(self) -> None:
        text = """# Controller Report

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: FAIL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: write revision task
reason_if_not_published: no reviewed packet selected
reason_if_no_route_promotion: actual_steps=120 and train_loop_seconds=30; STOP_NO_SIGNAL
"""
        findings = validator.validate_controller_report(Path("results/20260703_demo/controller_report.md"), text)
        self.assertTrue(any("experiment_adequacy_decision: PASS" in item.message for item in findings))
        self.assertTrue(any("route_negative_decision: STOP_SUPPORTED" in item.message for item in findings))

    def test_supported_scientific_stop_requires_adequacy_and_passes(self) -> None:
        text = """# Controller Report

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_SUPPORTED
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: return to GPT planner
reason_if_not_published: none
reason_if_no_route_promotion: fully trained variants remained below baseline; STOP_NO_SIGNAL supported
"""
        findings = validator.validate_controller_report(Path("results/20260703_demo/controller_report.md"), text)
        self.assertEqual(findings, [])

    def test_complete_unresolved_requires_next_required_action(self) -> None:
        text = """# Controller Report

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action:
reason_if_not_published: no reviewed packet selected
reason_if_no_route_promotion: evidence incomplete
"""
        findings = validator.validate_controller_report(Path("results/20260703_demo/controller_report.md"), text)
        self.assertTrue(any("next_required_action" in item.message for item in findings))

    def test_complete_controller_report_rejects_monitor_state(self) -> None:
        text = """# Controller Report

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: wait
reason_if_not_published: monitor
reason_if_no_route_promotion: PENDING_MONITOR remains
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("unresolved monitor" in item.message for item in findings))

    def test_blocked_controller_report_rejects_pending_state(self) -> None:
        text = """# Controller Report

controller_run_status: BLOCKED
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: EVIDENCE_NOT_FOUND
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: wait
reason_if_not_published: none
reason_if_no_route_promotion: job is RUNNING
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("monitor state to BLOCKED" in item.message for item in findings))

    def test_scheduler_block_requires_24_hour_threshold(self) -> None:
        text = """# Controller Report

controller_run_status: BLOCKED
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: EVIDENCE_NOT_FOUND
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: scheduler block
reason_if_not_published: none
reason_if_no_route_promotion: scheduler block while PENDING
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("24-hour threshold" in item.message for item in findings))

    def test_controller_report_rejects_internal_reviewer_and_slot_overrun(self) -> None:
        text = """# Controller Report

execution_mode: controller_supervised
controller_context.json: present
executor_slots_allowed: 1
actual_executor_slots: 2
reviewer: internal controller child resume agent
controller_run_status: INCOMPLETE
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: fix controller
reason_if_not_published: none
reason_if_no_route_promotion: none
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("executor_slots", messages)
        self.assertIn("internal recovery", messages)

    def test_running_job_outputs_missing_is_monitor_not_evidence_closeout(self) -> None:
        text = """# Controller Report

controller_run_status: INCOMPLETE
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: EVIDENCE_NOT_FOUND
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: collect evidence
reason_if_not_published: runtime output missing while job is still RUNNING
reason_if_no_route_promotion: NEEDS_EVIDENCE
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("running jobs cannot be closed" in item.message for item in findings))

    def test_chat_claimed_followup_completion_without_committed_evidence_is_rejected(self) -> None:
        text = """# Controller Report

controller_run_status: INCOMPLETE
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: EVIDENCE_NOT_FOUND
route_promotion_decision: NOT_EVALUABLE
route_negative_decision: NOT_EVALUABLE
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: find evidence
reason_if_not_published: chat/user statement finished
reason_if_no_route_promotion: none
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("from chat without committed evidence" in item.message for item in findings))

    def test_controller_report_rejects_forbidden_mapper_scan_and_stale_toolkit_report(self) -> None:
        text = """# Controller Report

controller_run_status: INCOMPLETE
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: PARTIAL
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload remains blocked
next_required_action: fix mapper
reason_if_not_published: mapper scanned raw data checkpoints
reason_if_no_route_promotion: used docs/local_install_report.md
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        messages = "\n".join(item.message for item in findings)
        self.assertIn("forbidden", messages)
        self.assertIn("local_install_report", messages)

    def test_components_csv_requires_final_output_effect_for_verified_rows(self) -> None:
        text = """component_id,branch,role,current_status,evidence_status,target_status,source_file,symbol,entrypoint,grep_key,config_keys,inputs,outputs,losses,final_output_effect,runtime_evidence,code_fingerprint_member,last_verified_milestone,review_token,notes
bad,MyoPS,test,implemented,verified,implemented,src/x.py,Sym,entry,grep,key,in,out,loss,,results/demo/result.md,fp,M9,TOKEN,note
"""
        findings = validator.validate_components_csv(Path("wiki/COMPONENTS.csv"), text)
        self.assertTrue(any("final_output_effect" in item.message for item in findings))

    def test_active_policy_rejects_retired_todo_reference(self) -> None:
        text = "Read TODO-agents-v2.md before acting.\n"
        findings = validator.validate_active_policy_doc(Path("START_HERE_FOR_GPT.md"), text)
        self.assertTrue(any("retired TODO" in item.message for item in findings))

    def test_active_policy_rejects_push_true(self) -> None:
        text = "auto_git_push: true\n"
        findings = validator.validate_active_policy_doc(Path("CONTROLLER_TASK_TEMPLATE.md"), text)
        self.assertTrue(any("enables controller/reviewer push" in item.message for item in findings))

    def test_finalizer_state_rejects_running_completion(self) -> None:
        text = """{
  "task_key": "demo",
  "required_job_ids": ["1"],
  "job_states": {"1": "RUNNING"},
  "exit_codes": {"1": "0:0"},
  "elapsed": {"1": "00:01:00"},
  "log_paths": [],
  "runtime_output_paths": [],
  "aggregation_command": "",
  "aggregation_exit_code": null,
  "validator_commands": [],
  "validator_exit_codes": [],
  "mapper_final_status": "not_requested",
  "lock_path": "results/demo/.lock",
  "git_head_before": "abc",
  "git_commit_after": null,
  "final_state": "PACKET_COMMITTED_FOR_REVIEW"
}"""
        findings = validator.validate_finalizer_state(Path("results/demo/finalizer_state.json"), text)
        self.assertTrue(any("nonterminal Slurm" in item.message or "completion" in item.message for item in findings))

    def test_finalizer_lock_release_and_retry_after_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "result"
            fixture = root / "completed.json"
            output = root / "runtime.txt"
            output.write_text("ok", encoding="utf-8")
            fixture.write_text(json.dumps({"jobs": {"1": {"state": "COMPLETED", "exit_code": "0:0", "elapsed": "00:01:00"}}}), encoding="utf-8")
            lock = root / "lock.json"
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code1 = finalizer.main(["--task-key", "demo", "--result-dir", str(result), "--required-job-id", "1", "--sacct-fixture", str(fixture), "--runtime-output-path", str(output), "--lock-path", str(lock), "--stage", "accounting"])
                code2 = finalizer.main(["--task-key", "demo", "--result-dir", str(result), "--required-job-id", "1", "--sacct-fixture", str(fixture), "--runtime-output-path", str(output), "--lock-path", str(lock), "--stage", "accounting"])
            finally:
                os.chdir(old)
            self.assertEqual(code1, 0)
            self.assertEqual(code2, 0)
            self.assertFalse(lock.exists())

    def test_finalizer_active_lock_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / "lock.json"
            lock.write_text(json.dumps({"pid": 1, "host": __import__("socket").gethostname(), "started_epoch": __import__("time").time(), "task_key": "demo"}), encoding="utf-8")
            result = root / "result"
            fixture = root / "pending.json"
            fixture.write_text(json.dumps({"jobs": {"1": {"state": "PENDING", "exit_code": "0:0", "elapsed": "00:00:00"}}}), encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = finalizer.main(["--task-key", "demo", "--result-dir", str(result), "--required-job-id", "1", "--sacct-fixture", str(fixture), "--lock-path", str(lock)])
            finally:
                os.chdir(old)
            self.assertEqual(code, 2)

    def test_finalizer_awaiting_sacct_then_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "result"
            output = root / "runtime.txt"
            output.write_text("ok", encoding="utf-8")
            fixture = root / "polls.json"
            fixture.write_text(json.dumps({"jobs": {"1": {"polls": [{"state": "AWAITING_SACCT"}, {"state": "COMPLETED", "exit_code": "0:0", "elapsed": "00:01:00"}]}}}), encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = finalizer.main(["--task-key", "demo", "--result-dir", str(result), "--required-job-id", "1", "--sacct-fixture", str(fixture), "--runtime-output-path", str(output), "--awaiting-sacct-retry-seconds", "2", "--awaiting-sacct-retry-interval", "1", "--stage", "accounting"])
            finally:
                os.chdir(old)
            state = json.loads((result / "finalizer_state.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(state["final_state"], "READY_FOR_MAPPER_FINAL")

    def test_executor_plan_rejects_overlapping_write_scope(self) -> None:
        data = {
            "version": 1,
            "max_parallel": 2,
            "executors": [
                {"id": "a", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "a", "worktree_path": "/tmp/a", "write_scope": ["x.py"], "prompt_path": "pa", "result_dir": "ra", "runtime_output_root": "oa", "slurm_job_namespace": "ja", "merge_order": 1},
                {"id": "b", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "b", "worktree_path": "/tmp/b", "write_scope": ["x.py"], "prompt_path": "pb", "result_dir": "rb", "runtime_output_root": "ob", "slurm_job_namespace": "jb", "merge_order": 2},
            ],
        }
        self.assertTrue(any("write_scope overlap" in item for item in executor_plan.validate_plan(data)))

    def test_executor_plan_allows_sequential_waves_over_slots(self) -> None:
        data = {
            "version": 1,
            "max_parallel": 1,
            "executors": [
                add_completion_contract({"id": "a", "lane": "tooling", "wave": 1, "can_run_parallel": False, "isolation_mode": "separate_worktree", "branch_name": "a", "worktree_path": "/tmp/a", "write_scope": ["x.py"], "prompt_path": "pa", "result_dir": "ra", "runtime_output_root": "oa", "slurm_job_namespace": "ja", "merge_order": 1}),
                add_completion_contract({"id": "b", "lane": "tooling", "wave": 2, "depends_on": ["a"], "can_run_parallel": False, "isolation_mode": "separate_worktree", "branch_name": "b", "worktree_path": "/tmp/b", "write_scope": ["x.py"], "prompt_path": "pb", "result_dir": "rb", "runtime_output_root": "ob", "slurm_job_namespace": "jb", "merge_order": 2}),
            ],
        }
        self.assertEqual(executor_plan.validate_plan(data), [])

    def test_watcher_does_not_exit_on_needs_monitor_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "result"
            script = root / "fake_finalizer.py"
            script.write_text(
                """import json
from pathlib import Path
p=Path('count.txt')
n=int(p.read_text()) if p.exists() else 0
p.write_text(str(n+1))
state='NEEDS_MONITOR' if n < 2 else 'READY_FOR_MAPPER_FINAL'
Path('result').mkdir(exist_ok=True)
(Path('result')/'finalizer_state.json').write_text(json.dumps({'final_state': state, 'job_states': {'1': 'RUNNING' if n < 2 else 'COMPLETED'}}))
""",
                encoding="utf-8",
            )
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = watcher.main(["--task-key", "demo", "--result-dir", str(result), "--finalizer-command", f"{sys.executable} {script}", "--foreground", "--poll-interval", "1", "--max-iterations", "4"])
            finally:
                os.chdir(old)
            receipt = json.loads((result / "tmux_watcher_receipt.json").read_text(encoding="utf-8"))
            ledger = (result / "tmux_watcher_iteration_ledger.csv").read_text(encoding="utf-8")
            self.assertEqual(code, 0)
            self.assertEqual(receipt["iterations"], 3)
            self.assertIn("NEEDS_MONITOR", ledger)
            self.assertIn("READY_FOR_MAPPER_FINAL", ledger)

    def test_finalizer_awaiting_sacct_exhaustion_is_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            watcher_script = root / "scripts/ops/start_care_tmux_watcher.py"
            watcher_script.parent.mkdir(parents=True)
            watcher_script.write_text(
                """import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--task-key')
p.add_argument('--result-dir')
p.add_argument('--session-name')
p.add_argument('--receipt-path')
p.add_argument('--finalizer-command')
p.add_argument('--lock-path')
p.add_argument('--log-path')
p.add_argument('--poll-interval')
args=p.parse_args()
receipt={'session_name': args.session_name, 'watcher_final_status': 'STARTED', 'log_path': args.log_path, 'lock_path': args.lock_path, 'result_dir': args.result_dir}
Path(args.receipt_path).parent.mkdir(parents=True, exist_ok=True)
Path(args.receipt_path).write_text(json.dumps(receipt))
print(args.session_name)
""",
                encoding="utf-8",
            )
            result = root / "result"
            fixture = root / "awaiting.json"
            fixture.write_text(json.dumps({"jobs": {"1": {"state": "AWAITING_SACCT"}}}), encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = finalizer.main(["--task-key", "demo", "--result-dir", str(result), "--required-job-id", "1", "--sacct-fixture", str(fixture), "--awaiting-sacct-retry-seconds", "0", "--stage", "accounting"])
            finally:
                os.chdir(old)
            state = json.loads((result / "finalizer_state.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(state["final_state"], "AWAITING_SACCT_RETRY_EXHAUSTED")
            self.assertTrue(state["retryable"])
            self.assertEqual(state["retry_backend"], "tmux_watcher")
            self.assertEqual(state["next_retry_job_id_or_tmux_session"], "care_demo_accounting_retry")
            self.assertTrue((result / "accounting_continuation_receipt.json").is_file())

    def test_executor_plan_rejects_nested_write_scope_overlap(self) -> None:
        data = {"version": 1, "max_parallel": 2, "executors": [
            {"id": "a", "lane": "tooling", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "a", "worktree_path": "/tmp/a", "write_scope": ["wiki"], "prompt_path": "pa", "result_dir": "ra", "runtime_output_root": "oa", "slurm_job_namespace": "ja", "merge_order": 1},
            {"id": "b", "lane": "tooling", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "b", "worktree_path": "/tmp/b", "write_scope": ["wiki/history"], "prompt_path": "pb", "result_dir": "rb", "runtime_output_root": "ob", "slurm_job_namespace": "jb", "merge_order": 2},
        ]}
        self.assertTrue(any("write_scope overlap" in item for item in executor_plan.validate_plan(data)))

    def test_executor_plan_rejects_lowercase_myops_cine_without_isolation(self) -> None:
        data = {"version": 1, "max_parallel": 2, "executors": [
            {"id": "left", "lane": "myops", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "a", "worktree_path": "/tmp/a", "write_scope": ["src/a.py"], "prompt_path": "pa", "result_dir": "ra", "runtime_output_root": "oa", "slurm_job_namespace": "ja", "merge_order": 1},
            {"id": "right", "lane": "cine", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "b", "worktree_path": "/tmp/b", "write_scope": ["src/b.py"], "prompt_path": "pb", "result_dir": "rb", "runtime_output_root": "ob", "slurm_job_namespace": "jb", "merge_order": 2},
        ]}
        self.assertTrue(any("MyoPS/Cine" in item for item in executor_plan.validate_plan(data)))

    def test_executor_plan_rejects_duplicate_worktree_branch_merge_order_and_cycle(self) -> None:
        data = {"version": 1, "max_parallel": 2, "executors": [
            {"id": "a", "lane": "tooling", "wave": 1, "depends_on": ["b"], "can_run_parallel": False, "isolation_mode": "separate_worktree", "branch_name": "same", "worktree_path": "/tmp/same", "write_scope": ["a"], "prompt_path": "pa", "result_dir": "same_result", "runtime_output_root": "oa", "slurm_job_namespace": "same_ns", "merge_order": 1},
            {"id": "b", "lane": "tooling", "wave": 1, "depends_on": ["a"], "can_run_parallel": False, "isolation_mode": "separate_worktree", "branch_name": "same", "worktree_path": "/tmp/same/child", "write_scope": ["b"], "prompt_path": "pb", "result_dir": "same_result/child", "runtime_output_root": "ob", "slurm_job_namespace": "same_ns", "merge_order": 1},
        ]}
        messages = "\n".join(executor_plan.validate_plan(data))
        self.assertIn("branch_name", messages)
        self.assertIn("worktree_path", messages)
        self.assertIn("merge_order", messages)
        self.assertIn("dependency cycle", messages)

    def test_executor_plan_accepts_valid_isolated_two_executor_wave(self) -> None:
        data = {"version": 1, "max_parallel": 2, "executors": [
            add_completion_contract({"id": "myops_worker", "lane": "myops", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "myops", "worktree_path": "/tmp/myops", "write_scope": ["src/myops"], "prompt_path": "pa", "result_dir": "ra", "runtime_output_root": "oa", "slurm_job_namespace": "ja", "lock_path": "la", "log_path": "loga", "merge_order": 1, "isolation_proof": "separate source/runtime paths"}),
            add_completion_contract({"id": "cine_worker", "lane": "cine", "wave": 1, "can_run_parallel": True, "isolation_mode": "separate_worktree", "branch_name": "cine", "worktree_path": "/tmp/cine", "write_scope": ["src/cine"], "prompt_path": "pb", "result_dir": "rb", "runtime_output_root": "ob", "slurm_job_namespace": "jb", "lock_path": "lb", "log_path": "logb", "merge_order": 2, "isolation_proof": "separate source/runtime paths"}),
        ]}
        self.assertEqual(executor_plan.validate_plan(data), [])

    def test_history_m8_proposal_and_todo_m10_case_are_validated(self) -> None:
        repo = Path(__file__).resolve().parents[3]
        proposal = repo / "wiki/history/M08/components/proposal.md"
        manifest = repo / "wiki/history/MIGRATION_MANIFEST.csv"
        self.assertIn("1.5 Proposal", proposal.read_text(encoding="utf-8"))
        self.assertIn("todo-m10.md", manifest.read_text(encoding="utf-8"))
        self.assertNotIn("TODO-M10.md", manifest.read_text(encoding="utf-8"))

    def test_history_comparison_not_generic_placeholder(self) -> None:
        repo = Path(__file__).resolve().parents[3]
        errors = arch_validator.validate_history(repo)
        self.assertFalse(any("generic placeholder" in item for item in errors), errors)

    def test_current_graph_node_component_id_consistency(self) -> None:
        repo = Path(__file__).resolve().parents[3]
        self.assertEqual(arch_validator.validate_architecture(repo), [])

    def test_gpt_m10_planning_missing_history_reading_fails(self) -> None:
        text = """---
task_type: "controller"
controller_mode: true
execution_mode: "controller_supervised"
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: "prompts/tasks/m10_executor_plan.yaml"
mapper_slots: 1
mapper_required: true
architecture_impact: "system"
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: false
continuity_backend: "none"
review_mode: "independent_thread"
reviewer: "separate_readonly"
---
# M10 redesign
"""
        findings = validator.validate_task_file(Path("prompts/tasks/M10_demo.md"), text, strict=True)
        self.assertTrue(any("history_files_read" in item.message for item in findings))

    def test_post_review_token_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki/history/M09").mkdir(parents=True)
            (root / "wiki").mkdir(exist_ok=True)
            (root / "wiki/README.md").write_text("# Wiki\n", encoding="utf-8")
            (root / "wiki/LINEAGE.md").write_text("# Lineage\n", encoding="utf-8")
            (root / "wiki/history/M09/snapshot.yaml").write_text("later_status_update: none\n", encoding="utf-8")
            review = root / "review.md"
            review.write_text("review token: M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY\nreview decision: ready\nreviewed commit: abc\nroute status: no promotion\n", encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = reconcile.main(["--review-md", str(review), "--no-generate"])
            finally:
                os.chdir(old)
            self.assertEqual(code, 0)
            self.assertIn("M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY", (root / "wiki/README.md").read_text(encoding="utf-8"))

    def test_post_review_token_reconciliation_accepts_m10(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wiki/history/M10").mkdir(parents=True)
            (root / "wiki").mkdir(exist_ok=True)
            (root / "wiki/README.md").write_text("# Wiki\n", encoding="utf-8")
            (root / "wiki/LINEAGE.md").write_text("# Lineage\n", encoding="utf-8")
            (root / "wiki/history/M10/snapshot.yaml").write_text("later_status_update: none\n", encoding="utf-8")
            review = root / "review.md"
            review.write_text("review token: M10_AUDITED_READY_DIAGNOSTIC_ONLY\nreview decision: ready\nreviewed commit: abc\nroute status: no promotion\n", encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = reconcile.main(["--review-md", str(review), "--history-version", "M10", "--no-generate"])
            finally:
                os.chdir(old)
            self.assertEqual(code, 0)
            self.assertIn("M10_AUDITED_READY_DIAGNOSTIC_ONLY", (root / "wiki/history/M10/snapshot.yaml").read_text(encoding="utf-8"))

    def test_create_history_snapshot_m10_dry_run(self) -> None:
        repo = Path(__file__).resolve().parents[3]
        code = create_history.main(["--milestone", "M10", "--dry-run"])
        self.assertEqual(code, 0)

    def test_controller_packet_missing_controller_report_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp) / "results/demo_controller"
            (packet / "subagents").mkdir(parents=True)
            for rel in validator.CONTROLLER_PACKET_REQUIRED_FILES:
                if rel == "controller_report.md":
                    continue
                path = packet / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("PACKET_COMMITTED_FOR_REVIEW\n" if rel == "completion_check.md" else "{}\n", encoding="utf-8")
            findings = validator.validate_controller_packet_dir(packet)
            self.assertTrue(any("controller_report.md" in item.message for item in findings))

    def test_merge_conflict_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args: str) -> None:
                cp = __import__("subprocess").run(["git", *args], cwd=root, text=True, stdout=__import__("subprocess").PIPE, stderr=__import__("subprocess").PIPE)
                self.assertEqual(cp.returncode, 0, cp.stderr or cp.stdout)
            git("init", "-b", "main")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            (root / "file.txt").write_text("base\n", encoding="utf-8")
            git("add", "file.txt")
            git("commit", "-m", "base")
            git("checkout", "-b", "executor_branch")
            (root / "file.txt").write_text("branch\n", encoding="utf-8")
            (root / "results/e/result").mkdir(parents=True)
            (root / "results/e/result/completion_check.md").write_text("READY_FOR_CONTROLLER_MERGE\n", encoding="utf-8")
            git("add", "file.txt", "results/e/result/completion_check.md")
            git("commit", "-m", "branch")
            git("checkout", "main")
            (root / "file.txt").write_text("main\n", encoding="utf-8")
            git("commit", "-am", "main")
            plan = root / "plan.yaml"
            plan.write_text("""version: 1
max_parallel: 1
executors:
  - id: e
    lane: tooling
    wave: 1
    depends_on: []
    blocking: true
    can_run_parallel: false
    isolation_mode: separate_worktree
    branch_name: executor_branch
    worktree_path: .
    read_scope: []
    write_scope:
      - file.txt
    result_dir: results/e/result
    prompt_path: results/e/prompt.md
    runtime_output_root: results/e/runtime
    slurm_job_namespace: e
    lock_path: results/e/lock
    log_path: results/e/log
    required_completion_file: results/e/result/completion_check.md
    required_completion_token: READY_FOR_CONTROLLER_MERGE
    merge_order: 1
""", encoding="utf-8")
            git("add", "plan.yaml")
            git("commit", "-m", "add packet")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = merge_wave.main(["--plan", str(plan), "--wave", "1"])
            finally:
                os.chdir(old)
            receipt = json.loads((root / "results/executor_wave_receipts/wave_1_merge_receipt.json").read_text(encoding="utf-8"))
            self.assertNotEqual(code, 0)
            self.assertEqual(receipt["merge_state"], "NEEDS_REVISION_PARALLEL_MERGE_CONFLICT")

    def test_merge_helper_rejects_incomplete_completion_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args: str) -> None:
                cp = __import__("subprocess").run(["git", *args], cwd=root, text=True, stdout=__import__("subprocess").PIPE, stderr=__import__("subprocess").PIPE)
                self.assertEqual(cp.returncode, 0, cp.stderr or cp.stdout)

            git("init", "-b", "main")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            (root / "base.txt").write_text("base\n", encoding="utf-8")
            git("add", "base.txt")
            git("commit", "-m", "base")
            git("checkout", "-b", "executor_branch")
            (root / "results/e/result").mkdir(parents=True)
            (root / "results/e/result/completion_check.md").write_text("NEEDS_MONITOR\n", encoding="utf-8")
            git("add", "results/e/result/completion_check.md")
            git("commit", "-m", "monitor packet")
            git("checkout", "main")
            plan = root / "plan.yaml"
            plan.write_text("""version: 1
max_parallel: 1
executors:
  - id: e
    lane: tooling
    wave: 1
    depends_on: []
    blocking: true
    can_run_parallel: false
    isolation_mode: separate_worktree
    branch_name: executor_branch
    worktree_path: .
    read_scope: []
    write_scope:
      - results/e/result
    result_dir: results/e/result
    prompt_path: results/e/prompt.md
    runtime_output_root: results/e/runtime
    slurm_job_namespace: e
    lock_path: results/e/lock
    log_path: results/e/log
    required_completion_file: results/e/result/completion_check.md
    required_completion_token: READY_FOR_CONTROLLER_MERGE
    merge_order: 1
""", encoding="utf-8")
            git("add", "plan.yaml")
            git("commit", "-m", "add plan")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = merge_wave.main(["--plan", str(plan), "--wave", "1"])
            finally:
                os.chdir(old)
            self.assertNotEqual(code, 0)
            receipt = json.loads((root / "results/executor_wave_receipts/wave_1_merge_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["merge_state"], "NEEDS_EVIDENCE")
            self.assertIn("NEEDS_MONITOR", receipt["failure_reason"])

    def test_merge_helper_reads_packets_from_separate_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            work1 = Path(tmp) / "work1"
            work2 = Path(tmp) / "work2"
            root.mkdir()

            def git(cwd: Path, *args: str) -> None:
                cp = __import__("subprocess").run(["git", *args], cwd=cwd, text=True, stdout=__import__("subprocess").PIPE, stderr=__import__("subprocess").PIPE)
                self.assertEqual(cp.returncode, 0, cp.stderr or cp.stdout)

            git(root, "init", "-b", "main")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Test")
            (root / "base.txt").write_text("base\n", encoding="utf-8")
            git(root, "add", "base.txt")
            git(root, "commit", "-m", "base")
            git(root, "worktree", "add", "-b", "exec1", str(work1), "HEAD")
            git(root, "worktree", "add", "-b", "exec2", str(work2), "HEAD")
            for work, eid in ((work1, "e1"), (work2, "e2")):
                git(work, "config", "user.email", "test@example.com")
                git(work, "config", "user.name", "Test")
                packet = work / f"results/{eid}/result"
                packet.mkdir(parents=True)
                (packet / "completion_check.md").write_text("READY_FOR_CONTROLLER_MERGE\n", encoding="utf-8")
                (packet / "result.md").write_text(f"{eid} done\n", encoding="utf-8")
                git(work, "add", f"results/{eid}/result/completion_check.md", f"results/{eid}/result/result.md")
                git(work, "commit", "-m", f"{eid} packet")
            self.assertFalse((root / "results/e1/result/completion_check.md").exists())
            plan = root / "plan.yaml"
            plan.write_text(f"""version: 1
max_parallel: 2
executors:
  - id: e1
    lane: tooling
    wave: 1
    depends_on: []
    blocking: true
    can_run_parallel: false
    isolation_mode: separate_worktree
    branch_name: exec1
    worktree_path: {work1}
    read_scope: []
    write_scope:
      - results/e1/result
    result_dir: results/e1/result
    prompt_path: results/e1/prompt.md
    runtime_output_root: results/e1/runtime
    slurm_job_namespace: e1
    lock_path: results/e1/lock
    log_path: results/e1/log
    required_completion_file: results/e1/result/completion_check.md
    required_completion_token: READY_FOR_CONTROLLER_MERGE
    merge_order: 1
  - id: e2
    lane: tooling
    wave: 1
    depends_on: []
    blocking: true
    can_run_parallel: false
    isolation_mode: separate_worktree
    branch_name: exec2
    worktree_path: {work2}
    read_scope: []
    write_scope:
      - results/e2/result
    result_dir: results/e2/result
    prompt_path: results/e2/prompt.md
    runtime_output_root: results/e2/runtime
    slurm_job_namespace: e2
    lock_path: results/e2/lock
    log_path: results/e2/log
    required_completion_file: results/e2/result/completion_check.md
    required_completion_token: READY_FOR_CONTROLLER_MERGE
    merge_order: 2
""", encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = merge_wave.main(["--plan", str(plan), "--wave", "1"])
            finally:
                os.chdir(old)
            self.assertEqual(code, 0)
            self.assertTrue((root / "results/e1/result/completion_check.md").is_file())
            self.assertTrue((root / "results/e2/result/completion_check.md").is_file())
            receipt = json.loads((root / "results/executor_wave_receipts/wave_1_merge_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["merge_state"], "MERGED")
            self.assertEqual(receipt["merged_executors"], ["e1", "e2"])

    def test_components_csv_rejects_scaffold_marked_implemented(self) -> None:
        text = """component_id,branch,role,current_status,evidence_status,target_status,source_file,symbol,entrypoint,grep_key,config_keys,inputs,outputs,losses,final_output_effect,runtime_evidence,code_fingerprint_member,last_verified_milestone,review_token,notes
bad,MyoPS,scaffold module,implemented,unverified,implemented,src/x.py,Sym,entry,grep,key,in,out,loss,effect,,fp,M9,TOKEN,scaffold only
"""
        findings = validator.validate_components_csv(Path("wiki/COMPONENTS.csv"), text)
        self.assertTrue(any("scaffold" in item.message for item in findings))

    def test_architecture_yaml_requires_stale_on_fingerprint_mismatch(self) -> None:
        text = """architecture_version: demo
review_token: TOKEN
code_fingerprint: old
fingerprint_status: mismatch
nodes:
  - id: a
edges:
  - from: a
    to: a
"""
        findings = validator.validate_architecture_yaml(Path("wiki/architecture.yaml"), text)
        self.assertTrue(any("stale" in item.message for item in findings))

    def test_review_cannot_support_route_negative_without_training_fields(self) -> None:
        text = """# Review

experiment_adequacy_decision: PASS
route_negative_decision: STOP_SUPPORTED
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED

The route is stopped.
"""
        findings = validator.validate_review_file(Path("results/20260703_demo/review.md"), text)
        self.assertTrue(any("actual_steps" in item.message for item in findings))

    def test_medium_risk_executor_git_without_review_warns(self) -> None:
        text = """---
task_type: "execution"
risk_level: "medium"
allow_git_commit: true
review_required: false
---
# Task
"""
        findings = validator.validate_task_file(Path("prompts/tasks/executor.md"), text, strict=False)
        self.assertTrue(any("review_required" in item.message for item in findings))
        self.assertTrue(all(item.severity == "warning" for item in findings))

    def test_validate_paths_reads_markdown_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "controller_report.md"
            path.write_text(
                """route_promotion_decision: NO_PROMOTION
controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PARTIAL
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
diagnostic_publication_decision: PUBLISH_REVIEWED_DIAGNOSTIC_PACKET
git_commit_decision: COMMIT_DIAGNOSTIC_ONLY
git_push_decision: SKIP_PUSH
published_files:
  - results/20260703_demo/result.md
blocked_actions:
  - validation upload remains blocked
next_required_action: GPT planner reviews diagnostic packet
reason_if_not_published: none
reason_if_no_route_promotion: no route promoted

diagnostic publication only; no route promotion
""",
                encoding="utf-8",
            )
            findings = validator.validate_paths([Path(tmp_dir)])
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
