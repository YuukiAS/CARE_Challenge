#!/usr/bin/env python3
"""Build case montages for the V2 forensic PDF."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
OOF_REL = Path("results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/mosaic_oof_prediction_manifest.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
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
            writer.writerow({k: row.get(k, "") for k in fieldnames})


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
    lo, hi = np.percentile(vals, [1, 99])
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((img - lo) / (hi - lo), 0, 1)


def overlay_mask(ax: Any, mask: np.ndarray, color: str, alpha: float) -> None:
    rgba = np.zeros(mask.shape + (4,), dtype=np.float32)
    colors = {
        "red": (1.0, 0.1, 0.1),
        "cyan": (0.0, 0.8, 1.0),
        "yellow": (1.0, 0.9, 0.0),
        "green": (0.1, 0.9, 0.2),
    }
    rgba[..., :3] = colors[color]
    rgba[..., 3] = mask.astype(np.float32) * alpha
    ax.imshow(rgba, interpolation="nearest")


def choose_slice(gt: np.ndarray, nnunet: np.ndarray, mosaic: np.ndarray) -> tuple[int, str]:
    lesion = np.isin(gt, [4, 5])
    fn = lesion & ~np.isin(nnunet, [4, 5])
    fp = np.isin(nnunet, [4, 5]) & ~lesion
    disagreement = np.isin(nnunet, [4, 5]) ^ np.isin(mosaic, [4, 5])
    scores = []
    for z in range(gt.shape[2]):
        scores.append(
            (
                int(lesion[:, :, z].sum()) + int(fn[:, :, z].sum()) + int(fp[:, :, z].sum()) + int(disagreement[:, :, z].sum()),
                z,
            )
        )
    best = max(scores)[1]
    return best, "max_lesion_fn_fp_disagreement"


def plot_case(root: Path, out_dir: Path, row: dict[str, str]) -> dict[str, Any]:
    case_id = row["case_id"]
    lge_path = root / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr" / f"{case_id}_0000.nii.gz"
    gt_path = root / row["gt"]
    nn_path = root / row["nnunet_prediction"]
    mo_path = root / row["mosaic_prediction_official"]
    img = np.asanyarray(nib.load(str(lge_path)).dataobj).astype(np.float32)
    gt = load_label(gt_path)
    nn = load_label(nn_path)
    mo = load_label(mo_path)
    z, reason = choose_slice(gt, nn, mo)
    base = normalize_slice(img[:, :, z])
    panels = [
        ("GT", gt[:, :, z]),
        ("nnU-Net", nn[:, :, z]),
        ("MoSAIC clean", mo[:, :, z]),
        ("Disagreement", (np.isin(nn[:, :, z], [4, 5]) ^ np.isin(mo[:, :, z], [4, 5])).astype(np.int16)),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(10.5, 2.9), dpi=150)
    for ax, (title, lab) in zip(axes, panels):
        ax.imshow(base.T, cmap="gray", origin="lower")
        if title == "Disagreement":
            overlay_mask(ax, lab.T > 0, "yellow", 0.55)
        else:
            overlay_mask(ax, (lab.T == 5), "red", 0.50)
            overlay_mask(ax, (lab.T == 4), "cyan", 0.45)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    fig.suptitle(f"{case_id} | {row['center']} | {row['modality_availability']} | z={z}", fontsize=10)
    fig.tight_layout()
    out_path = out_dir / f"{case_id}_montage.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return {
        "case_id": case_id,
        "center": row["center"],
        "modality_availability": row["modality_availability"],
        "slice_index": z,
        "slice_reason": reason,
        "montage_path": str(out_path.relative_to(root)),
        "visual_review_status": "CODEX_VISUAL_REVIEW_PENDING",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--count", type=int, default=20)
    args = ap.parse_args()
    root = args.root.resolve()
    result_root = root / RESULT_REL
    manifest_rows = read_csv(root / OOF_REL)
    oracle_rows = read_csv(result_root / "case_oracle_summary.csv")
    by_case_score: dict[str, float] = {}
    for row in oracle_rows:
        score = 0.0
        for key in (
            "unique_recovery_mosaic_over_nnunet_fraction",
            "unique_recovery_nnunet_over_mosaic_fraction",
            "voxel_tp_oracle_dice",
        ):
            try:
                score += float(row.get(key, 0) or 0)
            except ValueError:
                pass
        by_case_score[row["case_id"]] = max(by_case_score.get(row["case_id"], 0.0), score)
    selected = sorted(manifest_rows, key=lambda r: by_case_score.get(r["case_id"], 0.0), reverse=True)[: args.count]
    out_dir = result_root / "case_montages"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [plot_case(root, out_dir, row) for row in selected]
    write_csv(result_root / "case_montage_manifest.csv", rows)

    images = [plt.imread(str(root / r["montage_path"])) for r in rows]
    fig, axes = plt.subplots(5, 4, figsize=(16, 15), dpi=120)
    for ax, image, row in zip(axes.ravel(), images, rows):
        ax.imshow(image)
        ax.set_title(row["case_id"], fontsize=9)
        ax.axis("off")
    fig.tight_layout()
    sheet = result_root / "case_montages" / "contact_sheet_20_cases.png"
    fig.savefig(sheet, bbox_inches="tight")
    plt.close(fig)
    (result_root / "manual_visual_review_notes.md").write_text(
        "# Manual visual review notes\n\n"
        "Generated 20 case montages for Codex visual review. Red marks scar, cyan marks pure edema, yellow marks nnU-Net/MoSAIC disagreement. "
        "The `visual_review_status` values in `case_montage_manifest.csv` are updated after image inspection.\n",
        encoding="utf-8",
    )
    print(str(sheet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
