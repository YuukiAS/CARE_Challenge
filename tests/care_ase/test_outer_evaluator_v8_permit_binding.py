from pathlib import Path


def test_outer_evaluator_requires_explicit_v8_binding_arguments():
    source = Path("scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py").read_text(encoding="utf-8")
    for flag in (
        "--implementation-source-sha",
        "--review-packet-sha",
        "--effective-contract-sha256",
        "--critical-source-manifest-sha256",
        "--outer-permit",
        "--output-dir",
    ):
        assert flag in source
    assert "W45_PUSH_RECEIPT" not in source
