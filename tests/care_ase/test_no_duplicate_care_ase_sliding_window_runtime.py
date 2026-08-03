from pathlib import Path


def test_no_duplicate_care_ase_sliding_window_runtime():
    outer = Path("scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py").read_text(encoding="utf-8")
    canonical = Path("src/care_myocardium/inference/care_ase_r2_full_volume.py").read_text(encoding="utf-8")
    assert "def predict_care_ase_r2_full_volume_logits" in canonical
    assert "def sliding_window_logits" not in outer
    assert "def starts_for" not in outer
