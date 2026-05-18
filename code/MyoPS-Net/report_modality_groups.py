#!/usr/bin/env python3
"""Summarize MyoPS-Net metrics by source modality combination."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def discover_case_dirs(source_root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in sorted(source_root.glob("**/Case*")):
        if p.is_dir():
            out[p.name] = p
    return out


def load_modalities(data_root: Path | None, source_root: Path) -> dict[str, dict[str, bool]]:
    if data_root is not None:
        metadata = data_root / "modalities_present.json"
        if metadata.is_file():
            raw = load_json(metadata)
            return {
                case_id: {
                    "c0": bool(info.get("c0", False)),
                    "lge": bool(info.get("lge", False)),
                    "t2": bool(info.get("t2", False)),
                }
                for case_id, info in raw.items()
            }

    cases = discover_case_dirs(source_root)
    modalities: dict[str, dict[str, bool]] = {}
    for case_id, case_dir in cases.items():
        modalities[case_id] = {
            "c0": (case_dir / f"{case_id}_C0.nii.gz").is_file(),
            "lge": (case_dir / f"{case_id}_LGE.nii.gz").is_file(),
            "t2": (case_dir / f"{case_id}_T2.nii.gz").is_file(),
        }
    return modalities


def group_name(info: dict[str, bool]) -> str:
    parts = []
    if info.get("c0"):
        parts.append("C0")
    if info.get("lge"):
        parts.append("LGE")
    if info.get("t2"):
        parts.append("T2")
    return "+".join(parts) or "none"


def mean_non_null(values: list[float | None]) -> float | None:
    kept = [float(v) for v in values if v is not None]
    return mean(kept) if kept else None


def fmt(value: float | None) -> str:
    return "NA" if value is None else f"{value:.4f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evaluation-summary", type=Path, required=True)
    ap.add_argument("--fold-json", type=Path, required=True)
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--data-root", type=Path, default=None)
    ap.add_argument(
        "--source-root",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/CARE_Challenge/MyoPS_train"),
    )
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    args = ap.parse_args()

    summary = load_json(args.evaluation_summary)
    splits = load_json(args.fold_json)
    val_ids = splits["folds"][args.fold]["val"]
    modalities = load_modalities(args.data_root, args.source_root)

    rows: dict[str, dict[str, object]] = {}
    for case_id in val_ids:
        if case_id not in summary.get("per_case", {}):
            continue
        info = modalities.get(case_id, {"c0": False, "lge": True, "t2": False})
        group = group_name(info)
        rows.setdefault(group, {"cases": [], "class_4": [], "class_5": [], "foreground_mean": []})
        rows[group]["cases"].append(case_id)
        per_case = summary["per_case"][case_id]
        rows[group]["class_4"].append(per_case.get("class_4"))
        rows[group]["class_5"].append(per_case.get("class_5"))
        rows[group]["foreground_mean"].append(per_case.get("foreground_mean"))

    out = {
        "fold": args.fold,
        "n_cases": sum(len(v["cases"]) for v in rows.values()),
        "groups": {},
        "leaderboard_labels": {
            "class_4": "myops_edema",
            "class_5": "myops_scar",
        },
        "notes": [
            "Dice uses evaluation_summary per-case values; class means omit null GT-empty cases and score false positives as 0 when produced by evaluation.",
            "Groups are source acquisition availability, not training dropout groups.",
        ],
    }
    for group in sorted(rows):
        row = rows[group]
        out["groups"][group] = {
            "n_cases": len(row["cases"]),
            "cases": row["cases"],
            "mean_dice": {
                "myops_edema_class_4": mean_non_null(row["class_4"]),
                "myops_scar_class_5": mean_non_null(row["class_5"]),
                "foreground_mean": mean_non_null(row["foreground_mean"]),
            },
        }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        f"# MyoPS-Net fold{args.fold} modality-group metrics",
        "",
        "| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for group in sorted(out["groups"]):
        metrics = out["groups"][group]["mean_dice"]
        lines.append(
            f"| {group} | {out['groups'][group]['n_cases']} | "
            f"{fmt(metrics['myops_edema_class_4'])} | "
            f"{fmt(metrics['myops_scar_class_5'])} | "
            f"{fmt(metrics['foreground_mean'])} |"
        )
    lines.extend(
        [
            "",
            "Notes:",
            "- class_4 is CARE `myops_edema`; class_5 is CARE `myops_scar`.",
            "- `NA` means every case in that group was GT-empty for that class and had no false-positive prediction in the evaluator output.",
        ]
    )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output_json} and {args.output_md}")


if __name__ == "__main__":
    main()
