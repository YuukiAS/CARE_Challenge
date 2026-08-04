#!/usr/bin/env python
"""Run and combine CARE-ASE R2 held-out diagnostic comparisons for one step."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_KEY = "20260804_care_ase_r2_deadline_recovery_training_docker"
RUNTIME_ROOT = (
    REPO_ROOT
    / "results/20260804_care_ase_r2_formal_training_e9e212dd7856/runtime_deadline_e9e212dd7856"
)
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def run_fold(step: int, fold: int, *, force: bool) -> dict[str, Any]:
    ckpt = RUNTIME_ROOT / f"fold_{fold}" / f"checkpoint_step{step:05d}.pt"
    verified = ckpt.with_suffix(ckpt.suffix + ".verified.json")
    if not ckpt.is_file():
        raise FileNotFoundError(f"missing fold{fold} checkpoint for step{step}: {ckpt}")
    if not verified.is_file():
        raise FileNotFoundError(f"missing fold{fold} verified receipt for step{step}: {verified}")
    out = OUT_ROOT / f"user_override_outer_diagnostic_step{step:05d}" / f"fold_{fold}"
    summary = out / "outer_diagnostic_summary.json"
    if summary.is_file() and not force:
        return load_json(summary)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/evaluation/care_ase/evaluate_care_ase_r2_outer_diagnostic.py"),
        "--fold",
        str(fold),
        "--checkpoint-step",
        str(step),
        "--checkpoint",
        str(ckpt),
        "--output-dir",
        str(out),
        "--decision",
        f"USER_AUTHORIZED_HELDOUT_DIAGNOSTIC_STEP{step}",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    return load_json(summary)


def combine(step: int, fold_packets: list[dict[str, Any]]) -> dict[str, Any]:
    case_total = sum(int(packet["case_count"]) for packet in fold_packets)
    edema_total = sum(int(packet["edema_t2_case_count"]) for packet in fold_packets)

    def weighted_mean(key: str, *, edema: bool = False) -> float:
        total = edema_total if edema else case_total
        if total <= 0:
            return float("nan")
        numerator = 0.0
        for packet in fold_packets:
            n = int(packet["edema_t2_case_count"] if edema else packet["case_count"])
            numerator += float(packet["summary"][key]) * n
        return numerator / total

    care_scar = weighted_mean("care_scar_mean")
    nnunet_scar = weighted_mean("nnunet_scar_mean")
    care_edema = weighted_mean("care_pure_edema_mean", edema=True)
    nnunet_edema = weighted_mean("nnunet_pure_edema_mean", edema=True)
    packet = {
        "status": "PASS",
        "checkpoint_step": int(step),
        "decision": f"USER_AUTHORIZED_HELDOUT_DIAGNOSTIC_STEP{step}",
        "case_count_total": case_total,
        "edema_t2_case_count_total": edema_total,
        "outer_access_authorization": "explicit_user_authorized_diagnostic_heldout_comparison",
        "folds": fold_packets,
        "scar": {
            "care_mean": care_scar,
            "nnunet_mean": nnunet_scar,
            "delta_care_minus_nnunet": care_scar - nnunet_scar,
        },
        "pure_edema": {
            "care_mean": care_edema,
            "nnunet_mean": nnunet_edema,
            "delta_care_minus_nnunet": care_edema - nnunet_edema,
        },
    }
    mosaic_path = (
        REPO_ROOT.parent
        / ".tmp/codex-CARE/20260804_care_ase_r2_emergency_9h_training_docker/"
        "mosaic_full_myops_heldout_eval_trainlabels/mosaic_full_myops_heldout_summary.json"
    )
    if mosaic_path.is_file():
        mosaic = load_json(mosaic_path)
        packet["mosaic_reference"] = {
            "source": str(mosaic_path),
            "source_sha256": sha256_file(mosaic_path),
            "scar_mean": mosaic.get("mosaic_scar_mean"),
            "pure_edema_mean": mosaic.get("mosaic_pure_edema_mean"),
            "weights": mosaic.get("mosaic_full_data_weights"),
            "note": "MoSAIC full-data MyoPS weights; same cases and metric labels, not OOF-equivalent training exposure.",
        }
        packet["scar"]["delta_care_minus_mosaic"] = care_scar - float(mosaic["mosaic_scar_mean"])
        packet["pure_edema"]["delta_care_minus_mosaic"] = care_edema - float(mosaic["mosaic_pure_edema_mean"])
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    fold_packets = [run_fold(args.step, fold, force=args.force) for fold in (1, 4)]
    packet = combine(args.step, fold_packets)
    out = OUT_ROOT / f"outer_diagnostic_step{args.step:05d}_combined_summary.json"
    write_json(out, packet)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
