from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INFER = REPO_ROOT / "scripts/srr_production/infer_myops.py"
EVAL = REPO_ROOT / "scripts/srr_production/evaluate_myops_fair.py"


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def test_anchor_identity_inference_and_fair_eval_subset(tmp_path: Path) -> None:
    infer_root = tmp_path / "inference"
    eval_root = tmp_path / "evaluation"
    result = run_cmd(
        [
            sys.executable,
            str(INFER),
            "--mode",
            "anchor_identity_control",
            "--allow-untrained-diagnostic",
            "--max-cases",
            "2",
            "--output-root",
            str(infer_root),
        ]
    )
    assert result.returncode == 0, result.stderr + result.stdout
    contract = json.loads((infer_root / "batch3a_inference_contract.json").read_text(encoding="utf-8"))
    assert contract["status"] == "SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC"
    assert contract["case_count"] == 2
    assert contract["model_forward_count"] == 2
    assert contract["checkpoint_actual_load_count"] == 1
    assert contract["prototype_memory_actual_load_count"] == 1
    assert contract["anchor_identity_changed_voxels_total"] == 0
    result = run_cmd(
        [
            sys.executable,
            str(EVAL),
            "--max-cases",
            "2",
            "--identity-pred-dir",
            str(infer_root / "anchor_identity_control/predictions"),
            "--output-dir",
            str(eval_root),
        ]
    )
    assert result.returncode == 0, result.stderr + result.stdout
    completion = json.loads((eval_root / "batch2_completion.json").read_text(encoding="utf-8"))
    assert completion["status"] == "BATCH_2_IDENTITY_EVALUATION_AUTHORITY_COMPLETE"
    assert completion["srr_scientific_status"] == "SRR_COMPARISON_DISABLED_NO_CONTRACT"
    identity = json.loads((eval_root / "anchor_identity_44case.json").read_text(encoding="utf-8"))
    assert identity["changed_voxels_total"] == 0
    assert identity["raw_label_mismatch_total"] == 0


def test_untrained_srr_modes_require_explicit_diagnostic(tmp_path: Path) -> None:
    blocked = run_cmd(
        [
            sys.executable,
            str(INFER),
            "--mode",
            "anchor_bounded_srr_correction",
            "--max-cases",
            "1",
            "--output-root",
            str(tmp_path / "blocked"),
        ]
    )
    assert blocked.returncode != 0
    assert "--allow-untrained-diagnostic" in blocked.stderr
    diagnostic = run_cmd(
        [
            sys.executable,
            str(INFER),
            "--mode",
            "anchor_bounded_srr_correction",
            "--allow-untrained-diagnostic",
            "--max-cases",
            "1",
            "--output-root",
            str(tmp_path / "diagnostic"),
        ]
    )
    assert diagnostic.returncode == 0, diagnostic.stderr + diagnostic.stdout
    contract = json.loads((tmp_path / "diagnostic/batch3a_inference_contract.json").read_text(encoding="utf-8"))
    assert contract["status"] == "SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC"
    assert contract["model_forward_count"] == 1
    assert contract["nonidentity_downstream_tensor_max_abs_delta"] > 0
    assert contract["formal_training_count"] == 0


def test_srr_evaluation_requires_contract(tmp_path: Path) -> None:
    result = run_cmd(
        [
            sys.executable,
            str(EVAL),
            "--max-cases",
            "1",
            "--identity-pred-dir",
            str(tmp_path / "identity"),
            "--srr-pred-dir",
            str(tmp_path / "srr"),
            "--output-dir",
            str(tmp_path / "eval"),
        ]
    )
    assert result.returncode != 0
    assert "--srr-pred-dir requires --srr-contract" in result.stderr
