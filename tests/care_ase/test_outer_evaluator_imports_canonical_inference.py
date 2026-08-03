from pathlib import Path


def test_outer_evaluator_uses_canonical_inference_only():
    source = Path("scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py").read_text(encoding="utf-8")
    assert "from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_labels" in source
    assert "def sliding_window_logits" not in source
    assert "compute_slice_extent_statistics" not in source
    assert "20260803_care_ase_r2_full_fidelity_execution" not in source
