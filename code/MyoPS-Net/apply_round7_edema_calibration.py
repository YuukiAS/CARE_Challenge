#!/usr/bin/env python3
"""Round7 MyoPS-Net edema calibration with scar-preserving routing.

This is an export-only diagnostic. It never uses GT labels to modify
predictions. The default scar route is round4 combined_safe for every case.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import nibabel as nib
import numpy as np
from skimage import measure


EDEMA = 4
SCAR = 5


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_fold_cases(fold_json: Path, fold: int) -> list[str]:
    data = load_json(fold_json)
    folds = data["folds"]
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold {fold} out of range [0, {len(folds)})")
    return sorted(folds[fold]["val"])


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


def group_name(info: dict[str, bool]) -> str:
    parts = []
    if info.get("c0"):
        parts.append("C0")
    if info.get("lge"):
        parts.append("LGE")
    if info.get("t2"):
        parts.append("T2")
    return "+".join(parts) or "none"


def complete_case(info: dict[str, bool]) -> bool:
    return bool(info.get("c0") and info.get("lge") and info.get("t2"))


def remove_small_components(mask: np.ndarray, min_voxels: int) -> np.ndarray:
    if min_voxels <= 1:
        return mask
    kept = mask.copy()
    labels = measure.label(mask, connectivity=1)
    for component in measure.regionprops(labels):
        if component.area < min_voxels:
            kept[labels == component.label] = False
    return kept


def prediction_derived_support(arr: np.ndarray) -> np.ndarray:
    labels = measure.label((arr == EDEMA) | (arr == SCAR), connectivity=1)
    components = measure.regionprops(labels)
    if not components:
        return np.zeros_like(arr, dtype=bool)
    largest = max(components, key=lambda component: component.area)
    return labels == largest.label


def load_arr(path: Path) -> tuple[nib.Nifti1Image, np.ndarray]:
    img = nib.load(str(path))
    arr = np.asanyarray(img.dataobj).astype(np.uint8, copy=True)
    return img, arr


def summarize_change(before: np.ndarray, after: np.ndarray) -> dict[str, int]:
    out: dict[str, int] = {"changed_voxels": int(np.count_nonzero(before != after))}
    for class_id in (EDEMA, SCAR):
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


def variant_prediction(
    *,
    variant: str,
    round4: np.ndarray,
    round5: np.ndarray | None,
    info: dict[str, bool],
    min_component_voxels: int,
) -> np.ndarray:
    out = round4.copy()

    if variant in {"keep_round4_scar_round5_edema_complete", "round5_edema_component_filter"}:
        if complete_case(info):
            if round5 is None:
                raise ValueError("round5 prediction is required for round5 edema variants")
            out[out == EDEMA] = 0
            out[(round5 == EDEMA) & (out != SCAR)] = EDEMA

    elif variant == "edema_component_filter":
        pass

    elif variant == "edema_support_limited":
        if info.get("t2", False):
            support = prediction_derived_support(round4)
            out[(out == EDEMA) & ~support] = 0

    else:
        raise ValueError(f"Unknown variant: {variant}")

    if variant in {"edema_component_filter", "round5_edema_component_filter"} and info.get("t2", False):
        edema_kept = remove_small_components(out == EDEMA, min_component_voxels)
        out[(out == EDEMA) & ~edema_kept] = 0

    # Preserve the known-best scar route for all round7 label-level variants.
    out[out == SCAR] = 0
    out[(round4 == SCAR) & (out != EDEMA)] = SCAR
    return out


def write_summary_md(summary: dict, path: Path) -> None:
    lines = [
        f"# MyoPS-Net round7 {summary['variant']} changed voxels",
        "",
        f"- Scar route: `{summary['scar_route']}`",
        f"- Round4 prediction dir: `{summary['round4_pred_dir']}`",
        f"- Round5/fullmod prediction dir: `{summary['round5_pred_dir']}`",
        f"- Small edema component threshold: `{summary['min_component_voxels']}` voxels",
        "",
        "| modality group | n cases | changed voxels | class_4 before -> after | class_4 added | class_4 removed | class_5 before -> after | class_5 added | class_5 removed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in sorted(summary["groups"]):
        row = summary["groups"][group]
        counts = row["counts"]
        lines.append(
            f"| {group} | {row['n_cases']} | {counts['changed_voxels']} | "
            f"{counts['class_4_before']} -> {counts['class_4_after']} | "
            f"{counts['class_4_added']} | {counts['class_4_removed']} | "
            f"{counts['class_5_before']} -> {counts['class_5_after']} | "
            f"{counts['class_5_added']} | {counts['class_5_removed']} |"
        )
    lines.extend(
        [
            "",
            "Class labels are compact CARE labels: class_4 edema and class_5 scar.",
            "Class_5 should remain unchanged except where edema replacement would otherwise collide; the script reapplies round4 scar last.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--round4-pred-dir", type=Path, required=True)
    ap.add_argument("--round5-pred-dir", type=Path, default=None)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--fold-json", type=Path, required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument(
        "--variant",
        choices=[
            "keep_round4_scar_round5_edema_complete",
            "edema_support_limited",
            "edema_component_filter",
            "round5_edema_component_filter",
        ],
        required=True,
    )
    ap.add_argument("--min-component-voxels", type=int, default=20)
    ap.add_argument("--summary-json", type=Path, required=True)
    ap.add_argument("--summary-md", type=Path, required=True)
    args = ap.parse_args()

    modalities = load_modalities(args.data_root)
    case_ids = load_fold_cases(args.fold_json, args.fold)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for stale in args.output_dir.glob("*.nii.gz"):
        stale.unlink()

    totals: dict[str, int] = defaultdict(int)
    groups: dict[str, dict[str, object]] = {}
    per_case: dict[str, dict[str, object]] = {}

    for case_id in case_ids:
        pred_path = args.round4_pred_dir / f"{case_id}.nii.gz"
        if not pred_path.is_file():
            raise FileNotFoundError(f"Missing round4 prediction: {pred_path}")
        img, round4 = load_arr(pred_path)
        round5 = None
        if args.round5_pred_dir is not None:
            round5_path = args.round5_pred_dir / f"{case_id}.nii.gz"
            if round5_path.is_file():
                _, round5 = load_arr(round5_path)

        info = modalities.get(case_id, {"c0": False, "lge": True, "t2": False})
        group = group_name(info)
        after = variant_prediction(
            variant=args.variant,
            round4=round4,
            round5=round5,
            info=info,
            min_component_voxels=args.min_component_voxels,
        )
        counts = summarize_change(round4, after)
        add_counts(totals, counts)

        row = groups.setdefault(group, {"n_cases": 0, "cases": [], "counts": defaultdict(int)})
        row["n_cases"] += 1
        row["cases"].append(case_id)
        add_counts(row["counts"], counts)
        per_case[case_id] = {"group": group, "modalities": info, "counts": counts}

        out_img = nib.Nifti1Image(after.astype(np.uint8, copy=False), img.affine, img.header)
        nib.save(out_img, str(args.output_dir / f"{case_id}.nii.gz"))

    serial_groups = {
        group: {"n_cases": row["n_cases"], "cases": row["cases"], "counts": dict(row["counts"])}
        for group, row in groups.items()
    }
    summary = {
        "variant": args.variant,
        "scar_route": "round4 combined_safe class_5 reapplied for all cases",
        "round4_pred_dir": str(args.round4_pred_dir),
        "round5_pred_dir": str(args.round5_pred_dir) if args.round5_pred_dir else None,
        "output_dir": str(args.output_dir),
        "data_root": str(args.data_root),
        "fold_json": str(args.fold_json),
        "fold": args.fold,
        "n_cases": len(per_case),
        "min_component_voxels": args.min_component_voxels,
        "counts": dict(totals),
        "groups": serial_groups,
        "per_case": per_case,
        "notes": [
            "No GT labels are used to modify predictions.",
            "Every variant preserves class_5 from round4 combined_safe.",
            "Edema changes are restricted to T2-present cases for support/filter variants; round5 edema is copied only for complete C0+LGE+T2 cases.",
        ],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_summary_md(summary, args.summary_md)
    print(f"Wrote {args.output_dir}")
    print(f"Wrote {args.summary_json} and {args.summary_md}")


if __name__ == "__main__":
    main()
