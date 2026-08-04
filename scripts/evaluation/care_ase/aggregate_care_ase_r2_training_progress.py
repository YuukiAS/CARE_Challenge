#!/usr/bin/env python
"""Aggregate CARE-ASE R2 diagnostic comparisons into a progress curve."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_KEY = "20260804_care_ase_r2_deadline_recovery_training_docker"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = (
    REPO_ROOT
    / "results/20260804_care_ase_r2_formal_training_e9e212dd7856/runtime_deadline_e9e212dd7856"
)
MOSAIC_REFERENCE = (
    REPO_ROOT.parent
    / ".tmp/codex-CARE/20260804_care_ase_r2_emergency_9h_training_docker/"
    "mosaic_full_myops_heldout_eval_trainlabels/mosaic_full_myops_heldout_summary.json"
)


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out


def metric_from_packet(packet: dict[str, Any], group: str, key: str) -> float:
    if group in packet and key in packet[group]:
        return finite(packet[group][key])
    combined = packet.get("combined", {})
    legacy = {
        ("scar", "care_mean"): "care_scar_mean",
        ("scar", "nnunet_mean"): "nnunet_scar_mean",
        ("scar", "delta_care_minus_nnunet"): "care_minus_nnunet_scar_mean",
        ("pure_edema", "care_mean"): "care_pure_edema_mean",
        ("pure_edema", "nnunet_mean"): "nnunet_pure_edema_mean",
        ("pure_edema", "delta_care_minus_nnunet"): "care_minus_nnunet_pure_edema_mean",
    }
    return finite(combined.get(legacy.get((group, key), "")))


def checkpoint_binding(step: int, fold: int) -> dict[str, Any]:
    ckpt = RUNTIME_ROOT / f"fold_{fold}" / f"checkpoint_step{step:05d}.pt"
    verified = ckpt.with_suffix(ckpt.suffix + ".verified.json")
    return {
        f"fold{fold}_checkpoint": str(ckpt.relative_to(REPO_ROOT)) if ckpt.is_file() else "",
        f"fold{fold}_checkpoint_sha256": sha256_file(ckpt) if ckpt.is_file() else "",
        f"fold{fold}_verified_receipt": str(verified.relative_to(REPO_ROOT)) if verified.is_file() else "",
        f"fold{fold}_verified_receipt_sha256": sha256_file(verified) if verified.is_file() else "",
    }


def collect_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mosaic_reference = load_json(MOSAIC_REFERENCE) if MOSAIC_REFERENCE.is_file() else None
    for path in sorted(OUT_ROOT.glob("outer_diagnostic_step*_combined_summary.json")):
        match = re.search(r"step(\d+)", path.name)
        if not match:
            continue
        step = int(match.group(1))
        packet = load_json(path)
        row: dict[str, Any] = {
            "step": step,
            "summary_path": str(path.relative_to(REPO_ROOT)),
            "summary_sha256": sha256_file(path),
            "case_count_total": packet.get("case_count_total", 88),
            "edema_t2_case_count_total": packet.get("edema_t2_case_count_total", 32),
            "care_scar_mean": metric_from_packet(packet, "scar", "care_mean"),
            "nnunet_scar_mean": metric_from_packet(packet, "scar", "nnunet_mean"),
            "care_minus_nnunet_scar_mean": metric_from_packet(packet, "scar", "delta_care_minus_nnunet"),
            "care_pure_edema_mean": metric_from_packet(packet, "pure_edema", "care_mean"),
            "nnunet_pure_edema_mean": metric_from_packet(packet, "pure_edema", "nnunet_mean"),
            "care_minus_nnunet_pure_edema_mean": metric_from_packet(packet, "pure_edema", "delta_care_minus_nnunet"),
            "mosaic_scar_mean": "",
            "care_minus_mosaic_scar_mean": "",
            "mosaic_pure_edema_mean": "",
            "care_minus_mosaic_pure_edema_mean": "",
        }
        mosaic = packet.get("mosaic_reference")
        if not isinstance(mosaic, dict) and mosaic_reference is not None:
            mosaic = {
                "scar_mean": mosaic_reference.get("mosaic_scar_mean"),
                "pure_edema_mean": mosaic_reference.get("mosaic_pure_edema_mean"),
            }
        if isinstance(mosaic, dict):
            row["mosaic_scar_mean"] = finite(mosaic.get("scar_mean"))
            row["mosaic_pure_edema_mean"] = finite(mosaic.get("pure_edema_mean"))
            row["care_minus_mosaic_scar_mean"] = finite(row["care_scar_mean"]) - finite(row["mosaic_scar_mean"])
            row["care_minus_mosaic_pure_edema_mean"] = finite(row["care_pure_edema_mean"]) - finite(
                row["mosaic_pure_edema_mean"]
            )
        for fold in (1, 4):
            row.update(checkpoint_binding(step, fold))
        rows.append(row)
    return sorted(rows, key=lambda row: int(row["step"]))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = [int(row["step"]) for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=160, constrained_layout=True)
    for ax, pathology, care_key, nn_key, mosaic_key in [
        (axes[0], "Scar", "care_scar_mean", "nnunet_scar_mean", "mosaic_scar_mean"),
        (axes[1], "Pure edema", "care_pure_edema_mean", "nnunet_pure_edema_mean", "mosaic_pure_edema_mean"),
    ]:
        ax.plot(steps, [finite(row[care_key]) for row in rows], marker="o", label="CARE-ASE")
        nn_vals = [finite(row[nn_key]) for row in rows]
        if any(math.isfinite(v) for v in nn_vals):
            ax.plot(steps, nn_vals, linestyle="--", label="nnU-Net")
        mosaic_vals = [finite(row[mosaic_key]) for row in rows]
        if any(math.isfinite(v) for v in mosaic_vals):
            ax.plot(steps, mosaic_vals, linestyle=":", label="MoSAIC")
        ax.set_title(pathology)
        ax.set_xlabel("optimizer step")
        ax.set_ylabel("Dice mean")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("CARE-ASE R2 training progress diagnostic")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT_ROOT / "training_progress_curve")
    args = parser.parse_args()
    os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp/matplotlib"))
    rows = collect_rows()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "care_ase_r2_training_progress_curve.csv"
    json_path = out / "care_ase_r2_training_progress_curve.json"
    png_path = out / "care_ase_r2_training_progress_curve.png"
    write_csv(csv_path, rows)
    payload = {
        "status": "PASS" if rows else "NO_DIAGNOSTIC_SUMMARIES",
        "task_key": TASK_KEY,
        "row_count": len(rows),
        "steps": [int(row["step"]) for row in rows],
        "csv": str(csv_path.relative_to(REPO_ROOT)),
        "png": str(png_path.relative_to(REPO_ROOT)),
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    write_plot(png_path, rows)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
