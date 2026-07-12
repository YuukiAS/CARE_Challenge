from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module("validate_handoff_policy_retry_tests", REPO / "scripts/validation/validate_handoff_policy.py")
executor_plan = load_module("validate_executor_plan_retry_tests", REPO / "scripts/ops/validate_executor_plan.py")
finalizer = load_module("care_milestone_finalizer_retry_tests", REPO / "scripts/ops/care_milestone_finalizer.py")
watcher = load_module("start_care_tmux_watcher_retry_tests", REPO / "scripts/ops/start_care_tmux_watcher.py")
training_chain = load_module("submit_care_training_chain_retry_tests", REPO / "scripts/ops/submit_care_training_chain.py")


def slurm_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": "e1",
        "lane": "myops",
        "wave": 1,
        "depends_on": [],
        "can_run_parallel": False,
        "isolation_mode": "separate_worktree",
        "branch_name": "b1",
        "worktree_path": "/tmp/e1",
        "write_scope": ["src/train.py"],
        "prompt_path": "results/demo/subagents/e1.md",
        "result_dir": "results/demo/executors/e1",
        "runtime_output_root": "results/demo/runtime/e1",
        "slurm_job_namespace": "demo_e1",
        "lock_path": "results/demo/locks/e1.lock",
        "log_path": "results/demo/logs/e1.log",
        "merge_order": 1,
        "required_completion_file": "results/demo/executors/e1/completion_check.md",
        "required_completion_token": "READY_FOR_CONTROLLER_MERGE",
        "slurm_dependency_chain": ["D0", "D1"],
        "finalizer_dependency_policy": "afterany_all_wave_job_ids",
        "slurm_dependency_policy": {"training_dependency": "afterok", "finalizer_dependency": "afterany"},
        "retry_policy": {
            "operational_retry_allowed": True,
            "same_executor_attempt": True,
            "max_startup_retries": 2,
            "max_preemption_retries": 2,
            "max_unknown_retries": 0,
            "require_same_code_hash": True,
            "require_same_config_hash": True,
            "require_same_split_hash": True,
            "failed_attempt_training_credit": "zero",
        },
        "preflight": {
            "required": True,
            "command": "python scripts/ops/run_care_training_preflight.py --help",
            "receipt_path": "results/demo/executors/e1/preflight_receipt.json",
        },
        "retry_ledger_path": "results/demo/executors/e1/replacement_job_ledger.csv",
    }
    entry.update(overrides)
    return entry


class TestOperationalRetryPolicy(unittest.TestCase):
    def test_slurm_executor_requires_afterok_training_afterany_finalizer(self) -> None:
        plan = {"version": 1, "max_parallel": 1, "executors": [slurm_entry()]}
        self.assertEqual(executor_plan.validate_plan(plan), [])

    def test_training_afterany_without_independent_reason_fails(self) -> None:
        bad = slurm_entry(slurm_dependency_policy={"training_dependency": "afterany", "finalizer_dependency": "afterany"})
        messages = "\n".join(executor_plan.validate_plan({"version": 1, "max_parallel": 1, "executors": [bad]}))
        self.assertIn("training_dependency must be afterok", messages)

    def test_controller_auth_request_requires_scope_change_fields(self) -> None:
        text = """# Controller Report

controller_run_status: BLOCKED
operational_completion_status: INCOMPLETE
experiment_adequacy_decision: EVIDENCE_NOT_FOUND
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: DO_NOT_PUBLISH
git_commit_decision: SKIP_COMMIT
git_push_decision: SKIP_PUSH
published_files:
blocked_actions:
  - validation upload
next_required_action: obtain explicit authorization after ModuleNotFoundError environment repair
reason_if_not_published: none
reason_if_no_route_promotion: no execution
"""
        findings = validator.validate_controller_report(Path("results/demo/controller_report.md"), text)
        self.assertTrue(any("required scope-change fields" in item.message for item in findings))

    def test_missing_mpmath_failure_is_retryable_same_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "result"
            log = root / "job.log"
            log.write_text("ModuleNotFoundError: No module named 'mpmath'\n", encoding="utf-8")
            fixture = root / "jobs.json"
            fixture.write_text(json.dumps({"jobs": {"58644072": {"state": "FAILED", "exit_code": "1:0", "elapsed": "00:11:04"}}}), encoding="utf-8")
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = finalizer.main([
                    "--task-key", "demo",
                    "--result-dir", str(result),
                    "--required-job-id", "58644072",
                    "--sacct-fixture", str(fixture),
                    "--log-path", str(log),
                    "--stage", "accounting",
                ])
            finally:
                os.chdir(old)
            state = json.loads((result / "finalizer_state.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(state["final_state"], "OPERATIONAL_RETRY_REQUIRED")
            self.assertEqual(state["failure_class"], "STARTUP_ENVIRONMENT_FAILURE")
            self.assertTrue(state["retryable"])
            self.assertEqual(state["suggested_next_state"], "HAND_BACK_TO_CONTROLLER_FOR_SAME_SCOPE_RETRY")
            self.assertEqual(state["job_attempt_lineage"][0]["training_credit"], "zero")

    def test_watcher_hands_retryable_failure_back_to_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "result"
            script = root / "fake_finalizer.py"
            script.write_text(
                "import json\nfrom pathlib import Path\nPath('result').mkdir(exist_ok=True)\n"
                "Path('result/finalizer_state.json').write_text(json.dumps({'final_state':'OPERATIONAL_RETRY_REQUIRED','job_states':{'1':'FAILED'}}))\n",
                encoding="utf-8",
            )
            old = Path.cwd()
            try:
                import os

                os.chdir(root)
                code = watcher.main([
                    "--task-key", "demo",
                    "--result-dir", str(result),
                    "--finalizer-command", f"{sys.executable} {script}",
                    "--foreground",
                    "--poll-interval", "1",
                    "--max-iterations", "1",
                ])
            finally:
                os.chdir(old)
            receipt = json.loads((result / "tmux_watcher_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(receipt["watcher_final_status"], "HAND_BACK_TO_CONTROLLER_FOR_SAME_SCOPE_RETRY")

    def test_training_chain_yaml_fallback_supports_clean_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "chain.yaml"
            manifest.write_text(
                """executor_id: m10_myops_training_executor
attempt_number: 2
scope_changed: false
stages:
  - id: D0
    script: jobs/src/d0.sh
  - id: D1
    script: jobs/src/d1.sh
    requires_success_of: [D0]
""",
                encoding="utf-8",
            )
            data = training_chain.load_yaml_fallback(manifest)
            self.assertEqual(data["executor_id"], "m10_myops_training_executor")
            self.assertEqual(data["attempt_number"], "2")
            self.assertFalse(data["scope_changed"])
            self.assertEqual(data["stages"][1]["requires_success_of"], ["D0"])
            self.assertEqual(training_chain.validate_manifest(data), [])


if __name__ == "__main__":
    unittest.main()
