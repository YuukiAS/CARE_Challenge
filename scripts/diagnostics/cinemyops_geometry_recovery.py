#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk


DEFAULT_TRAIN_ROOT = Path("data/CARE_Challenge/CineMyoPS_train")
DEFAULT_OUTPUT_DIR = Path("results/20260625_cine_geometry")


@dataclass(frozen=True)
class CropBox:
    z0: int
    z1: int
    y0: int
    y1: int
    x0: int
    x1: int


def discover_train_pairs(root: Path) -> list[tuple[str, str, Path, Path]]:
    pairs: list[tuple[str, str, Path, Path]] = []
    for cine_path in sorted(root.glob("*/*_Cine.nii.gz")):
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        label_path = cine_path.parent / f"{case_id}_gd.nii.gz"
        if label_path.is_file():
            pairs.append((cine_path.parent.name, case_id, cine_path, label_path))
    return pairs


def extract_frame(image4d: sitk.Image, frame_index: int = 0) -> sitk.Image:
    size = list(image4d.GetSize())
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size[0], size[1], size[2], 0])
    extractor.SetIndex([0, 0, 0, int(frame_index)])
    return extractor.Execute(image4d)


def rounded(values: tuple[float, ...], digits: int = 6) -> list[float]:
    return [round(float(v), digits) for v in values]


def allclose_tuple(a: tuple[float, ...], b: tuple[float, ...], atol: float) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), rtol=0.0, atol=atol))


def values_counts(arr: np.ndarray) -> dict[int, int]:
    values, counts = np.unique(arr, return_counts=True)
    return {int(v): int(c) for v, c in zip(values.tolist(), counts.tolist(), strict=True)}


def foreground_bbox(mask: np.ndarray, margin_yx: int) -> CropBox:
    coords = np.argwhere(mask)
    if coords.size == 0:
        raise ValueError("foreground mask is empty")
    z0, y0, x0 = coords.min(axis=0).tolist()
    z1, y1, x1 = (coords.max(axis=0) + 1).tolist()
    shape_z, shape_y, shape_x = mask.shape
    return CropBox(
        z0=max(0, z0),
        z1=min(shape_z, z1),
        y0=max(0, y0 - margin_yx),
        y1=min(shape_y, y1 + margin_yx),
        x0=max(0, x0 - margin_yx),
        x1=min(shape_x, x1 + margin_yx),
    )


def crop_and_invert(arr: np.ndarray, crop: CropBox) -> tuple[np.ndarray, np.ndarray]:
    cropped = arr[crop.z0 : crop.z1, crop.y0 : crop.y1, crop.x0 : crop.x1]
    restored = np.zeros_like(arr)
    restored[crop.z0 : crop.z1, crop.y0 : crop.y1, crop.x0 : crop.x1] = cropped
    return cropped, restored


def resample_label_to_frame(label: sitk.Image, frame: sitk.Image) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(frame)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(label)


def serialise_csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=True)
    return value


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: serialise_csv_value(row.get(key, "")) for key in fieldnames})


