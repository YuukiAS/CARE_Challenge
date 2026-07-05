from __future__ import annotations

import unittest
from argparse import Namespace

import torch

from src.care_myocardium.models.srr_propref import BaselinePreservingResidualGate, SRRProposeRefineMyoPS


class TestSRRBaselineGate(unittest.TestCase):
    def test_closed_gate_reproduces_anchor_logits(self) -> None:
        torch.manual_seed(11)
        gate = BaselinePreservingResidualGate(num_classes=6)
        srr_logits = torch.randn(1, 6, 4, 6, 6)
        anchor_prob = torch.softmax(torch.randn_like(srr_logits), dim=1)
        availability = torch.tensor([[1.0, 1.0, 1.0]])

        outputs = gate(srr_logits, {"probabilities": anchor_prob}, availability, force_closed=True)
        expected = gate._as_logits(anchor_prob, srr_logits)

        self.assertTrue(torch.allclose(outputs["final_logits"], expected, atol=1e-6))
        self.assertTrue(torch.equal(outputs["gate"], torch.zeros_like(outputs["gate"])))

    def test_formal_propref_forward_emits_baseline_gate_evidence(self) -> None:
        torch.manual_seed(12)
        model = SRRProposeRefineMyoPS(base_channels=4)
        x = torch.randn(1, 3, 5, 8, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        anchor_prob = torch.softmax(torch.randn(1, 6, 5, 8, 8), dim=1)

        outputs = model(x, availability, anchor_features={"probabilities": anchor_prob})

        self.assertEqual(tuple(outputs["logits"].shape), (1, 6, 5, 8, 8))
        self.assertEqual(tuple(outputs["srr_logits_pre_anchor"].shape), (1, 6, 5, 8, 8))
        self.assertEqual(tuple(outputs["baseline_residual_gate"].shape), (1, 6, 5, 8, 8))
        self.assertEqual(outputs["baseline_gate_status"], "baseline_preserving_residual")
        self.assertTrue(torch.isfinite(outputs["bounded_delta_srr"]).all().item())
        self.assertLessEqual(float(outputs["baseline_residual_gate"].detach().max()), 1.0)
        self.assertGreaterEqual(float(outputs["baseline_residual_gate"].detach().min()), 0.0)


    def test_propref_loss_reports_baseline_preservation_objective(self) -> None:
        from scripts.training.run_srr_propref_myops_fold0 import propref_loss

        torch.manual_seed(13)
        model = SRRProposeRefineMyoPS(base_channels=4)
        x = torch.randn(1, 3, 5, 8, 8)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        labels = torch.zeros(1, 5, 8, 8, dtype=torch.long)
        labels[:, 1:4, 2:6, 2:6] = 1
        anchor_prob = torch.full((1, 6, 5, 8, 8), 0.01)
        anchor_prob[:, 1] = 0.95
        anchor_prob = anchor_prob / anchor_prob.sum(dim=1, keepdim=True)
        outputs = model(x, availability, anchor_features={"probabilities": anchor_prob})
        args = Namespace(
            anatomy_weight=1.0,
            scar_weight=1.0,
            edema_weight=1.0,
            proposal_margin=0.25,
            component_proposal_margin=0.35,
            component_proposal_weight=0.20,
            semantic_retrieval_weight=0.04,
            semantic_coverage_weight=0.03,
            semantic_integrative_weight=0.02,
            baseline_preservation_weight=0.10,
            baseline_preservation_confidence=0.80,
            baseline_gate_harm_weight=0.25,
            margin_weight=0.30,
            proposal_weight=0.45,
            roi_weight=0.25,
            roi_remote_weight=0.05,
        )
        loss, metrics = propref_loss(outputs, labels, availability, "soft_roi_refinement", args)
        self.assertTrue(torch.isfinite(loss).item())
        self.assertIn("baseline_preservation_loss", metrics)
        self.assertIn("baseline_preserve_voxels", metrics)
        self.assertIn("baseline_preserve_gate_mean", metrics)
        self.assertGreater(float(metrics["baseline_preserve_voxels"].detach()), 0.0)
        self.assertGreaterEqual(float(metrics["baseline_preservation_loss"].detach()), 0.0)


if __name__ == "__main__":
    unittest.main()
