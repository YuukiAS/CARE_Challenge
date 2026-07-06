from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from scripts.evaluation.run_srr_v3_m6_concrete_architecture_repair import synthetic_case, validate_packet, write_csv_rows
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS


def _write_minimal_valid_packet(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "srr_v3_fidelity_contract.md").write_text("bounded architecture/runtime smoke only\n", encoding="utf-8")
    write_csv_rows(
        path / "architecture_component_trace.csv",
        [{"variant": "m6", "component": "trace", "first_party_code_path": "src/example.py:1", "fix_status": "IMPLEMENTED"}],
    )
    write_csv_rows(
        path / "retrieval_bank_runtime_sanity.csv",
        [{"mean_usage": "0.1", "masked_invalid_slot_usage": "0", "t2_private_usage_when_no_t2": "0"}],
    )
    write_csv_rows(
        path / "prototype_bank_runtime_sanity.csv",
        [{"bank_type": "edema_safe_negative", "empty_bank_status": "NONEMPTY", "no_t2_used_as_edema_negative": "False"}],
    )
    write_csv_rows(
        path / "branch_arbitration_sanity.csv",
        [
            {
                "sanity_type": "correction_positive",
                "status": "PASS",
                "logit_delta_abs_mean": "0.1",
                "chosen_source": "srr_v3_full_context",
                "fallback_reason": "evidence_arbitration",
            },
            {
                "sanity_type": "low_quality_srr",
                "status": "PASS",
                "chosen_source": "segmentation_branch",
                "fallback_reason": "low_quality_srr_evidence_empty",
                "srr_confidence": "0",
                "correction_mask_rate": "0",
                "label_delta_vs_anchor": "0",
                "final_equals_anchor_labels": "True",
            },
        ],
    )
    write_csv_rows(
        path / "decode_gate_consistency_sanity.csv",
        [{"status": "PASS", "hidden_decode_delta_voxels": "0"}],
    )
    write_csv_rows(
        path / "refiner_roi_component_sanity.csv",
        [{"is_full_volume_crop": "False"}],
    )
    write_csv_rows(
        path / "loss_refiner_component_sanity.csv",
        [{"backward_status": "PASS", "gradient_norm": "1.0"}],
    )
    write_csv_rows(
        path / "no_t2_safety_sanity.csv",
        [{"status": "PASS", "edema_proposal_voxels": "0", "edema_refiner_voxels": "0", "edema_final_decode_voxels": "0"}],
    )


class TestSRRM6ContinuedGates(unittest.TestCase):
    def test_low_quality_srr_arbitration_selects_segmentation_branch(self) -> None:
        torch.manual_seed(20260706)
        x, _y, av, anchor, component = synthetic_case(t2_present=True, shape=(3, 10, 10))
        model = SRRProposeRefineMyoPS(
            variant="m6_conservative_component_arbitration",
            encoder_profile="safe_4scale",
            disable_local_refinement=True,
        ).eval()
        with torch.no_grad():
            outputs = model(x, av, anchor_features=anchor, component_features=component, disable_srr_evidence=True)
        final_labels = outputs["logits"].argmax(dim=1)
        anchor_labels = outputs["nnunet_anchor_logits"].argmax(dim=1)
        self.assertEqual(outputs["branch_chosen_source"], "segmentation_branch")
        self.assertEqual(outputs["branch_fallback_reason"], "low_quality_srr_evidence_empty")
        self.assertTrue(torch.equal(final_labels, anchor_labels))
        self.assertEqual(float(outputs["branch_correction_mask"].max()), 0.0)
        self.assertLess(float(outputs["branch_srr_confidence"].max()), 1e-3)

    def test_strict_validator_accepts_minimal_valid_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp) / "packet"
            _write_minimal_valid_packet(packet)
            ok, reasons = validate_packet(packet)
        self.assertTrue(ok, reasons)

    def test_strict_validator_fails_missing_or_claim_only_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp) / "packet"
            _write_minimal_valid_packet(packet)
            (packet / "srr_v3_fidelity_contract.md").unlink()
            ok, reasons = validate_packet(packet)
        self.assertFalse(ok)
        self.assertIn("missing_fidelity_contract", reasons)

    def test_strict_validator_fails_no_t2_unsafe_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp) / "packet"
            _write_minimal_valid_packet(packet)
            write_csv_rows(
                packet / "no_t2_safety_sanity.csv",
                [{"status": "FAIL", "edema_proposal_voxels": "0", "edema_refiner_voxels": "0", "edema_final_decode_voxels": "1"}],
            )
            ok, reasons = validate_packet(packet)
        self.assertFalse(ok)
        self.assertIn("no_t2_edema_nonzero", reasons)

    def test_strict_validator_fails_zero_srr_contribution_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp) / "packet"
            _write_minimal_valid_packet(packet)
            rows = [
                {
                    "sanity_type": "correction_positive",
                    "status": "FAIL",
                    "logit_delta_abs_mean": "0",
                    "chosen_source": "srr_v3_full_context",
                    "fallback_reason": "evidence_arbitration",
                }
            ]
            write_csv_rows(packet / "branch_arbitration_sanity.csv", rows)
            ok, reasons = validate_packet(packet)
        self.assertFalse(ok)
        self.assertIn("zero_srr_contribution_correction_positive", reasons)


if __name__ == "__main__":
    unittest.main()
