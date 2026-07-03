from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


VALIDATOR_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validation" / "validate_handoff_policy.py"
SPEC = importlib.util.spec_from_file_location("validate_handoff_policy", VALIDATOR_PATH)
assert SPEC is not None
validator = importlib.util.module_from_spec(SPEC)
sys.modules["validate_handoff_policy"] = validator
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


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
git_push_decision: PUSH_DIAGNOSTIC_ONLY
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
