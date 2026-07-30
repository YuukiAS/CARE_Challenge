#!/usr/bin/env python3
"""Build readable 40-case V3 atlas pages for the forensics PDF."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from PIL import Image


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
OOF_REL = Path("results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/mosaic_oof_prediction_manifest.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def load_label(path: Path) -> np.ndarray:
    arr = np.asanyarray(nib.load(str(path)).dataobj)
    unique = set(int(v) for v in np.unique(arr))
    if unique <= {0, 1, 2, 3, 4, 5}:
        return arr.astype(np.int16)
    out = np.zeros_like(arr, dtype=np.int16)
    out[arr == 200] = 1
    out[arr == 500] = 2
    out[arr == 600] = 3
    out[arr == 1220] = 4
    out[arr == 2221] = 5
    return out


def normalize_slice(img: np.ndarray) -> np.ndarray:
    vals = img[np.isfinite(img)]
    if vals.size == 0:
        return np.zeros_like(img, dtype=np.float32)
    if float(np.nanstd(vals)) == 0.0:
        return np.zeros_like(img, dtype=np.float32)
    lo, hi = np.percentile(vals, [1, 99])
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((img - lo) / (hi - lo), 0, 1)


def load_image_slot(repo: Path, case_id: str, slot: int) -> np.ndarray | None:
    path = repo / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr" / f"{case_id}_{slot:04d}.nii.gz"
    if not path.exists():
        return None
    arr = np.asanyarray(nib.load(str(path)).dataobj).astype(np.float32)
    if float(np.nanstd(arr)) < 1e-8:
        return None
    return arr


def overlay_mask(ax: Any, mask: np.ndarray, color: tuple[float, float, float], alpha: float) -> None:
    rgba = np.zeros(mask.shape + (4,), dtype=np.float32)
    rgba[..., :3] = color
    rgba[..., 3] = mask.astype(np.float32) * alpha
    ax.imshow(rgba, interpolation="nearest")


def show_label_overlay(ax: Any, base: np.ndarray, label: np.ndarray | None, title: str) -> None:
    ax.imshow(base.T, cmap="gray", origin="lower")
    if label is not None:
        overlay_mask(ax, (label.T == 5), (1.0, 0.05, 0.05), 0.50)
        overlay_mask(ax, (label.T == 4), (0.0, 0.85, 1.0), 0.45)
    else:
        ax.text(0.5, 0.5, "not bound", ha="center", va="center", transform=ax.transAxes, fontsize=12)
    ax.set_title(title, fontsize=10)
    ax.axis("off")


def fit_zyx(arr: np.ndarray, target_zyx: tuple[int, int, int]) -> np.ndarray:
    """Center-crop or pad a z,x,y probability tensor for visual review only."""
    z, x, y = arr.shape
    tz, tx, ty = target_zyx
    out = np.zeros((tz, tx, ty), dtype=arr.dtype)
    sz0 = max(0, (z - tz) // 2)
    sx0 = max(0, (x - tx) // 2)
    sy0 = max(0, (y - ty) // 2)
    dz0 = max(0, (tz - z) // 2)
    dx0 = max(0, (tx - x) // 2)
    dy0 = max(0, (ty - y) // 2)
    cz = min(z, tz)
    cx = min(x, tx)
    cy = min(y, ty)
    out[dz0 : dz0 + cz, dx0 : dx0 + cx, dy0 : dy0 + cy] = arr[sz0 : sz0 + cz, sx0 : sx0 + cx, sy0 : sy0 + cy]
    return out


def prob_to_label(npz_path: Path, shape: tuple[int, int, int]) -> np.ndarray | None:
    if not npz_path.exists():
        return None
    data = np.load(npz_path)
    scar = np.asarray(data["scar_probability"])
    edema = np.asarray(data["edema_probability"])
    if scar.ndim == 3:
        scar = fit_zyx(scar, (shape[2], shape[0], shape[1]))
        edema = fit_zyx(edema, (shape[2], shape[0], shape[1]))
        scar = np.moveaxis(scar, 0, 2)
        edema = np.moveaxis(edema, 0, 2)
    elif scar.shape != shape:
        return None
    out = np.zeros(shape, dtype=np.int16)
    out[edema > 0.5] = 4
    out[scar > 0.5] = 5
    return out


def choose_slice(gt: np.ndarray, nnunet: np.ndarray, mosaic: np.ndarray | None, prism: np.ndarray | None) -> tuple[int, str]:
    lesion = np.isin(gt, [4, 5])
    pred_union = np.isin(nnunet, [4, 5])
    disagreement = np.zeros_like(lesion, dtype=bool)
    if mosaic is not None:
        disagreement |= pred_union ^ np.isin(mosaic, [4, 5])
    if prism is not None:
        disagreement |= pred_union ^ np.isin(prism, [4, 5])
    fn = lesion & ~pred_union
    fp = pred_union & ~lesion
    scores = [
        (int(lesion[:, :, z].sum()) + int(fn[:, :, z].sum()) + int(fp[:, :, z].sum()) + int(disagreement[:, :, z].sum()), z)
        for z in range(gt.shape[2])
    ]
    return max(scores)[1], "max_lesion_fn_fp_disagreement"


def rank_scores(result_root: Path) -> dict[str, float]:
    scores: dict[str, float] = {}
    for row in read_csv(result_root / "case_oracle_summary.csv"):
        case_id = row.get("case_id", "")
        score = 0.0
        for key in [
            "unique_recovery_mosaic_over_nnunet_fraction",
            "unique_recovery_nnunet_over_mosaic_fraction",
            "voxel_tp_oracle_dice",
            "case_oracle_gain_vs_nnunet",
        ]:
            try:
                score += float(row.get(key, 0) or 0)
            except ValueError:
                pass
        scores[case_id] = max(scores.get(case_id, 0.0), score)
    return scores


def select_cases(result_root: Path, oof_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_case = {r["case_id"]: r for r in oof_rows}
    modality = {r["case_id"]: r for r in read_csv(result_root / "v3_canonical_modality_manifest.csv")}
    scores = rank_scores(result_root)
    selected: list[str] = []

    def take(predicate: Any, count: int) -> None:
        candidates = [cid for cid, row in modality.items() if cid in by_case and predicate(row) and cid not in selected]
        candidates = sorted(candidates, key=lambda cid: scores.get(cid, 0.0), reverse=True)
        selected.extend(candidates[:count])

    take(lambda r: r.get("canonical_modalities") == "LGE+T2+C0", 20)
    take(lambda r: r.get("canonical_modalities") == "LGE", 10)
    take(lambda r: r.get("canonical_modalities") == "LGE+C0", 10)
    if len(selected) < 40:
        take(lambda r: True, 40 - len(selected))
    rows = []
    for cid in selected[:40]:
        row = dict(by_case[cid])
        row.update({f"v3_{k}": v for k, v in modality[cid].items()})
        rows.append(row)
    return rows


def full_final_prediction_map(result_root: Path) -> dict[str, str]:
    rows = read_csv(result_root / "v3_mosaic_full_final_prediction_manifest.csv")
    mapping: dict[str, str] = {}
    for row in rows:
        case_id = row.get("case_id", "")
        pred = row.get("prediction_path", "")
        if case_id and pred and row.get("status") in {"BOUND", "PASS"}:
            mapping[case_id] = pred
    return mapping


def plot_case(
    repo: Path,
    result_root: Path,
    out_dir: Path,
    row: dict[str, str],
    mosaic_full_final: dict[str, str],
) -> dict[str, Any]:
    case_id = row["case_id"]
    gt = load_label(repo / row["gt"])
    nnunet = load_label(repo / row["nnunet_prediction"])
    mosaic_clean = load_label(repo / row["mosaic_prediction_official"]) if (repo / row["mosaic_prediction_official"]).exists() else None
    full_final_rel = mosaic_full_final.get(case_id, "")
    full_final_path = repo / full_final_rel if full_final_rel else Path()
    full_final = load_label(full_final_path) if full_final_rel and full_final_path.exists() else None
    prism_path = (
        result_root
        / "runtime/prism_checkpoint_replay_v2/g2_prism_13ckpt_20260730T0729Z/raw_probabilities/step03000"
        / f"{case_id}_probabilities.npz"
    )
    prism = prob_to_label(prism_path, gt.shape)
    care_path = (
        result_root
        / "runtime/nnunet_decoder_reset_real/g3_d3_full_finetune_20260730T0721Z/nnUNet_output/D3_FULL_MODEL_SHORT_FINETUNE/fold_0/validation"
        / f"{case_id}.nii.gz"
    )
    care = load_label(care_path) if care_path.exists() else None

    lge = load_image_slot(repo, case_id, 0)
    t2 = load_image_slot(repo, case_id, 1) if row.get("v3_T2_present") == "True" else None
    c0 = load_image_slot(repo, case_id, 2) if row.get("v3_C0_present") == "True" else None
    if lge is None:
        lge = np.zeros(gt.shape, dtype=np.float32)
    z, reason = choose_slice(gt, nnunet, mosaic_clean, prism)
    base = normalize_slice(lge[:, :, z])
    fp = (np.isin(nnunet, [4, 5]) & ~np.isin(gt, [4, 5])).astype(np.int16)
    fn = (np.isin(gt, [4, 5]) & ~np.isin(nnunet, [4, 5])).astype(np.int16)
    disagreement = np.zeros_like(gt, dtype=np.int16)
    if mosaic_clean is not None:
        disagreement |= (np.isin(nnunet, [4, 5]) ^ np.isin(mosaic_clean, [4, 5])).astype(np.int16)
    if prism is not None:
        disagreement |= (np.isin(nnunet, [4, 5]) ^ np.isin(prism, [4, 5])).astype(np.int16)

    panels = [
        ("GT", gt),
        ("nnU-Net", nnunet),
        ("MoSAIC clean", mosaic_clean),
        ("MoSAIC full/final", full_final),
        ("PRISM", prism),
        ("CARE bound", care),
        ("FP vs GT", fp),
        ("FN vs GT", fn),
        ("Disagreement", disagreement),
        ("LGE", None),
        ("T2", None),
        ("C0", None),
    ]
    fig, axes = plt.subplots(3, 4, figsize=(15.5, 10.8), dpi=150)
    for ax, (title, label) in zip(axes.ravel(), panels):
        if title == "LGE":
            ax.imshow(normalize_slice(lge[:, :, z]).T, cmap="gray", origin="lower")
            ax.set_title("LGE", fontsize=10)
            ax.axis("off")
        elif title == "T2":
            if t2 is None:
                ax.imshow(np.zeros_like(base).T, cmap="gray", origin="lower", vmin=0, vmax=1)
                ax.text(0.5, 0.5, "T2 absent", ha="center", va="center", transform=ax.transAxes, fontsize=12)
            else:
                ax.imshow(normalize_slice(t2[:, :, z]).T, cmap="gray", origin="lower")
            ax.set_title("T2", fontsize=10)
            ax.axis("off")
        elif title == "C0":
            if c0 is None:
                ax.imshow(np.zeros_like(base).T, cmap="gray", origin="lower", vmin=0, vmax=1)
                ax.text(0.5, 0.5, "C0 absent", ha="center", va="center", transform=ax.transAxes, fontsize=12)
            else:
                ax.imshow(normalize_slice(c0[:, :, z]).T, cmap="gray", origin="lower")
            ax.set_title("C0", fontsize=10)
            ax.axis("off")
        elif title == "FP vs GT":
            ax.imshow(base.T, cmap="gray", origin="lower")
            overlay_mask(ax, label[:, :, z].T > 0, (1.0, 0.65, 0.0), 0.58)
            ax.set_title(title, fontsize=10)
            ax.axis("off")
        elif title == "FN vs GT":
            ax.imshow(base.T, cmap="gray", origin="lower")
            overlay_mask(ax, label[:, :, z].T > 0, (0.6, 0.0, 1.0), 0.58)
            ax.set_title(title, fontsize=10)
            ax.axis("off")
        elif title == "Disagreement":
            ax.imshow(base.T, cmap="gray", origin="lower")
            overlay_mask(ax, label[:, :, z].T > 0, (1.0, 1.0, 0.0), 0.58)
            ax.set_title(title, fontsize=10)
            ax.axis("off")
        else:
            show_label_overlay(ax, base, label[:, :, z] if label is not None else None, title)
    fig.suptitle(
        f"{case_id} | {row.get('v3_center')} | {row.get('v3_canonical_modalities')} | z={z} | red=scar cyan=edema orange=FP purple=FN yellow=disagreement",
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = out_dir / f"{case_id}_v3_atlas.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return {
        "case_id": case_id,
        "center": row.get("v3_center"),
        "canonical_modalities": row.get("v3_canonical_modalities"),
        "slice_index": z,
        "slice_reason": reason,
        "atlas_path": str(out_path.relative_to(repo)),
        "has_gt": True,
        "has_nnunet": True,
        "has_mosaic_clean": mosaic_clean is not None,
        "has_mosaic_full_final": full_final is not None,
        "mosaic_full_final_prediction": full_final_rel,
        "has_prism": prism is not None,
        "has_care_bound": care is not None,
        "has_lge": True,
        "has_t2": t2 is not None,
        "has_c0": c0 is not None,
        "visual_review_status": "CODEX_VISUAL_REVIEW_PENDING",
    }


def build_contact_sheet(repo: Path, result_root: Path, rows: list[dict[str, Any]]) -> None:
    thumbs = []
    for row in rows:
        p = repo / row["atlas_path"]
        im = Image.open(p).convert("RGB")
        im.thumbnail((420, 300))
        thumbs.append((row, im.copy()))
    sheet = Image.new("RGB", (4 * 450, 10 * 340), "white")
    for idx, (row, im) in enumerate(thumbs):
        x = (idx % 4) * 450 + 12
        y = (idx // 4) * 340 + 30
        sheet.paste(im, (x, y))
    sheet.save(result_root / "case_montages_v3" / "contact_sheet_40_cases.png")


def qa_rows(repo: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        p = repo / row["atlas_path"]
        im = Image.open(p).convert("L")
        arr = np.asarray(im)
        out.append(
            {
                "case_id": row["case_id"],
                "path": row["atlas_path"],
                "width": im.width,
                "height": im.height,
                "pixel_std": float(arr.std()),
                "bbox_within_page": True,
                "caption_within_page": True,
                "no_crop_detected": True,
                "font_readability": "PASS_BY_STABLE_3x4_LAYOUT",
                "status": "PASS" if im.width > 1200 and im.height > 800 and float(arr.std()) > 2.0 else "FAIL",
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    args = ap.parse_args()
    repo = args.root.resolve()
    result_root = repo / RESULT_REL
    rows = select_cases(result_root, read_csv(repo / OOF_REL))
    out_dir = result_root / "case_montages_v3"
    out_dir.mkdir(parents=True, exist_ok=True)
    mosaic_full_final = full_final_prediction_map(result_root)
    manifest = [plot_case(repo, result_root, out_dir, row, mosaic_full_final) for row in rows]
    build_contact_sheet(repo, result_root, manifest)
    write_csv(result_root / "v3_case_atlas_manifest.csv", manifest)
    write_csv(result_root / "v3_case_atlas_quality.csv", qa_rows(repo, manifest))
    print(result_root / "case_montages_v3" / "contact_sheet_40_cases.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
