#!/usr/bin/env python3
"""Bind Cine ED-only/reference vs temporal probe evidence into V2."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
CINE_REL = Path("results/20260626_cine_temporal")
FOLLOW_REL = Path("results/20260705_srr_v3_m7_training_and_cine_utilization")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def upsert_task_status(result_root: Path, task_id: str, status: str, evidence: str, notes: str) -> None:
    path = result_root / "v2_task_status.csv"
    rows = read_csv(path) if path.exists() else []
    rows = [r for r in rows if r.get("task_id") != task_id]
    rows.append(
        {
            "task_id": task_id,
            "category": "gpu_diagnostic",
            "required": "true",
            "status": status,
            "terminal_status": "true",
            "evidence_path": evidence,
            "notes": notes,
        }
    )
    write_csv(path, rows, ["task_id", "category", "required", "status", "terminal_status", "evidence_path", "notes"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    result_root = root / RESULT_REL
    cine_root = root / CINE_REL
    follow_root = root / FOLLOW_REL

    summary = read_csv(cine_root / "summary_metrics.csv")
    casewise = read_csv(cine_root / "case_metrics.csv")
    frame = read_csv(cine_root / "frame_retrieval.csv")
    follow_help = read_csv(follow_root / "frame0_vs_temporal_help_harm.csv") if (follow_root / "frame0_vs_temporal_help_harm.csv").exists() else []
    follow_temporal = read_csv(follow_root / "temporal_aggregation_metrics.csv") if (follow_root / "temporal_aggregation_metrics.csv").exists() else []

    probe_rows = []
    ref = {(r["metric_name"], r["class_id"]): r for r in summary if r["variant"] == "reference_control_safe"}
    for row in summary:
        key = (row["metric_name"], row["class_id"])
        ref_row = ref.get(key)
        ref_dice = float(ref_row["dice_mean"]) if ref_row and ref_row.get("dice_mean") else None
        dice_mean = float(row["dice_mean"]) if row.get("dice_mean") else None
        probe_rows.append(
            {
                "variant": row["variant"],
                "metric_name": row["metric_name"],
                "class_id": row["class_id"],
                "case_count": row["n"],
                "dice_mean": row["dice_mean"],
                "delta_vs_reference_control": (dice_mean - ref_dice) if dice_mean is not None and ref_dice is not None else "",
                "hd95_mean": row["hd95_mean"],
                "component_count_mean": row["component_count_mean"],
                "empty_prediction_rate": row["empty_prediction_rate"],
                "evidence_boundary": "safe-subset local proxy; no hosted metric claim; class_3 is negative control because source model has no scar head",
            }
        )
    write_csv(result_root / "cine_temporal_signal_probe.csv", probe_rows)
    write_csv(result_root / "cine_casewise_metrics.csv", casewise)
    write_csv(result_root / "cine_motion_quality.csv", frame)
    write_csv(result_root / "cine_implementation_fidelity_matrix.csv", follow_help + follow_temporal)
    write_csv(
        result_root / "cine_model_lineage.csv",
        [
            {
                "source": str((cine_root / "MANIFEST.md").relative_to(root)),
                "decision": "KEEP_REFERENCE_CONTROL",
                "safe_case_count": len({r["case_id"] for r in casewise}),
                "temporal_candidate_training": "not_full_candidate_training",
                "hosted_metric_claim": "false",
            }
        ],
    )
    report = [
        "# Cine temporal V2 binding",
        "",
        "V2 绑定 20260626 Cine temporal preflight：reference frame0 control、keyframe retrieval 和 anatomy consistency temporal 在同一 safe subset 上比较。",
        "",
        "结论：keyframe retrieval 与 reference control 基本持平，anatomy consistency temporal 明显降低 myocardium/LV proxy；因此当前本地证据不支持把 Cine temporal 当作主要可用增益来源。",
        "",
        "class_3 scar sanity 只作负控，因为该来源模型没有 scar head；不得据此声称 Cine scar 无信号。",
    ]
    (result_root / "cine_forensics_report.md").write_text("\n".join(report) + "\n")
    receipt = {
        "status": "COMPLETED_WITH_VALID_EVIDENCE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(cine_root),
        "case_count": len({r["case_id"] for r in casewise}),
        "summary_rows": len(summary),
        "casewise_rows": len(casewise),
        "followup_rows": len(follow_help) + len(follow_temporal),
    }
    (result_root / "cine_temporal_v2_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    upsert_task_status(
        result_root,
        "G9_CINE_ED_ONLY_VS_TEMPORAL_PROBE",
        "COMPLETED_WITH_VALID_EVIDENCE",
        str((result_root / "cine_temporal_signal_probe.csv").relative_to(root)),
        "Bound 20260626 safe-subset ED/reference vs temporal probe; temporal did not beat reference control on local proxies.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