def audit_case(center: str, case_id: str, cine_path: Path, label_path: Path, margin_yx: int) -> tuple[dict[str, Any], dict[str, Any]]:
    cine = sitk.ReadImage(str(cine_path))
    frame0 = extract_frame(cine, 0)
    label = sitk.ReadImage(str(label_path))
    label_arr = sitk.GetArrayFromImage(label)
    foreground = label_arr > 0

    size_match = tuple(frame0.GetSize()) == tuple(label.GetSize())
    spacing_match = allclose_tuple(frame0.GetSpacing(), label.GetSpacing(), atol=1e-6)
    origin_match = allclose_tuple(frame0.GetOrigin(), label.GetOrigin(), atol=5e-6)
    direction_match = allclose_tuple(frame0.GetDirection(), label.GetDirection(), atol=1e-6)
    strict_match = size_match and spacing_match and origin_match and direction_match

    resampled = resample_label_to_frame(label, frame0)
    resampled_arr = sitk.GetArrayFromImage(resampled)
    resample_changed_voxels = int(np.count_nonzero(resampled_arr != label_arr)) if resampled_arr.shape == label_arr.shape else None

    crop = foreground_bbox(foreground, margin_yx=margin_yx)
    cropped, restored = crop_and_invert(label_arr, crop)
    foreground_voxels = int(foreground.sum())
    restored_foreground_voxels = int((restored > 0).sum())
    missing_foreground_voxels = int(np.count_nonzero(np.logical_and(foreground, restored == 0)))
    extra_foreground_voxels = int(np.count_nonzero(np.logical_and(restored > 0, ~foreground)))
    crop_preserves_foreground = missing_foreground_voxels == 0 and restored_foreground_voxels == foreground_voxels
    label_roundtrip_exact = bool(np.array_equal(restored, label_arr))

    crop_row = {
        "center": center,
        "case_id": case_id,
        "strict_frame0_label_metadata_match": strict_match,
        "crop_z0": crop.z0,
        "crop_z1": crop.z1,
        "crop_y0": crop.y0,
        "crop_y1": crop.y1,
        "crop_x0": crop.x0,
        "crop_x1": crop.x1,
        "original_shape_zyx": list(label_arr.shape),
        "cropped_shape_zyx": list(cropped.shape),
        "foreground_voxels": foreground_voxels,
        "restored_foreground_voxels": restored_foreground_voxels,
        "missing_foreground_voxels": missing_foreground_voxels,
        "extra_foreground_voxels": extra_foreground_voxels,
        "crop_preserves_foreground": crop_preserves_foreground,
        "label_roundtrip_exact": label_roundtrip_exact,
        "metadata_restore_policy": "inverse array is written with frame0 CopyInformation for model outputs",
        "frame0_size": list(frame0.GetSize()),
        "frame0_spacing": rounded(frame0.GetSpacing()),
        "frame0_origin": rounded(frame0.GetOrigin()),
        "frame0_direction": rounded(frame0.GetDirection()),
    }

    row = {
        "center": center,
        "case_id": case_id,
        "cine_path": str(cine_path),
        "label_path": str(label_path),
        "frames": int(cine.GetSize()[3]),
        "cine_size": list(cine.GetSize()),
        "frame0_size": list(frame0.GetSize()),
        "label_size": list(label.GetSize()),
        "frame0_spacing": rounded(frame0.GetSpacing()),
        "label_spacing": rounded(label.GetSpacing()),
        "frame0_origin": rounded(frame0.GetOrigin()),
        "label_origin": rounded(label.GetOrigin()),
        "frame0_direction": rounded(frame0.GetDirection()),
        "label_direction": rounded(label.GetDirection()),
        "size_match": size_match,
        "spacing_match": spacing_match,
        "origin_match": origin_match,
        "direction_match": direction_match,
        "strict_frame0_label_metadata_match": strict_match,
        "label_values": values_counts(label_arr),
        "foreground_voxels": foreground_voxels,
        "resample_to_frame0_changed_voxels": resample_changed_voxels,
        "repair_policy": "safe" if strict_match else "holdout_for_header_or_resample_repair",
        "crop_preserves_foreground": crop_preserves_foreground,
        "label_roundtrip_exact": label_roundtrip_exact,
    }
    return row, crop_row


