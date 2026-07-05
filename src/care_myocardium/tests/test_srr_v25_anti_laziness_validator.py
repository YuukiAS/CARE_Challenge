from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import torch

from scripts.validation.validate_srr_v25_anti_laziness import (
    check_completion_check_before_final_review,
    check_controller_report_schema,
    check_required_file_names,
    check_runtime_call_trace,
    check_task_graph_consistency,
    check_training_evidence_adequacy,
    identity_fallback_matches_anchor,
    main as validator_main,
    run_checks,
    unsupported_claim_issues,
)


class TestSRRV25AntiLazinessValidator(unittest.TestCase):
    def test_missing_required_result_directory_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            task_dir.mkdir(parents=True)
            controller = task_dir / "controller.md"
            controller.write_text("1. `prompts/tasks/20260704_missing.md`\n")
            (task_dir / "20260704_missing.md").write_text("## Required Outputs\n\n- `result.md`\n")
            (root / "results").mkdir()

            issues = check_required_file_names(root, controller, root / "results")

        self.assertTrue(any(issue.code == "REQUIRED_RESULT_DIR_MISSING" for issue in issues))

    def test_required_file_name_checker_rejects_similar_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            result_dir = root / "results" / "20260704_example"
            task_dir.mkdir(parents=True)
            result_dir.mkdir(parents=True)
            controller = task_dir / "controller.md"
            controller.write_text("1. `prompts/tasks/20260704_example.md`\n")
            (task_dir / "20260704_example.md").write_text(
                "## Required Outputs\n\n- `result.md`\n- `same_split_metrics.md`\n"
            )
            (result_dir / "result.md").write_text("ok")
            (result_dir / "sameSplitMetrics.md").write_text("wrong name")

            issues = check_required_file_names(root, controller, root / "results")

        self.assertTrue(any(issue.code == "REQUIRED_FILE_MISSING" for issue in issues))

    def test_task_graph_mismatch_between_controller_report_and_results_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            controller_results = root / "results" / "20260704_controller"
            (root / "results" / "20260704_a").mkdir(parents=True)
            controller_results.mkdir(parents=True)
            task_dir.mkdir(parents=True)
            controller = task_dir / "20260704_controller.md"
            controller.write_text(
                "\n".join(
                    [
                        "1. `prompts/tasks/20260704_a.md`",
                        "2. `prompts/tasks/20260704_b.md`",
                    ]
                )
            )
            (controller_results / "controller_report.md").write_text(
                "## Executor Subtask List\n\n| subtask | status | result path |\n| --- | --- | --- |\n| `20260704_a` | `EXECUTED_UNAUDITED` | `results/20260704_a/result.md` |\n"
            )

            issues = check_task_graph_consistency(root, controller, root / "results")

        codes = {issue.code for issue in issues}
        self.assertIn("CONTROLLER_REPORT_SUBTASK_MISSING", codes)
        self.assertIn("TASK_GRAPH_RESULT_DIR_MISSING", codes)

    def test_final_review_without_completion_check_readiness_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            task_dir.mkdir(parents=True)
            controller = task_dir / "20260704_controller.md"
            controller.write_text(
                "\n".join(
                    [
                        "1. `prompts/tasks/20260704_srr_v25_completion_check.md`",
                        "2. `prompts/tasks/20260704_srr_v25_final_readonly_audit.md`",
                    ]
                )
            )
            (root / "results").mkdir()

            issues = check_completion_check_before_final_review(controller, root / "results")

        self.assertTrue(any(issue.code == "COMPLETION_CHECK_READINESS_MISSING" for issue in issues))

    def test_completion_check_ready_token_passes_final_review_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            decision_dir = root / "results" / "20260704_srr_v25_completion_check"
            task_dir.mkdir(parents=True)
            decision_dir.mkdir(parents=True)
            controller = task_dir / "20260704_controller.md"
            controller.write_text(
                "\n".join(
                    [
                        "1. `prompts/tasks/20260704_srr_v25_completion_check.md`",
                        "2. `prompts/tasks/20260704_srr_v25_final_readonly_audit.md`",
                    ]
                )
            )
            (decision_dir / "decision.md").write_text("decision: READY_FOR_FINAL_AUDIT\n")

            issues = check_completion_check_before_final_review(controller, root / "results")

        self.assertEqual(issues, [])

    def test_controller_report_missing_terminal_schema_field_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            controller_results = root / "results" / "20260704_controller"
            task_dir.mkdir(parents=True)
            controller_results.mkdir(parents=True)
            controller = task_dir / "20260704_controller.md"
            controller.write_text("")
            (controller_results / "controller_report.md").write_text("controller_run_status: COMPLETE\n")

            issues = check_controller_report_schema(controller, root / "results")

        self.assertTrue(any(issue.code == "CONTROLLER_REPORT_FIELD_MISSING" for issue in issues))

    def test_strict_mode_is_default_and_diagnostic_non_strict_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            task_dir.mkdir(parents=True)
            controller = task_dir / "20260704_controller.md"
            controller.write_text("1. `prompts/tasks/20260704_missing.md`\n")
            (task_dir / "20260704_missing.md").write_text("## Required Outputs\n\n- `result.md`\n")
            (root / "results").mkdir()

            with redirect_stdout(StringIO()):
                strict_exit = validator_main(["--repo-root", str(root), "--controller", str(controller), "--results-root", str(root / "results")])
            with redirect_stdout(StringIO()):
                diagnostic_exit = validator_main(
                    [
                        "--repo-root",
                        str(root),
                        "--controller",
                        str(controller),
                        "--results-root",
                        str(root / "results"),
                        "--diagnostic-non-strict",
                    ]
                )

        self.assertEqual(strict_exit, 1)
        self.assertEqual(diagnostic_exit, 0)

    def test_smoke_scale_training_cannot_support_completion_or_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / "prompts" / "tasks"
            controller_results = root / "results" / "20260704_controller"
            task_dir.mkdir(parents=True)
            controller_results.mkdir(parents=True)
            controller = task_dir / "20260704_controller.md"
            controller.write_text("")
            (controller_results / "controller_report.md").write_text(
                "\n".join(
                    [
                        "report_status: `COMPLETE_DIAGNOSTIC`",
                        "Result: `actual_optimizer_steps=6`, `eval_cases=4`.",
                        "The bounded matrix is used as full route evidence.",
                        "route_negative_decision: STOP_CURRENT_BOUNDED_PACKET_ONLY",
                    ]
                )
            )

            issues = check_training_evidence_adequacy(controller, root / "results")

        self.assertTrue(any(issue.code == "SMOKE_SCALE_TRAINING_INADEQUATE" for issue in issues))

    def test_utility_only_prototype_builder_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = root / "src" / "care_myocardium" / "models"
            train_dir = root / "scripts" / "training"
            loss_dir = root / "src" / "care_myocardium" / "losses"
            model_dir.mkdir(parents=True)
            train_dir.mkdir(parents=True)
            loss_dir.mkdir(parents=True)
            (model_dir / "proposal_prototypes.py").write_text("def build_prototype_bank_from_labeled_features():\n    pass\n")
            (model_dir / "srr_propref.py").write_text("class Model:\n    pass\n")
            (model_dir / "srr_v2_unet.py").write_text("")
            (model_dir / "srr_blocks.py").write_text("")
            (loss_dir / "srr_losses.py").write_text("")
            (train_dir / "run_srr_propref_myops_fold0.py").write_text("def train():\n    pass\n")

            issues = check_runtime_call_trace(root)

        self.assertTrue(any(issue.code == "UTILITY_ONLY_NOT_CALLED" for issue in issues))

    def test_supported_claim_without_runtime_evidence_is_detected(self) -> None:
        text = "claim.prototype_bank: SUPPORTED by implementation intent only"
        issues = unsupported_claim_issues(text, "fixture.md")

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "CLAIM_WITHOUT_RUNTIME_EVIDENCE")

    def test_identity_fallback_formula_reproduces_anchor_when_gate_closed(self) -> None:
        anchor = torch.randn(1, 6, 2, 2, 2)
        delta = torch.randn_like(anchor)
        gate = torch.zeros_like(anchor)

        final = identity_fallback_matches_anchor(anchor, gate, delta)

        self.assertTrue(torch.equal(final, anchor))

    def test_current_20260704_bad_packet_fails_hard_gate_regression(self) -> None:
        repo = Path.cwd()
        controller = repo / "prompts" / "tasks" / "20260704_srr_v25_full_completion_goal.md"
        issues = run_checks(repo, controller, repo / "results")
        messages = "\n".join(f"{issue.code}: {issue.message}" for issue in issues)

        self.assertIn("20260704_cine_temporal_dictionary_integration", messages)
        self.assertIn("20260704_srr_v25_completion_check", messages)
        self.assertTrue(any(issue.code == "COMPLETION_CHECK_READINESS_MISSING" for issue in issues))
        self.assertTrue(any(issue.code == "SMOKE_SCALE_TRAINING_INADEQUATE" for issue in issues))


if __name__ == "__main__":
    unittest.main()
