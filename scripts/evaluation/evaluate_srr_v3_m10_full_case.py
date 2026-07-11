#!/usr/bin/env python3
"""Lightweight M10 full-case evidence copier.

The legacy trainer already performs full-case export/evaluation after a
checkpoint is available.  This script normalizes those per-variant artifacts
into the phase result directory without inventing missing evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from scripts.training.run_srr_v3_m10_complete_repair import PHASES, REPO_ROOT


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def dynamic_fields(rows: list[dict[str, object]], preferred: list[str]) -> list[str]:
    fields = list(preferred)
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    parser.add_argument("--runtime-root", default="")
    args = parser.parse_args()
    spec = PHASES[args.phase]
    result_dir = REPO_ROOT / spec.result_dir
    runtime_root = Path(args.runtime_root) if args.runtime_root else result_dir / "runtime"
    if not runtime_root.is_absolute():
        runtime_root = REPO_ROOT / runtime_root
    variant_dir = runtime_root / "variants" / spec.run_label
    summary_path = variant_dir / "summary.json"
    manifest = {
        "phase": spec.phase,
        "result_dir": str(result_dir),
        "runtime_root": str(runtime_root),
        "variant_dir": str(variant_dir),
        "summary_path": str(summary_path),
        "status": "EVIDENCE_NOT_FOUND",
        "copied_files": [],
    }
    if not summary_path.is_file():
        (result_dir / "full_case_evaluation_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        raise SystemExit(2)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    copied: list[str] = []
    for source_name, target_name in [
        ("component_hd_by_case_checkpoint_best.csv", "case_metrics.csv"),
        ("subgroup_metrics_checkpoint_best.csv", "hard_subgroup_metrics.csv"),
        ("prediction_sanity_checkpoint_best.csv", "prediction_sanity_cases.csv"),
    ]:
        source = variant_dir / source_name
        if source.is_file():
            target = result_dir / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append(str(target))
    rows = read_csv(result_dir / "prediction_sanity_cases.csv")
    if rows:
        status_rows: list[dict[str, object]] = []
        for row in rows:
            status_rows.append(
                {
                    "case_id": row.get("case_id", ""),
                    "checkpoint_name": row.get("checkpoint_name", "checkpoint_best"),
                    "decode_mode": row.get("decode_mode", ""),
                    "foreground_rate": row.get("foreground_rate", ""),
                    "pathology_rate": row.get("pathology_rate", ""),
                    "edema_voxels": row.get("edema_voxels", ""),
                    "scar_voxels": row.get("scar_voxels", ""),
                    "status": "RUNTIME_EVIDENCE",
                }
            )
        write_csv(result_dir / "prediction_sanity_table.csv", status_rows, dynamic_fields(status_rows, ["case_id", "checkpoint_name", "decode_mode", "status"]))
    lines = [
        f"# Prediction Sanity - {spec.phase}",
        "",
        f"Runtime summary: `{summary_path}`",
        f"Eval cases: `{summary.get('eval_cases', 'EVIDENCE_NOT_FOUND')}`",
        f"Prediction dirs: `{summary.get('prediction_dirs', [])}`",
        "",
        "This file summarizes runtime artifacts only; it does not claim hosted metrics.",
    ]
    (result_dir / "prediction_sanity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest["status"] = "RUNTIME_EVIDENCE_COPIED"
    manifest["copied_files"] = copied
    (result_dir / "full_case_evaluation_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
