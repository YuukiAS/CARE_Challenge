from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from scripts.validation.validate_srr_v25_anti_laziness import (
    check_required_file_names,
    check_runtime_call_trace,
    identity_fallback_matches_anchor,
    unsupported_claim_issues,
)


class TestSRRV25AntiLazinessValidator(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
