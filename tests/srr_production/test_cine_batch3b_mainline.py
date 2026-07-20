from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/srr_production/infer_cine_batch3b.py"


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def test_cine_batch3b_real_case_diagnostic_contract(tmp_path: Path) -> None:
    result = run_cmd(
        [
            sys.executable,
            str(SCRIPT),
            "--max-cases",
            "1",
            "--flow-max-side",
            "48",
            "--output-root",
            str(tmp_path / "cine_batch3b"),
        ]
    )
    assert result.returncode == 0, result.stderr + result.stdout
    contract = json.loads((tmp_path / "cine_batch3b/batch3b_cine_contract.json").read_text(encoding="utf-8"))
    assert contract["status"] == "BATCH3B_REAL_CINE_MAINLINE_DIAGNOSTIC_COMPLETE"
    assert contract["case_count"] == 1
    assert contract["time_axis_preserved_all_cases"] is True
    assert contract["nonreference_entered_temporal_aggregation_all_cases"] is True
    assert contract["temporal_aggregation_affects_output"] is True
    assert contract["registration_method"] == "slice2d_dense_optical_flow_ilk_image_based"
    assert contract["cinema_used"] is False
    assert contract["historical_b7_b8_formal_authority"] is False
    assert contract["formal_training_count"] == 0
    assert contract["slurm_job_count"] == 0
    assert contract["validation_upload_count"] == 0
    assert contract["hosted_metric_claim_count"] == 0
    assert contract["performance_claim"] == "NONE_LOCAL_DIAGNOSTIC_ONLY"
    for rel in [
        "batch3b_time_axis_audit.csv",
        "batch3b_registration_warp_qc.csv",
        "batch3b_temporal_aggregation.csv",
        "batch3b_ed_space_evaluation.csv",
        "batch3b_known_bad_report.json",
    ]:
        assert (tmp_path / "cine_batch3b" / rel).is_file()


def test_cine_batch3b_known_bad_injection_passes(tmp_path: Path) -> None:
    result = run_cmd(
        [
            sys.executable,
            str(SCRIPT),
            "--max-cases",
            "1",
            "--flow-max-side",
            "32",
            "--output-root",
            str(tmp_path / "known_bad"),
        ]
    )
    assert result.returncode == 0, result.stderr + result.stdout
    known_bad = json.loads((tmp_path / "known_bad/batch3b_known_bad_report.json").read_text(encoding="utf-8"))
    assert known_bad["status"] == "BATCH3B_KNOWN_BAD_INJECTION_PASS"
    assert {check["name"] for check in known_bad["checks"]} == {
        "reject_3d_cine_missing_time_axis",
        "reject_no_nonreference_frame",
        "reject_nonreference_weight_without_reference_anchor",
    }
    assert all(check["detected"] for check in known_bad["checks"])
