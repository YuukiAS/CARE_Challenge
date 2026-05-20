#!/usr/bin/env python3
"""Round8 export-only prior reliability gates for U-MyoPS fold0.

The prediction variants in this script are intentionally conservative: they use
only model predictions, Stage1 prior masks, and modality metadata. Ground truth
is used only for offline taxonomy/evaluation artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_img(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint16, copy=False)
    return img, arr


def write_like(arr: np.ndarray, ref: sitk.Image, path: Path) -> None:
    out = sitk.GetImageFromArray(arr.astype(np.uint16, copy=False))
    out.CopyInformation(ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out, str(path))


def mask_for(arr: np.ndarray, cls: int) -> np.ndarray:
    if cls == 4:
        return (arr == 4) | (arr == 1220)
    if cls == 5:
        return (arr == 5) | (arr == 2221)
    return arr == cls


def dice_masks(pred: np.ndarray, gt: np.ndarray) -> float:
    ps = int(pred.sum())
    gs = int(gt.sum())
    if ps == 0 and gs == 0:
        return 1.0
    denom = ps + gs
    if denom == 0:
        return 0.0
    return float(2.0 * np.logical_and(pred, gt).sum() / denom)


def subject_meta_by_case(staged_root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for meta_path in staged_root.glob("*/subject_meta.json"):
        meta = read_json(meta_path)
        out[meta["case_id"]] = meta
    return out


def is_complete(mods: dict) -> bool:
    return bool(mods.get("c0") and mods.get("t2") and mods.get("de"))


def stage1_prior_by_case(stage1_gen_dir: Path, prior_tag: str) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for subject_dir in sorted(p for p in stage1_gen_dir.iterdir() if p.is_dir()):
        meta_path = subject_dir / "subject_meta.json"
        case_id = None
        if meta_path.is_file():
            case_id = read_json(meta_path)["case_id"]
        else:
            parts = subject_dir.name.split("_")
            case_id = parts[-1] if parts else None
        if not case_id:
            continue
        matches = sorted(subject_dir.glob(f"*_{prior_tag}_{case_id}.nii.gz"))
        if matches:
            out[case_id] = matches[0]
    return out


def label_components_6(mask: np.ndarray) -> tuple[np.ndarray, list[int]]:
    labels = np.zeros(mask.shape, dtype=np.int32)
    sizes: list[int] = []
    current = 0
    shape = mask.shape
    for start in zip(*np.nonzero(mask)):
        if labels[start] != 0:
            continue
        current += 1
        q: deque[tuple[int, int, int]] = deque([tuple(int(x) for x in start)])
        labels[start] = current
        size = 0
        while q:
            z, y, x = q.popleft()
            size += 1
            for dz, dy, dx in ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)):
                nz, ny, nx = z + dz, y + dy, x + dx
                if (
                    0 <= nz < shape[0]
                    and 0 <= ny < shape[1]
                    and 0 <= nx < shape[2]
                    and mask[nz, ny, nx]
                    and labels[nz, ny, nx] == 0
                ):
                    labels[nz, ny, nx] = current
                    q.append((nz, ny, nx))
        sizes.append(size)
    return labels, sizes


def dilate_xy(mask: np.ndarray, radius_xy: int, radius_z: int = 0) -> np.ndarray:
    if radius_xy <= 0 and radius_z <= 0:
        return mask.astype(bool, copy=False)
    zz, yy, xx = np.ogrid[-radius_z : radius_z + 1, -radius_xy : radius_xy + 1, -radius_xy : radius_xy + 1]
    st = (zz / max(radius_z, 1)) ** 2 + (yy / max(radius_xy, 1)) ** 2 + (xx / max(radius_xy, 1)) ** 2 <= 1
    if radius_z == 0:
        st = st[0:1]
    return ndi.binary_dilation(mask.astype(bool, copy=False), structure=st)


def replace_scar(base: np.ndarray, scar_source: np.ndarray) -> np.ndarray:
    out = base.copy()
    out[mask_for(out, 5)] = 0
    out[mask_for(scar_source, 5)] = 5
    return out


def keep_largest_until(mask: np.ndarray, cap_voxels: int) -> np.ndarray:
    labels, sizes = label_components_6(mask)
    order = sorted(enumerate(sizes, start=1), key=lambda x: x[1], reverse=True)
    keep = np.zeros_like(mask, dtype=bool)
    remaining = int(cap_voxels)
    for idx, size in order:
        if remaining <= 0:
            break
        comp = labels == idx
        if size <= remaining or not keep.any():
            keep |= comp
            remaining -= size
    return keep


def remove_small_far_components(arr: np.ndarray, support: np.ndarray, min_voxels: int) -> np.ndarray:
    out = arr.copy()
    scar = mask_for(out, 5)
    labels, sizes = label_components_6(scar)
    remove = np.zeros_like(scar, dtype=bool)
    for idx, size in enumerate(sizes, start=1):
        comp = labels == idx
        if size < min_voxels and not np.logical_and(comp, support).any():
            remove |= comp
    out[remove] = 0
    return out


def cap_scar(arr: np.ndarray, cap_voxels: int) -> np.ndarray:
    out = arr.copy()
    scar = mask_for(out, 5)
    if int(scar.sum()) <= cap_voxels:
        return out
    keep = keep_largest_until(scar, cap_voxels)
    out[scar & ~keep] = 0
    return out


def classify_failure(row: dict, qc: dict | None) -> str:
    gt = int(row["gt_class_5_voxels"])
    pred = int(row["pred_class_5_voxels"])
    if gt == 0 and pred > 0:
        return "gt_empty_pred_nonempty"
    if gt > 0 and pred == 0:
        return "missed_scar"
    ratio = pred / gt if gt else math.inf
    overlap = int(qc["prior_gt_pathology_overlap_voxels"]) if qc else -1
    if overlap >= 0 and overlap < 50:
        return "very_low_prior_pathology_overlap"
    if ratio > 2.0:
        return "over_segmentation"
    if ratio < 0.5:
        return "under_segmentation"
    return "localization_or_mixed"


def write_taxonomy(rows: list[dict], out_csv: Path, out_md: Path) -> None:
    fields = list(rows[0].keys())
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# U-MyoPS round8 prior-gate failure taxonomy",
        "",
        "| case | scar_dice | pred_scar | gt_scar | pred/gt | prior_overlap | pred_prior_overlap | modality_group | category |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for r in sorted(rows, key=lambda x: float(x["scar_dice"])):
        lines.append(
            f"| {r['case']} | {float(r['scar_dice']):.4f} | {r['pred_scar_voxels']} | {r['gt_scar_voxels']} | "
            f"{float(r['pred_gt_volume_ratio']):.3f} | {r['prior_gt_pathology_overlap_voxels']} | "
            f"{r['pred_prior_overlap_voxels']} | {r['modality_group']} | {r['failure_category']} |"
        )
    lines += ["", "## Category counts", "", "| category | n | mean scar Dice |", "| --- | ---: | ---: |"]
    cats = sorted({r["failure_category"] for r in rows})
    for cat in cats:
        subset = [r for r in rows if r["failure_category"] == cat]
        lines.append(f"| {cat} | {len(subset)} | {np.mean([float(r['scar_dice']) for r in subset]):.4f} |")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_eval(root: Path, pred_dir: Path, out_dir: Path, fold: int) -> None:
    py = root / "envs" / "env_CARE" / "bin" / "python"
    if not py.is_file():
        py = Path("python")
    cmd = [
        str(py),
        str(root / "scripts/evaluation/evaluate_predictions.py"),
        "--pred-dir",
        str(pred_dir),
        "--gt-dir",
        str(root / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"),
        "--fold-json",
        str(root / "data/benchmarks/protocol/splits_MyoPS.json"),
        "--fold",
        str(fold),
        "--foreground-classes",
        "4,5",
        "--hd",
        "--hd95",
        "--output-dir",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True)


def grouped_report(root: Path, metrics_dir: Path, per_case_counts: Path, out_md: Path) -> None:
    summary = read_json(metrics_dir / "evaluation_summary.json")
    counts = list(csv.DictReader(per_case_counts.open(encoding="utf-8")))
    per_case = summary["per_case"]
    per_hd = summary.get("per_case_hd", {})
    per_hd95 = summary.get("per_case_hd95", {})

    def mean_for(rows: list[dict], key: str) -> float:
        vals = [per_case[r["case"]][key] for r in rows if per_case[r["case"]][key] is not None]
        return float(np.mean(vals)) if vals else float("nan")

    def mean_hd(rows: list[dict], hd_map: dict, key: str) -> float:
        vals = [hd_map.get(r["case"], {}).get(key) for r in rows]
        vals = [v for v in vals if v is not None]
        return float(np.mean(vals)) if vals else float("nan")

    groups = {
        "all_cases": counts,
        "scar_gt_positive_only": [r for r in counts if r["gt_class_5_positive"] == "True"],
        "complete/T2-present": [r for r in counts if r["complete_modalities"] == "True"],
        "missing-modality": [r for r in counts if r["complete_modalities"] != "True"],
    }
    lines = [
        f"# {metrics_dir.parent.name} grouped diagnostics",
        "",
        "| group | n | myops_edema | myops_scar | scar_HD | scar_HD95 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, rows in groups.items():
        lines.append(
            f"| {name} | {len(rows)} | {mean_for(rows, 'class_4'):.4f} | {mean_for(rows, 'class_5'):.4f} | "
            f"{mean_hd(rows, per_hd, 'class_5'):.4f} | {mean_hd(rows, per_hd95, 'class_5'):.4f} |"
        )
    lowest = sorted(counts, key=lambda r: per_case[r["case"]]["class_5"])[:10]
    lines += [
        "",
        "## Lowest Scar Cases",
        "",
        "| case | scar_dice | scar_HD | scar_HD95 | pred_scar | gt_scar | modalities |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in lowest:
        cid = r["case"]
        lines.append(
            f"| {cid} | {per_case[cid]['class_5']:.4f} | {per_hd.get(cid, {}).get('class_5')} | "
            f"{per_hd95.get(cid, {}).get('class_5')} | {r['pred_class_5_voxels']} | "
            f"{r['gt_class_5_voxels']} | {r['modalities_present']} |"
        )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_per_case_counts(root: Path, pred_dir: Path, metrics_dir: Path, fold: int, meta: dict[str, dict]) -> Path:
    summary = read_json(metrics_dir / "evaluation_summary.json")
    case_ids = sorted(read_json(root / "data/benchmarks/protocol/splits_MyoPS.json")["folds"][fold]["val"])
    gt_dir = root / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
    rows: list[dict] = []
    for cid in case_ids:
        _, pred = read_img(pred_dir / f"{cid}.nii.gz")
        _, gt = read_img(gt_dir / f"{cid}.nii.gz")
        mods = meta[cid]["modalities_present"]
        p4, g4 = mask_for(pred, 4), mask_for(gt, 4)
        p5, g5 = mask_for(pred, 5), mask_for(gt, 5)
        rows.append(
            {
                "case": cid,
                "center": meta[cid].get("center", cid[4] if len(cid) > 4 else ""),
                "modalities_present": json.dumps(mods, sort_keys=True),
                "t2_present": bool(mods.get("t2")),
                "complete_modalities": is_complete(mods),
                "geometry_match": True,
                "dice_class_4": summary["per_case"][cid]["class_4"],
                "pred_class_4_voxels": int(p4.sum()),
                "gt_class_4_voxels": int(g4.sum()),
                "gt_class_4_positive": bool(g4.any()),
                "empty_gt_class_4_counted_1": bool(not g4.any() and not p4.any()),
                "dice_class_5": summary["per_case"][cid]["class_5"],
                "pred_class_5_voxels": int(p5.sum()),
                "gt_class_5_voxels": int(g5.sum()),
                "gt_class_5_positive": bool(g5.any()),
                "empty_gt_class_5_counted_1": bool(not g5.any() and not p5.any()),
            }
        )
    out = metrics_dir / "per_case_counts.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out


def main() -> None:
    root = repo_root()
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--round7-dir", type=Path, default=root / "results/predictions/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0")
    ap.add_argument("--round5-dir", type=Path, default=root / "results/predictions/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0")
    ap.add_argument("--stage1-gen-dir", type=Path, default=root / "third_party/U-MyoPS_myops/outputs/asn_myo_tps_tps_ZS_unaligned_1.0_fold0/gen_res")
    ap.add_argument("--prior-tag", type=str, default="img_de_branch_lab")
    ap.add_argument("--diagnostics-root", type=Path, default=root / "results/diagnostics/U-MyoPS_round8_prior_gate")
    ap.add_argument("--pred-root", type=Path, default=root / "results/predictions")
    ap.add_argument("--metrics-root", type=Path, default=root / "results/metrics/unified")
    args = ap.parse_args()

    case_ids = sorted(read_json(root / "data/benchmarks/protocol/splits_MyoPS.json")["folds"][args.fold]["val"])
    gt_dir = root / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
    round7_metrics = root / "results/metrics/unified/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0"
    base_counts = list(csv.DictReader((round7_metrics / "per_case_counts.csv").open(encoding="utf-8")))
    qc_rows = {r["case"]: r for r in csv.DictReader((round7_metrics / "stage1_prior_qc.csv").open(encoding="utf-8"))}
    meta = subject_meta_by_case(root / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data")
    priors = stage1_prior_by_case(args.stage1_gen_dir, args.prior_tag)

    loaded: dict[str, dict[str, Any]] = {}
    taxonomy: list[dict] = []
    pred_prior_ratios = []
    scar_volumes = []
    for row in base_counts:
        cid = row["case"]
        ref, gt = read_img(gt_dir / f"{cid}.nii.gz")
        _, r7 = read_img(args.round7_dir / f"{cid}.nii.gz")
        _, r5 = read_img(args.round5_dir / f"{cid}.nii.gz")
        _, prior_arr = read_img(priors[cid])
        prior = prior_arr != 0
        support = dilate_xy(prior, radius_xy=8)
        pred_scar = mask_for(r7, 5)
        pred_prior_overlap = int(np.logical_and(pred_scar, support).sum())
        pred_vox = int(pred_scar.sum())
        prior_vox = int(prior.sum())
        ratio = pred_vox / max(1, prior_vox)
        pred_prior_ratios.append(ratio)
        scar_volumes.append(pred_vox)
        q = qc_rows.get(cid)
        gt_vox = int(row["gt_class_5_voxels"])
        pred_gt_ratio = pred_vox / gt_vox if gt_vox else math.inf
        taxonomy.append(
            {
                "case": cid,
                "scar_dice": row["dice_class_5"],
                "pred_scar_voxels": pred_vox,
                "gt_scar_voxels": gt_vox,
                "pred_gt_volume_ratio": pred_gt_ratio,
                "pred_prior_overlap_voxels": pred_prior_overlap,
                "pred_prior_overlap_fraction": pred_prior_overlap / max(1, pred_vox),
                "prior_nonzero_voxels": prior_vox,
                "prior_gt_pathology_overlap_voxels": int(q["prior_gt_pathology_overlap_voxels"]) if q else -1,
                "prior_gt_support_dice": float(q["prior_gt_support_dice"]) if q else float("nan"),
                "modality_group": "complete" if row["complete_modalities"] == "True" else "missing_modality",
                "failure_category": classify_failure(row, q),
            }
        )
        loaded[cid] = {"ref": ref, "gt": gt, "r7": r7, "r5": r5, "prior": prior, "support": support, "meta": meta[cid]}

    write_taxonomy(
        taxonomy,
        args.diagnostics_root / "case_failure_taxonomy.csv",
        args.diagnostics_root / "case_failure_taxonomy.md",
    )

    ratio_cap = float(np.quantile(pred_prior_ratios, 0.85))
    abs_cap = int(np.quantile(scar_volumes, 0.85))
    variants = {
        "U-MyoPS_round8_drop_empty_gt_like_false_positive_proxy": "Delete very small scars with weak prior support and multiple proxy signs of false positive.",
        "U-MyoPS_round8_tiny_c0_lge_no_t2_suppression": "Diagnostic-only: suppress tiny scar predictions in C0+LGE/no-T2 cases.",
        "U-MyoPS_round8_prior_reliable_keep_lge_fallback": "Fallback to round5 LGE-only scar when the Stage1 prior appears unreliable by prediction/prior volume.",
        "U-MyoPS_round8_component_hd_guard": "Remove only small scar components outside dilated Stage1 support.",
        "U-MyoPS_round8_volume_ratio_guard": "Cap scar volume using protocol prediction/prior distribution, keeping largest components.",
    }
    variant_actions: dict[str, list[dict]] = {k: [] for k in variants}
    for tag in variants:
        out_dir = args.pred_root / tag / f"fold_{args.fold}"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for cid in case_ids:
            item = loaded[cid]
            pred = item["r7"].copy()
            scar = mask_for(pred, 5)
            pred_vox = int(scar.sum())
            prior_vox = int(item["prior"].sum())
            support_overlap = int(np.logical_and(scar, item["support"]).sum())
            support_frac = support_overlap / max(1, pred_vox)
            action = "keep"
            if tag.endswith("false_positive_proxy"):
                labels, sizes = label_components_6(scar)
                n_components = len(sizes)
                largest = max(sizes) if sizes else 0
                if pred_vox <= 300 and (support_frac < 0.25 or n_components > 2 or largest < 150):
                    pred[scar] = 0
                    action = f"drop_small_weak_support(pred={pred_vox}, support_frac={support_frac:.3f})"
            elif tag.endswith("tiny_c0_lge_no_t2_suppression"):
                mods = item["meta"]["modalities_present"]
                if pred_vox <= 250 and mods.get("c0") and mods.get("de") and not mods.get("t2"):
                    pred[scar] = 0
                    action = f"drop_tiny_c0_lge_no_t2(pred={pred_vox})"
            elif tag.endswith("lge_fallback"):
                pred_prior_ratio = pred_vox / max(1, prior_vox)
                low_reliability = prior_vox < 750 or support_frac < 0.20 or pred_prior_ratio > ratio_cap
                if low_reliability:
                    pred = replace_scar(pred, item["r5"])
                    action = f"round5_scar_fallback(ratio={pred_prior_ratio:.3f}, support_frac={support_frac:.3f})"
            elif tag.endswith("component_hd_guard"):
                pred = remove_small_far_components(pred, item["support"], min_voxels=120)
                removed = pred_vox - int(mask_for(pred, 5).sum())
                if removed:
                    action = f"removed_far_small_components={removed}"
            elif tag.endswith("volume_ratio_guard"):
                cap = max(400, min(abs_cap, int(ratio_cap * max(1, prior_vox))))
                if pred_vox > cap:
                    pred = cap_scar(pred, cap)
                    action = f"cap_{pred_vox}_to_{int(mask_for(pred, 5).sum())}(cap={cap})"
            write_like(pred, item["ref"], out_dir / f"{cid}.nii.gz")
            variant_actions[tag].append({"case": cid, "action": action})

    for tag, description in variants.items():
        pred_dir = args.pred_root / tag / f"fold_{args.fold}"
        metrics_dir = args.metrics_root / tag / f"fold_{args.fold}"
        if metrics_dir.exists():
            shutil.rmtree(metrics_dir)
        run_eval(root, pred_dir, metrics_dir, args.fold)
        counts_path = write_per_case_counts(root, pred_dir, metrics_dir, args.fold, meta)
        grouped_report(root, metrics_dir, counts_path, metrics_dir / "grouped_diagnostics.md")
        with (args.diagnostics_root / f"{tag}_actions.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["case", "action"])
            writer.writeheader()
            writer.writerows(variant_actions[tag])

    manifest = {
        "round": "U-MyoPS round8 prior reliability gate",
        "inputs": {
            "round7_dir": str(args.round7_dir),
            "round5_fallback_dir": str(args.round5_dir),
            "stage1_gen_dir": str(args.stage1_gen_dir),
            "prior_tag": args.prior_tag,
            "latest_leaderboard_scar": str(root / "results/leaderboard/care2026_myocardium_myops_scar_latest.csv"),
        },
        "thresholds": {
            "pred_prior_ratio_cap_q85": ratio_cap,
            "scar_volume_abs_cap_q85": abs_cap,
        },
        "variants": variants,
        "notes": [
            "Prediction edits do not use GT labels.",
            "GT is used for taxonomy and offline evaluation only.",
            "round5 fallback is pure U-MyoPS LGE-only/no-prior, not nnU-Net.",
        ],
    }
    args.diagnostics_root.mkdir(parents=True, exist_ok=True)
    (args.diagnostics_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote diagnostics to {args.diagnostics_root}")
    for tag in variants:
        print(f"Wrote/evaluated {tag}")


if __name__ == "__main__":
    main()
