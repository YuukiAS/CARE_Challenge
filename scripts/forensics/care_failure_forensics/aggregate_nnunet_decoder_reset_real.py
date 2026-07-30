#!/usr/bin/env python3
"""Aggregate real nnU-Net V2 decoder-reset diagnostic outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
VARIANTS = [
    "D0_FULL_PRETRAINED_IDENTITY",
    "D1_DECODER_RESET_ENCODER_FROZEN",
    "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE",
    "D3_FULL_MODEL_SHORT_FINETUNE",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in fieldnames} for row in rows])


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:
            return "nan"
        return f"{value:.9f}"
    return str(value)


def append_or_replace_status(path: Path, task_id: str, status_row: dict[str, Any]) -> None:
    fieldnames = ["task_id", "category", "required", "status", "terminal_status", "evidence_path", "notes"]
    rows: list[dict[str, Any]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = [{k: row.get(k, "") for k in fieldnames} for row in csv.DictReader(f)]
    replaced = False
    for row in rows:
        if row.get("task_id") == task_id:
            row.update(status_row)
            replaced = True
    if not replaced:
        rows.append({"task_id": task_id, **status_row})
    write_csv(path, rows, fieldnames)


def case_id_from_prediction_path(path: str) -> str:
    return Path(path).stem.replace(".nii", "")


def aggregate_run(root: Path, result_root: Path, run_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    runtime = result_root / "runtime/nnunet_decoder_reset_real" / run_id
    summary_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    pred_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        receipt_path = runtime / variant / "completion_receipt.json"
        if not receipt_path.exists():
            continue
        receipt = read_json(receipt_path)
        validation_folder = Path(receipt["validation_folder"])
        summary_path = validation_folder / "summary.json"
        if not summary_path.exists():
            continue
        summary = read_json(summary_path)
        mean = summary.get("mean", {})
        fg = summary.get("foreground_mean", {})
        row = {
            "run_id": run_id,
            "variant": variant,
            "status": receipt.get("status"),
            "slurm_job_id": receipt.get("environment", {}).get("slurm_job_id", ""),
            "slurm_step_id": receipt.get("environment", {}).get("slurm_step_id", ""),
            "node": receipt.get("environment", {}).get("hostname", ""),
            "gpu": receipt.get("environment", {}).get("cuda_device_name", ""),
            "checkpoint_sha256": receipt.get("checkpoint_sha256", ""),
            "actual_train_count": receipt.get("split_contract", {}).get("actual_train_count", ""),
            "inner_select_count": receipt.get("split_contract", {}).get("inner_select_count", ""),
            "class_1_dice": fmt(mean.get("1", {}).get("Dice")),
            "class_2_dice": fmt(mean.get("2", {}).get("Dice")),
            "class_3_dice": fmt(mean.get("3", {}).get("Dice")),
            "official_pure_edema_label4_dice": fmt(mean.get("4", {}).get("Dice")),
            "official_scar_label5_dice": fmt(mean.get("5", {}).get("Dice")),
            "foreground_mean_dice": fmt(fg.get("Dice")),
            "validation_summary": str(summary_path.relative_to(root)),
            "completion_receipt": str(receipt_path.relative_to(root)),
            "prediction_dir": str(validation_folder.relative_to(root)),
            "notes": "Real nnU-Net v2 trainer/plans validation on frozen inner_select.",
        }
        summary_rows.append(row)
        for entry in summary.get("metric_per_case", []):
            case = case_id_from_prediction_path(entry.get("prediction_file", ""))
            metrics = entry.get("metrics", {})
            case_rows.append(
                {
                    "run_id": run_id,
                    "variant": variant,
                    "case_id": case,
                    "class_1_dice": fmt(metrics.get("1", {}).get("Dice")),
                    "class_2_dice": fmt(metrics.get("2", {}).get("Dice")),
                    "class_3_dice": fmt(metrics.get("3", {}).get("Dice")),
                    "official_pure_edema_label4_dice": fmt(metrics.get("4", {}).get("Dice")),
                    "official_scar_label5_dice": fmt(metrics.get("5", {}).get("Dice")),
                    "prediction_file": str(Path(entry.get("prediction_file", "")).relative_to(root)),
                    "reference_file": str(Path(entry.get("reference_file", "")).relative_to(root)),
                }
            )
        for pred in sorted(validation_folder.glob("Case*.nii.gz")):
            sidecars = [pred.with_suffix("").with_suffix(".npz"), pred.with_suffix("").with_suffix(".pkl")]
            pred_rows.append(
                {
                    "run_id": run_id,
                    "variant": variant,
                    "case_id": pred.name.replace(".nii.gz", ""),
                    "prediction_file": str(pred.relative_to(root)),
                    "prediction_sha256": sha256_file(pred),
                    "prediction_size_bytes": pred.stat().st_size,
                    "probability_npz": str(sidecars[0].relative_to(root)) if sidecars[0].exists() else "",
                    "properties_pkl": str(sidecars[1].relative_to(root)) if sidecars[1].exists() else "",
                }
            )
    return summary_rows, case_rows, pred_rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--run-id", action="append", required=True)
    args = ap.parse_args()

    root = args.root.resolve()
    result_root = root / RESULT_REL
    all_summary: list[dict[str, Any]] = []
    all_case: list[dict[str, Any]] = []
    all_pred: list[dict[str, Any]] = []
    for run_id in args.run_id:
        summary_rows, case_rows, pred_rows = aggregate_run(root, result_root, run_id)
        all_summary.extend(summary_rows)
        all_case.extend(case_rows)
        all_pred.extend(pred_rows)

    summary_fields = [
        "run_id",
        "variant",
        "status",
        "slurm_job_id",
        "slurm_step_id",
        "node",
        "gpu",
        "checkpoint_sha256",
        "actual_train_count",
        "inner_select_count",
        "class_1_dice",
        "class_2_dice",
        "class_3_dice",
        "official_pure_edema_label4_dice",
        "official_scar_label5_dice",
        "foreground_mean_dice",
        "validation_summary",
        "completion_receipt",
        "prediction_dir",
        "notes",
    ]
    case_fields = [
        "run_id",
        "variant",
        "case_id",
        "class_1_dice",
        "class_2_dice",
        "class_3_dice",
        "official_pure_edema_label4_dice",
        "official_scar_label5_dice",
        "prediction_file",
        "reference_file",
    ]
    pred_fields = [
        "run_id",
        "variant",
        "case_id",
        "prediction_file",
        "prediction_sha256",
        "prediction_size_bytes",
        "probability_npz",
        "properties_pkl",
    ]
    write_csv(result_root / "nnunet_decoder_reset_real_summary.csv", all_summary, summary_fields)
    write_csv(result_root / "nnunet_decoder_reset_real_casewise.csv", all_case, case_fields)
    write_csv(result_root / "nnunet_decoder_reset_prediction_manifest.csv", all_pred, pred_fields)

    completed_variants = {row["variant"] for row in all_summary if row.get("status") == "COMPLETED_WITH_VALID_EVIDENCE"}
    d0_complete = "D0_FULL_PRETRAINED_IDENTITY" in completed_variants
    d1d3_complete = all(v in completed_variants for v in VARIANTS[1:])
    append_or_replace_status(
        result_root / "v2_task_status.csv",
        "G1_NNUNET_IDENTITY_REPRODUCTION",
        {
            "category": "gpu_diagnostic",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE" if d0_complete else "REQUIRED_NOT_TERMINAL",
            "terminal_status": "true" if d0_complete else "false",
            "evidence_path": str((result_root / "nnunet_decoder_reset_real_summary.csv").relative_to(root)),
            "notes": "D0 full pretrained identity replay on 12 inner_select cases.",
        },
    )
    append_or_replace_status(
        result_root / "v2_task_status.csv",
        "G3_REAL_NNUNET_DECODER_RESET",
        {
            "category": "gpu_diagnostic",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE" if d1d3_complete else "PARTIAL_COMPLETED_D0_ONLY",
            "terminal_status": "true" if d1d3_complete else "false",
            "evidence_path": str((result_root / "nnunet_decoder_reset_real_summary.csv").relative_to(root)),
            "notes": f"Completed variants: {','.join(sorted(completed_variants))}; PRISM wrapper residue not counted.",
        },
    )
    receipt = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AGGREGATED",
        "run_ids": args.run_id,
        "completed_variants": sorted(completed_variants),
        "summary_csv": str((result_root / "nnunet_decoder_reset_real_summary.csv").relative_to(root)),
        "casewise_csv": str((result_root / "nnunet_decoder_reset_real_casewise.csv").relative_to(root)),
        "prediction_manifest_csv": str((result_root / "nnunet_decoder_reset_prediction_manifest.csv").relative_to(root)),
        "g1_status": "COMPLETED_WITH_VALID_EVIDENCE" if d0_complete else "REQUIRED_NOT_TERMINAL",
        "g3_status": "COMPLETED_WITH_VALID_EVIDENCE" if d1d3_complete else "PARTIAL_COMPLETED_D0_ONLY",
    }
    write_json(result_root / "nnunet_decoder_reset_real_aggregation_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
