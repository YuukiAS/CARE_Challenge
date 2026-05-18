#!/usr/bin/env python3
"""Round4 MyoPS-Net export-only postprocess ablations."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import nibabel as nib
import numpy as np
from skimage import measure


CLASSES = (4, 5)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def group_name(info: dict[str, bool]) -> str:
    parts = []
    if info.get("c0", False):
        parts.append("C0")
    if info.get("lge", False):
        parts.append("LGE")
    if info.get("t2", False):
        parts.append("T2")
    return "+".join(parts) or "none"


def load_modalities(data_root: Path) -> dict[str, dict[str, bool]]:
    metadata = data_root / "modalities_present.json"
    if not metadata.is_file():
        raise FileNotFoundError(f"Missing modality metadata: {metadata}")
    raw = load_json(metadata)
    return {
        case_id: {
            "c0": bool(info.get("c0", False)),
            "lge": bool(info.get("lge", False)),
            "t2": bool(info.get("t2", False)),
        }
        for case_id, info in raw.items()
    }


def remove_small_components(arr: np.ndarray, class_id: int, min_voxels: int) -> np.ndarray:
    if min_voxels <= 1:
        return arr
    out = arr.copy()
    labels = measure.label(arr == class_id, connectivity=1)
    for component in measure.regionprops(labels):
        if component.area < min_voxels:
            out[labels == component.label] = 0
    return out


def prediction_derived_support(arr: np.ndarray) -> np.ndarray:
    labels = measure.label((arr == 4) | (arr == 5), connectivity=1)
    components = measure.regionprops(labels)
    if not components:
        return np.zeros_like(arr, dtype=bool)
    largest = max(components, key=lambda component: component.area)
    return labels == largest.label


def apply_rule(
    arr: np.ndarray,
    *,
    rule: str,
    info: dict[str, bool],
    support: np.ndarray | None,
    min_component_voxels: int,
) -> np.ndarray:
    out = arr.copy()
    if rule == "t2_missing_suppress_edema":
        if not info.get("t2", False):
            out[out == 4] = 0
        return out
    if rule == "myocardium_limited_pathology":
        if support is None:
            support = prediction_derived_support(out)
        out[((out == 4) | (out == 5)) & (support < 1)] = 0
        return out
    if rule == "small_component_filter":
        for class_id in CLASSES:
            out = remove_small_components(out, class_id, min_component_voxels)
        return out
    raise ValueError(f"Unknown rule: {rule}")


def summarize_change(before: np.ndarray, after: np.ndarray) -> dict[str, int]:
    out: dict[str, int] = {"changed_voxels": int(np.count_nonzero(before != after))}
    for class_id in CLASSES:
        before_mask = before == class_id
        after_mask = after == class_id
        out[f"class_{class_id}_before"] = int(np.count_nonzero(before_mask))
        out[f"class_{class_id}_after"] = int(np.count_nonzero(after_mask))
        out[f"class_{class_id}_removed"] = int(np.count_nonzero(before_mask & ~after_mask))
        out[f"class_{class_id}_added"] = int(np.count_nonzero(after_mask & ~before_mask))
    return out


def add_counts(dst: dict[str, int], src: dict[str, int]) -> None:
    for key, value in src.items():
        dst[key] += int(value)


def fmt(value: float | int | None) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    return f"{value:.4f}"


def write_summary_md(summary: dict, path: Path) -> None:
    groups = summary["groups"]
    lines = [
        f"# MyoPS-Net round4 {summary['variant']} changed voxels",
        "",
        f"- Rules: `{', '.join(summary['rules'])}`",
        f"- Small component threshold: `{summary['min_component_voxels']}` voxels",
        f"- Affects official T2-present validation cases: `{summary['affects_t2_present_cases']}`",
        "",
        "| source group | n cases | changed voxels | class_4 removed | class_5 removed | class_4 before -> after | class_5 before -> after |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in sorted(groups):
        row = groups[group]
        counts = row["counts"]
        lines.append(
            f"| {group} | {row['n_cases']} | {counts['changed_voxels']} | "
            f"{counts['class_4_removed']} | {counts['class_5_removed']} | "
            f"{counts['class_4_before']} -> {counts['class_4_after']} | "
            f"{counts['class_5_before']} -> {counts['class_5_after']} |"
        )
    lines.append("")
    lines.append("Per-class counts are compact CARE labels: class_4 edema, class_5 scar.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument(
        "--variant",
        choices=[
            "t2_missing_suppress_edema",
            "myocardium_limited_pathology",
            "small_component_filter",
            "combined_safe",
        ],
        required=True,
    )
    ap.add_argument("--support-dir", type=Path, default=None)
    ap.add_argument("--min-component-voxels", type=int, default=20)
    ap.add_argument(
        "--combined-rule",
        action="append",
        choices=["t2_missing_suppress_edema", "myocardium_limited_pathology", "small_component_filter"],
        default=None,
        help="Rule to apply for combined_safe; repeat to compose in order.",
    )
    ap.add_argument("--summary-json", type=Path, required=True)
    ap.add_argument("--summary-md", type=Path, required=True)
    args = ap.parse_args()

    modalities = load_modalities(args.data_root)
    if args.variant == "combined_safe":
        rules = args.combined_rule or ["t2_missing_suppress_edema"]
    else:
        rules = [args.variant]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for stale in args.output_dir.glob("*.nii.gz"):
        stale.unlink()

    totals: dict[str, int] = defaultdict(int)
    groups: dict[str, dict[str, object]] = {}
    per_case: dict[str, dict[str, object]] = {}

    for pred_path in sorted(args.input_dir.glob("*.nii.gz")):
        case_id = pred_path.name.replace(".nii.gz", "")
        info = modalities.get(case_id, {"c0": False, "lge": True, "t2": False})
        group = group_name(info)
        img = nib.load(str(pred_path))
        before = np.asanyarray(img.dataobj).astype(np.uint8, copy=False)
        after = before.copy()

        support = None
        if args.support_dir is not None:
            support_path = args.support_dir / pred_path.name
            if support_path.is_file():
                support = np.asanyarray(nib.load(str(support_path)).dataobj).astype(np.uint8, copy=False)

        for rule in rules:
            after = apply_rule(
                after,
                rule=rule,
                info=info,
                support=support,
                min_component_voxels=args.min_component_voxels,
            )

        counts = summarize_change(before, after)
        add_counts(totals, counts)
        row = groups.setdefault(
            group,
            {
                "n_cases": 0,
                "cases": [],
                "counts": defaultdict(int),
                "t2_present": bool(info.get("t2", False)),
            },
        )
        row["n_cases"] += 1
        row["cases"].append(case_id)
        add_counts(row["counts"], counts)
        per_case[case_id] = {
            "group": group,
            "modalities": info,
            "counts": counts,
        }

        out_img = nib.Nifti1Image(after.astype(np.uint8, copy=False), img.affine, img.header)
        nib.save(out_img, str(args.output_dir / pred_path.name))

    serial_groups = {}
    for group, row in groups.items():
        serial_groups[group] = {
            "n_cases": row["n_cases"],
            "cases": row["cases"],
            "counts": dict(row["counts"]),
        }

    t2_present_changed = [
        cid
        for cid, row in per_case.items()
        if row["modalities"].get("t2", False) and row["counts"]["changed_voxels"] > 0
    ]
    summary = {
        "variant": args.variant,
        "rules": rules,
        "input_dir": str(args.input_dir),
        "output_dir": str(args.output_dir),
        "data_root": str(args.data_root),
        "support_dir": str(args.support_dir) if args.support_dir else None,
        "support_note": (
            "myocardium_limited_pathology uses --support-dir masks when provided; otherwise it uses the "
            "largest connected component of the prediction-derived class_4/class_5 support, without GT."
        ),
        "min_component_voxels": args.min_component_voxels,
        "n_cases": len(per_case),
        "counts": dict(totals),
        "groups": serial_groups,
        "per_case": per_case,
        "affects_t2_present_cases": bool(t2_present_changed),
        "t2_present_changed_cases": t2_present_changed,
        "official_validation_note": (
            "Official MyoPS validation cases are expected to be T2-present; rules that only change "
            "T2-missing source cases should not affect official validation predictions."
        ),
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_summary_md(summary, args.summary_md)
    print(f"Wrote {args.output_dir}")
    print(f"Wrote {args.summary_json}")
    print(f"Wrote {args.summary_md}")


if __name__ == "__main__":
    main()
