#!/usr/bin/env python3
"""Lane B Round03 hosted calibration preparation for CineMyoPS topology LCC.

This script is packaging-QA only. It does not train, submit Slurm jobs, run
inference, create a validation zip, upload, or download weights.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration"

PATHOLOGY_DIRECT_UPLOAD = (
    REPO_ROOT
    / "results/submissions/care_myocardium_validation/upload_ready/"
    / "nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921"
)
PATHOLOGY_DIRECT_TREE = PATHOLOGY_DIRECT_UPLOAD / "submission_tree"
PATHOLOGY_DIRECT_MANIFEST = PATHOLOGY_DIRECT_UPLOAD / "manifest.json"

TOPOLOGY_LCC_COMPACT_DIR = (
    REPO_ROOT / "results/predictions/CineMyoPS_R8_validation_hd_repair/pathology_largest_component/fold_0"
)

CINE_VAL_ROOT = REPO_ROOT / "data/CARE_Challenge/CineMyoPS_val"
MYOPS_VAL_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_val"

CINE_COMPACT_TO_RAW = {0: 0, 1: 200, 2: 500, 3: 2221}
LEGAL_CINE_COMPACT = set(CINE_COMPACT_TO_RAW)
LEGAL_CINE_RAW = {0, 200, 500, 2221}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows for {path}")
    names = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        return f"{value:.{digits}f}"
    return str(value)


def image_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    image = sitk.ReadImage(str(path))
    return image, sitk.GetArrayFromImage(image)


def write_like(array: np.ndarray, reference: sitk.Image, path: Path) -> None:
    image = sitk.GetImageFromArray(array.astype(np.uint16, copy=False))
    image.CopyInformation(reference)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(image, str(path))


def spacing_zyx(image: sitk.Image) -> tuple[float, ...]:
    return tuple(float(v) for v in image.GetSpacing()[::-1])


def discover_cine_validation_cases(root: Path) -> list[str]:
    return sorted(p.name.replace("_Cine.nii.gz", "") for p in root.glob("**/Case*_Cine.nii.gz"))


def discover_myops_validation_cases(root: Path) -> list[str]:
    return sorted(p.name for p in root.glob("**/Case*") if p.is_dir() and (p / f"{p.name}_LGE.nii.gz").is_file())


def prediction_map_from_dir(root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(root.glob("Case*.nii.gz")):
        mapping[path.name.replace(".nii.gz", "")] = path
    return mapping


def prediction_map_from_submission_branch(branch_root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(branch_root.glob("Anonymous Center/Case*/Case*_pred.nii.gz")):
        mapping[path.parent.name] = path
    return mapping


def compact_to_raw(compact: np.ndarray) -> np.ndarray:
    raw = np.zeros_like(compact, dtype=np.uint16)
    for src, dst in CINE_COMPACT_TO_RAW.items():
        raw[compact == src] = dst
    return raw


def bbox(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


def bbox_text(box: tuple[np.ndarray, np.ndarray] | None) -> str:
    if box is None:
        return ""
    return f"{box[0].tolist()}..{box[1].tolist()}"


def bbox_gap_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    gap = np.zeros(len(spacing), dtype=np.float64)
    for axis in range(len(spacing)):
        if a[1][axis] < b[0][axis]:
            gap[axis] = b[0][axis] - a[1][axis]
        elif b[1][axis] < a[0][axis]:
            gap[axis] = a[0][axis] - b[1][axis]
    return float(np.linalg.norm(gap * np.asarray(spacing, dtype=np.float64)))


def center_distance_mm(a: tuple[np.ndarray, np.ndarray] | None, b: tuple[np.ndarray, np.ndarray] | None, spacing: tuple[float, ...]) -> float | None:
    if a is None or b is None:
        return None
    ca = (a[0].astype(np.float64) + a[1].astype(np.float64)) / 2.0
    cb = (b[0].astype(np.float64) + b[1].astype(np.float64)) / 2.0
    return float(np.linalg.norm((ca - cb) * np.asarray(spacing, dtype=np.float64)))


def component_stats(mask: np.ndarray) -> tuple[int, int, float]:
    cc, n_comp = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    if n_comp == 0:
        return 0, 0, 0.0
    counts = np.bincount(cc.ravel())
    largest = int(counts[1:].max())
    total = int(mask.sum())
    return int(n_comp), largest, float(largest / total) if total else 0.0


def label_histogram(arr: np.ndarray) -> dict[int, int]:
    values, counts = np.unique(arr, return_counts=True)
    return {int(v): int(c) for v, c in zip(values, counts)}


def label_histogram_text(hist: dict[int, int]) -> str:
    return json.dumps({str(k): v for k, v in sorted(hist.items())}, sort_keys=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_raw_case(case_id: str, raw_path: Path, *, variant: str, compact_labels: set[int] | None = None) -> dict[str, object]:
    image, raw = image_array(raw_path)
    spacing = spacing_zyx(image)
    hist = label_histogram(raw)
    scar = raw == 2221
    myocardium = raw == 200
    lv = raw == 500
    anatomy = myocardium | lv
    scar_box = bbox(scar)
    anatomy_box = bbox(anatomy)
    comp_count, largest_voxels, largest_fraction = component_stats(scar)
    volume_mm3 = int(scar.sum()) * float(np.prod(spacing))
    return {
        "case_id": case_id,
        "variant": variant,
        "source_path": rel(raw_path),
        "compact_labels": json.dumps(sorted(compact_labels)) if compact_labels is not None else "",
        "compact_labels_legal": compact_labels <= LEGAL_CINE_COMPACT if compact_labels is not None else "",
        "raw_labels": label_histogram_text(hist),
        "raw_label_subset_legal": set(hist) <= LEGAL_CINE_RAW,
        "raw_2221_non_empty": int(scar.sum()) > 0,
        "raw_2221_voxels": int(scar.sum()),
        "raw_2221_volume_mm3": volume_mm3,
        "raw_2221_components": comp_count,
        "largest_raw_2221_voxels": largest_voxels,
        "largest_raw_2221_fraction": largest_fraction,
        "raw_200_voxels": int(myocardium.sum()),
        "raw_500_voxels": int(lv.sum()),
        "anatomy_voxels": int(anatomy.sum()),
        "scar_anatomy_ratio": float(int(scar.sum()) / max(1, int(anatomy.sum()))),
        "raw_2221_bbox": bbox_text(scar_box),
        "anatomy_bbox": bbox_text(anatomy_box),
        "raw_2221_bbox_gap_mm": bbox_gap_mm(scar_box, anatomy_box, spacing),
        "raw_2221_center_distance_mm": center_distance_mm(scar_box, anatomy_box, spacing),
        "image_size_xyz": json.dumps(list(image.GetSize())),
        "spacing_xyz": json.dumps([float(v) for v in image.GetSpacing()]),
        "fallback_required": int(scar.sum()) == 0,
    }


def myops_case_hash_rows(source_root: Path, staged_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    source_map = prediction_map_from_submission_branch(source_root)
    staged_map = prediction_map_from_submission_branch(staged_root)
    for cid in sorted(source_map):
        rows.append(
            {
                "case_id": cid,
                "source_path": rel(source_map[cid]),
                "staged_path": rel(staged_map[cid]),
                "sha256_source": sha256(source_map[cid]),
                "sha256_staged": sha256(staged_map[cid]),
                "hash_match": sha256(source_map[cid]) == sha256(staged_map[cid]),
            }
        )
    return rows


def write_summary(
    *,
    out_root: Path,
    run_id: str,
    qa_pass: bool,
    fail_reasons: list[str],
    staging_tree: Path,
    myops_rows: list[dict[str, object]],
    raw_rows: list[dict[str, object]],
    diff_rows: list[dict[str, object]],
    previous_manifest: dict,
) -> None:
    mean_components = float(np.mean([int(r["raw_2221_components"]) for r in raw_rows]))
    mean_largest = float(np.mean([float(r["largest_raw_2221_fraction"]) for r in raw_rows]))
    total_2221 = int(sum(int(r["raw_2221_voxels"]) for r in raw_rows))
    previous_total_2221 = int(sum(int(r["previous_raw_2221_voxels"]) for r in diff_rows))
    current_total_2221 = int(sum(int(r["current_raw_2221_voxels"]) for r in diff_rows))
    removed_total = int(sum(int(r["raw_2221_voxels_removed_vs_pathology_direct"]) for r in diff_rows))

    summary_lines = [
        "# Lane B Round03 hosted calibration packaging QA",
        "",
        f"- Run id: `{run_id}`",
        f"- QA status: `{'PASS' if qa_pass else 'FAIL'}`",
        f"- Candidate staging tree: `{rel(staging_tree)}`",
        "- Zip created: `no`",
        "- Upload performed: `no`",
        f"- MyoPS branch source: `{rel(PATHOLOGY_DIRECT_TREE / 'MyoPS')}`",
        f"- Cine compact topology_lcc source: `{rel(TOPOLOGY_LCC_COMPACT_DIR)}`",
        f"- Previous official pathology_direct source: `{rel(PATHOLOGY_DIRECT_TREE / 'CineMyoPS')}`",
        "",
        "## QA gates",
        "",
        "| gate | result |",
        "| --- | --- |",
        f"| raw Cine label subset in {{0,200,500,2221}} | {'pass' if all(r['raw_label_subset_legal'] for r in raw_rows) else 'fail'} |",
        f"| compact Cine labels in {{0,1,2,3}} | {'pass' if all(r['compact_labels_legal'] for r in raw_rows) else 'fail'} |",
        f"| raw 2221 non-empty | {'pass' if all(r['raw_2221_non_empty'] for r in raw_rows) else 'fail'} |",
        f"| Cine validation case count | {len(raw_rows)} |",
        f"| MyoPS copied file hash match | {'pass' if all(r['hash_match'] for r in myops_rows) else 'fail'} |",
        f"| generated zip/upload | no |",
        "",
        "## Aggregate Cine topology_lcc QC",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| cases | {len(raw_rows)} |",
        f"| total raw 2221 voxels | {total_2221} |",
        f"| mean raw 2221 components | {mean_components:.4f} |",
        f"| mean largest-component fraction | {mean_largest:.4f} |",
        f"| previous pathology_direct raw 2221 voxels | {previous_total_2221} |",
        f"| current topology_lcc raw 2221 voxels | {current_total_2221} |",
        f"| removed 2221 voxels vs pathology_direct | {removed_total} |",
        "",
        "## Failure reasons",
        "",
    ]
    if fail_reasons:
        summary_lines.extend(f"- {reason}" for reason in fail_reasons)
    else:
        summary_lines.append("- none")
    summary_lines.extend(
        [
            "",
            "## Source manifest anchor",
            "",
            f"- Previous official submission id: `{previous_manifest.get('submission_id')}`",
            f"- Previous MyoPS source: `{previous_manifest.get('myops', {}).get('source')}`",
            f"- Previous Cine combine mode: `{previous_manifest.get('cine', {}).get('combine_mode')}`",
        ]
    )
    (out_root / "packaging_qc_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    manifest_lines = [
        f"run_id={run_id}",
        f"qa_status={'PASS' if qa_pass else 'FAIL'}",
        f"staging_tree={staging_tree}",
        "zip_created=no",
        "upload_performed=no",
        f"myops_branch_source={PATHOLOGY_DIRECT_TREE / 'MyoPS'}",
        f"myops_model_source=existing nnUNet conservative baseline copied from previous pathology_direct submission tree",
        f"cine_compact_source={TOPOLOGY_LCC_COMPACT_DIR}",
        "cine_candidate=Cine_topology_lcc",
        "cine_compact_mapping=0->0,1->200,2->500,3->2221",
        f"previous_pathology_direct_tree={PATHOLOGY_DIRECT_TREE / 'CineMyoPS'}",
        f"cine_cases={len(raw_rows)}",
        f"myops_cases={len(myops_rows)}",
        f"fail_reasons={json.dumps(fail_reasons, ensure_ascii=False)}",
    ]
    (out_root / "candidate_package_manifest.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    readme_lines = [
        "# Hosted calibration candidate readme",
        "",
        f"Candidate: `{run_id}`",
        "",
        "This is a staging tree for a future manual hosted calibration decision. No zip was created and no upload was performed by this script.",
        "",
        "Branch sources:",
        f"- `MyoPS/`: copied unchanged from `{rel(PATHOLOGY_DIRECT_TREE / 'MyoPS')}`.",
        f"- `CineMyoPS/`: regenerated from compact topology_lcc predictions under `{rel(TOPOLOGY_LCC_COMPACT_DIR)}` using compact mapping `1=200`, `2=500`, `3=2221`.",
        "",
        "Manual packaging target, if the user decides to spend a validation attempt:",
        f"- tree: `{rel(staging_tree)}`",
        "- expected zip roots: `MyoPS/` and `CineMyoPS/` only",
        "- expected zip filename: `CARE-Myocardium-OrganAgent.zip`",
        "",
        f"QA result: `{'PASS' if qa_pass else 'FAIL'}`",
    ]
    if qa_pass:
        readme_lines.append("Conclusion: 可以由用户手动提交 hosted calibration；这仍是 calibration experiment，不是最终模型。")
    else:
        readme_lines.append("Conclusion: QA did not pass; do not package/upload until fail reasons are fixed.")
    (out_root / "hosted_calibration_candidate_readme.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=f"nnUNet_MyoPS+Cine_topology_lcc_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    out_root = args.out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    staging_tree = out_root / "staging" / args.run_id / "submission_tree"
    if staging_tree.exists():
        raise RuntimeError(f"Refusing to overwrite existing staging tree: {staging_tree}")

    required = [
        PATHOLOGY_DIRECT_TREE / "MyoPS",
        PATHOLOGY_DIRECT_TREE / "CineMyoPS",
        PATHOLOGY_DIRECT_MANIFEST,
        TOPOLOGY_LCC_COMPACT_DIR,
        CINE_VAL_ROOT,
        MYOPS_VAL_ROOT,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)

    previous_manifest = read_json(PATHOLOGY_DIRECT_MANIFEST)
    expected_cine_cases = discover_cine_validation_cases(CINE_VAL_ROOT)
    expected_myops_cases = discover_myops_validation_cases(MYOPS_VAL_ROOT)
    compact_map = prediction_map_from_dir(TOPOLOGY_LCC_COMPACT_DIR)
    previous_cine_map = prediction_map_from_submission_branch(PATHOLOGY_DIRECT_TREE / "CineMyoPS")

    fail_reasons: list[str] = []
    if sorted(compact_map) != expected_cine_cases:
        fail_reasons.append(f"Cine compact case list mismatch: expected={expected_cine_cases}, found={sorted(compact_map)}")
    if sorted(previous_cine_map) != expected_cine_cases:
        fail_reasons.append(f"Previous pathology_direct Cine case list mismatch: expected={expected_cine_cases}, found={sorted(previous_cine_map)}")

    myops_source = PATHOLOGY_DIRECT_TREE / "MyoPS"
    myops_staged = staging_tree / "MyoPS"
    shutil.copytree(myops_source, myops_staged, copy_function=shutil.copy2)
    myops_rows = myops_case_hash_rows(myops_source, myops_staged)
    staged_myops_cases = sorted(r["case_id"] for r in myops_rows)
    if staged_myops_cases != expected_myops_cases:
        fail_reasons.append(f"MyoPS staged case list mismatch: expected={expected_myops_cases}, found={staged_myops_cases}")
    if not all(r["hash_match"] for r in myops_rows):
        fail_reasons.append("MyoPS copied file hashes do not match source package tree")

    raw_rows: list[dict[str, object]] = []
    topology_rows: list[dict[str, object]] = []
    diff_rows: list[dict[str, object]] = []
    for case_id in expected_cine_cases:
        compact_path = compact_map[case_id]
        image, compact = image_array(compact_path)
        compact_labels = set(label_histogram(compact))
        raw = compact_to_raw(compact)
        raw_path = staging_tree / "CineMyoPS" / "Anonymous Center" / case_id / f"{case_id}_pred.nii.gz"
        write_like(raw, image, raw_path)

        row = summarize_raw_case(case_id, raw_path, variant="topology_lcc", compact_labels=compact_labels)
        raw_rows.append(row)
        topology_rows.append(
            {
                **row,
                "compact_source_path": rel(compact_path),
                "compact_mapping_confirmed": "1=200;2=500;3=2221",
                "fallback_used": False,
            }
        )
        if not row["compact_labels_legal"]:
            fail_reasons.append(f"{case_id}: compact labels outside {sorted(LEGAL_CINE_COMPACT)}")
        if not row["raw_label_subset_legal"]:
            fail_reasons.append(f"{case_id}: raw labels outside {sorted(LEGAL_CINE_RAW)}")
        if not row["raw_2221_non_empty"]:
            fail_reasons.append(f"{case_id}: raw 2221 empty; no fallback applied in Round03 staging")

        previous_row = summarize_raw_case(case_id, previous_cine_map[case_id], variant="pathology_direct")
        previous_image, previous_raw = image_array(previous_cine_map[case_id])
        if previous_raw.shape != raw.shape:
            removed = added = overlap = -1
        else:
            previous_scar = previous_raw == 2221
            current_scar = raw == 2221
            removed = int(np.logical_and(previous_scar, ~current_scar).sum())
            added = int(np.logical_and(~previous_scar, current_scar).sum())
            overlap = int(np.logical_and(previous_scar, current_scar).sum())
        diff_rows.append(
            {
                "case_id": case_id,
                "previous_variant": "pathology_direct",
                "current_variant": "topology_lcc",
                "previous_raw_labels": previous_row["raw_labels"],
                "current_raw_labels": row["raw_labels"],
                "previous_raw_2221_voxels": previous_row["raw_2221_voxels"],
                "current_raw_2221_voxels": row["raw_2221_voxels"],
                "raw_2221_voxels_removed_vs_pathology_direct": removed,
                "raw_2221_voxels_added_vs_pathology_direct": added,
                "raw_2221_voxels_overlap": overlap,
                "previous_raw_2221_components": previous_row["raw_2221_components"],
                "current_raw_2221_components": row["raw_2221_components"],
                "previous_largest_raw_2221_fraction": previous_row["largest_raw_2221_fraction"],
                "current_largest_raw_2221_fraction": row["largest_raw_2221_fraction"],
                "previous_raw_2221_bbox": previous_row["raw_2221_bbox"],
                "current_raw_2221_bbox": row["raw_2221_bbox"],
                "previous_raw_2221_volume_mm3": previous_row["raw_2221_volume_mm3"],
                "current_raw_2221_volume_mm3": row["raw_2221_volume_mm3"],
                "previous_raw_2221_bbox_gap_mm": previous_row["raw_2221_bbox_gap_mm"],
                "current_raw_2221_bbox_gap_mm": row["raw_2221_bbox_gap_mm"],
                "previous_raw_2221_center_distance_mm": previous_row["raw_2221_center_distance_mm"],
                "current_raw_2221_center_distance_mm": row["raw_2221_center_distance_mm"],
            }
        )

    staged_cine_cases = sorted(prediction_map_from_submission_branch(staging_tree / "CineMyoPS"))
    if staged_cine_cases != expected_cine_cases:
        fail_reasons.append(f"Staged Cine case list mismatch: expected={expected_cine_cases}, found={staged_cine_cases}")

    fieldnames = list(raw_rows[0].keys())
    write_csv(out_root / "raw_label_qc.csv", raw_rows, fieldnames)
    write_csv(out_root / "case_level_topology_lcc_qc.csv", topology_rows, list(topology_rows[0].keys()))
    write_csv(out_root / "diff_from_pathology_direct.csv", diff_rows, list(diff_rows[0].keys()))

    qa_pass = not fail_reasons
    write_summary(
        out_root=out_root,
        run_id=args.run_id,
        qa_pass=qa_pass,
        fail_reasons=fail_reasons,
        staging_tree=staging_tree,
        myops_rows=myops_rows,
        raw_rows=raw_rows,
        diff_rows=diff_rows,
        previous_manifest=previous_manifest,
    )

    print(json.dumps({"qa_pass": qa_pass, "run_id": args.run_id, "out_root": str(out_root), "staging_tree": str(staging_tree)}, indent=2))
    return 0 if qa_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