def write_geometry_audit(
    safe_rows: list[dict[str, Any]],
    mismatch_rows: list[dict[str, Any]],
    crop_rows: list[dict[str, Any]],
    path: Path,
) -> None:
    mismatch_names = [f"{row['center']}_{row['case_id']}" for row in mismatch_rows]
    origin_mismatches = [f"{row['center']}_{row['case_id']}" for row in mismatch_rows if not row["origin_match"]]
    spacing_mismatches = [f"{row['center']}_{row['case_id']}" for row in mismatch_rows if not row["spacing_match"]]
    crop_failures = [f"{row['center']}_{row['case_id']}" for row in crop_rows if not row["crop_preserves_foreground"]]
    roundtrip_failures = [f"{row['center']}_{row['case_id']}" for row in crop_rows if not row["label_roundtrip_exact"]]
    lines = [
        "# CineMyoPS Geometry Audit",
        "",
        "## Summary",
        "",
        f"- train cases audited: {len(safe_rows) + len(mismatch_rows)}",
        f"- strict safe cases: {len(safe_rows)}",
        f"- metadata mismatch cases: {len(mismatch_rows)}",
        f"- origin mismatch cases: `{origin_mismatches}`",
        f"- spacing mismatch cases: `{spacing_mismatches}`",
        f"- crop foreground failures: `{crop_failures}`",
        f"- exact label roundtrip failures: `{roundtrip_failures}`",
        "",
        "## Contract",
        "",
        "- Frame 0 is the supervised reference frame for this gate.",
        "- `safe_cases.csv` requires size, spacing, origin, and direction match between extracted frame 0 and the raw label under the recorded tolerances.",
        "- `mismatch_cases.csv` keeps cases with metadata discrepancies out of the first supervised reference-control subset; they are not discarded.",
        "- `crop_roundtrip.csv` uses the train-label foreground bounding box with an in-plane margin as a protocol check for heart-ROI crop/inverse safety.",
        "- Model outputs should be inverse-mapped into the original frame array and written with `frame0` metadata via `CopyInformation(frame0)`.",
        "",
        "## Interpretation",
        "",
    ]
    if len(safe_rows) >= 59 and not crop_failures and not roundtrip_failures:
        lines.extend(
            [
                "The safe subset is large enough to continue a reference-frame control without waiting for mismatch repair.",
                "The five mismatch cases should remain in a separate repair queue for explicit header or nearest-neighbor resampling review.",
            ]
        )
    else:
        lines.append("The safe-subset gate is not yet clean enough for training; inspect the failure rows before submitting a job.")
    lines.extend(["", "## Mismatch Cases", ""])
    if mismatch_rows:
        for row in mismatch_rows:
            reasons = []
            for key in ["size_match", "spacing_match", "origin_match", "direction_match"]:
                if not row[key]:
                    reasons.append(key.replace("_match", ""))
            lines.append(f"- `{row['center']}_{row['case_id']}`: {', '.join(reasons)}")
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_decision(safe_rows: list[dict[str, Any]], mismatch_rows: list[dict[str, Any]], crop_rows: list[dict[str, Any]], path: Path) -> str:
    crop_ok = all(bool(row["crop_preserves_foreground"]) and bool(row["label_roundtrip_exact"]) for row in crop_rows)
    if safe_rows and crop_ok and len(safe_rows) >= 59:
        status = "GO_CINE_REFERENCE"
    elif safe_rows and crop_ok:
        status = "REVISE_GEOMETRY_SAFE_SUBSET_ONLY"
    elif mismatch_rows:
        status = "REVISE_MISMATCH_REPAIR"
    else:
        status = "STOP_CINE_GEOMETRY"
    lines = [
        "# Decision 20260625 Cine Geometry",
        "",
        f"status: `{status}`",
        "",
        "## Evidence",
        "",
        f"- safe strict frame0/label metadata matches: {len(safe_rows)}",
        f"- mismatch cases held out for repair: {len(mismatch_rows)}",
        f"- crop roundtrip rows: {len(crop_rows)}",
        f"- crop foreground preserved for all rows: {crop_ok}",
        "",
        "## Next Step",
        "",
    ]
    if status == "GO_CINE_REFERENCE":
        lines.append("Run the next reference-frame control on `safe_cases.csv`; keep mismatch rows out of supervised training until header/resampling repair is reviewed.")
    elif status == "REVISE_GEOMETRY_SAFE_SUBSET_ONLY":
        lines.append("Use only the safe subset for diagnostics, but do not submit training until the subset size and sampling policy are accepted.")
    elif status == "REVISE_MISMATCH_REPAIR":
        lines.append("Repair or resample mismatch cases before training because the crop/inverse or safe-subset gate is not clean.")
    else:
        lines.append("Stop the Cine route until raw data and label geometry can be established.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status


def write_manifest(output_dir: Path, status: str) -> None:
    files = [
        "safe_cases.csv",
        "mismatch_cases.csv",
        "crop_roundtrip.csv",
        "geometry_audit.md",
        "decision.md",
        "result.md",
        "MANIFEST.md",
    ]
    lines = [
        "# Manifest 20260625 Cine Geometry",
        "",
        f"- status: `{status}`",
        "- task: `prompts/tasks/20260625_cine_geometry.md`",
        "",
        "## Files",
        "",
    ]
    for name in files:
        lines.append(f"- `{output_dir / name}`")
    (output_dir / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_result(output_dir: Path, safe_rows: list[dict[str, Any]], mismatch_rows: list[dict[str, Any]], status: str) -> None:
    mismatch_names = [f"{row['center']}_{row['case_id']}" for row in mismatch_rows]
    lines = [
        "# Result 20260625 Cine Geometry",
        "",
        f"status: `{status}`",
        "",
        "## Summary",
        "",
        f"- Audited {len(safe_rows) + len(mismatch_rows)} CineMyoPS train cases.",
        f"- Wrote {len(safe_rows)} strict safe cases to `safe_cases.csv`.",
        f"- Wrote {len(mismatch_rows)} metadata mismatch cases to `mismatch_cases.csv`: `{mismatch_names}`.",
        "- Crop/inverse protocol check is recorded in `crop_roundtrip.csv`.",
        "- No validation submission, upload package, network access, or training job was used by this script.",
        "",
        "## Caveat",
        "",
        "The crop proof uses train labels as an oracle protocol check. A training/inference entrypoint should replace that oracle with a CineMA anatomy union or another non-GT heart prior before model evaluation.",
        "",
        "## Artifacts",
        "",
        "- `geometry_audit.md`",
        "- `safe_cases.csv`",
        "- `mismatch_cases.csv`",
        "- `crop_roundtrip.csv`",
        "- `decision.md`",
        "- `MANIFEST.md`",
    ]
    (output_dir / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build CineMyoPS safe/mismatch geometry split and crop roundtrip evidence.")
    parser.add_argument("--train-root", type=Path, default=DEFAULT_TRAIN_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--margin-yx", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    crop_rows: list[dict[str, Any]] = []
    for center, case_id, cine_path, label_path in discover_train_pairs(args.train_root):
        row, crop_row = audit_case(center, case_id, cine_path, label_path, margin_yx=args.margin_yx)
        rows.append(row)
        crop_rows.append(crop_row)

    safe_rows = [row for row in rows if row["strict_frame0_label_metadata_match"]]
    mismatch_rows = [row for row in rows if not row["strict_frame0_label_metadata_match"]]

    write_csv(safe_rows, args.output_dir / "safe_cases.csv")
    write_csv(mismatch_rows, args.output_dir / "mismatch_cases.csv")
    write_csv(crop_rows, args.output_dir / "crop_roundtrip.csv")
    write_geometry_audit(safe_rows, mismatch_rows, crop_rows, args.output_dir / "geometry_audit.md")
    status = write_decision(safe_rows, mismatch_rows, crop_rows, args.output_dir / "decision.md")
    write_result(args.output_dir, safe_rows, mismatch_rows, status)
    write_manifest(args.output_dir, status)

    print(json.dumps({"status": status, "safe_cases": len(safe_rows), "mismatch_cases": len(mismatch_rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
