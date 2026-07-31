#!/usr/bin/env python3
"""Build MyoWall-IF geometry gate evidence.

The formal path consumes frozen stock nnU-Net anatomy probabilities. The
``--smoke-from-label`` mode remains available for contract/debug smoke, but is
marked zero-credit and cannot satisfy final validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.myowall_if.geometry import FrozenStockGeometryCacheBuilder  # noqa: E402
from src.care_myocardium.models.myowall_if.geometry import WallCoordinateTransform, WallInverseTransform  # noqa: E402
from src.care_myocardium.models.myowall_if.stock_adapter import StockNNUNetFeatureAdapter  # noqa: E402
from src.care_myocardium.models.myowall_if.evaluator import MyoWallPilotEvaluator  # noqa: E402

TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_seg(case_id: str) -> torch.Tensor:
    import blosc2
    import numpy as np

    arr = np.asarray(blosc2.open(str(REPO_ROOT / f"data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres/{case_id}_seg.b2nd"), mode="r")[:]).squeeze()
    return torch.from_numpy(arr).long()


def load_patch(case_id: str, patch_size: list[int]) -> torch.Tensor:
    import blosc2

    arr = np.asarray(blosc2.open(str(REPO_ROOT / f"data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres/{case_id}.b2nd"), mode="r")[:])
    x = torch.from_numpy(arr).float().unsqueeze(0)
    z, y, w = x.shape[-3:]
    target_z, target_y, target_x = patch_size
    crop = x[..., : min(z, target_z), : min(y, target_y), : min(w, target_x)]
    pad = (0, max(0, target_x - crop.shape[-1]), 0, max(0, target_y - crop.shape[-2]), 0, max(0, target_z - crop.shape[-3]))
    return F.pad(crop, pad)


def roundtrip_metrics(p_wall: torch.Tensor, geom, *, spacing_zyx: tuple[float, float, float]) -> dict[str, float | None]:
    evaluator = MyoWallPilotEvaluator()
    mask = (p_wall >= 0.30).float()
    transform = WallCoordinateTransform()
    inverse = WallInverseTransform()
    wall_lattice = transform(mask, geom, mode="bilinear")
    recon = inverse(wall_lattice, geom, output_shape=tuple(int(v) for v in mask.shape[-3:]), outside_value=0.0)
    pred_np = (recon[0, 0].detach().cpu().numpy() >= 0.50).astype(np.uint8)
    ref_np = (mask[0, 0].detach().cpu().numpy() >= 0.50).astype(np.uint8)
    den = int(pred_np.sum() + ref_np.sum())
    dice = 1.0 if den == 0 else float(2 * np.logical_and(pred_np, ref_np).sum() / den)
    hd95 = evaluator.hd95(pred_np, ref_np, 1, spacing_zyx)
    return {"wall_roundtrip_dice": dice, "wall_roundtrip_hd95_mm": hd95}


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-list", choices=("pilot_inner", "pilot_train", "all_pilot"), default="pilot_inner")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--smoke-from-label", action="store_true")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    if args.case_list == "pilot_train":
        cases = (RESULT_ROOT / "pilot_train_cases.txt").read_text(encoding="utf-8").splitlines()
    elif args.case_list == "all_pilot":
        cases = (RESULT_ROOT / "pilot_train_cases.txt").read_text(encoding="utf-8").splitlines()
        cases.extend((RESULT_ROOT / "pilot_inner_cases.txt").read_text(encoding="utf-8").splitlines())
    else:
        cases = (RESULT_ROOT / "pilot_inner_cases.txt").read_text(encoding="utf-8").splitlines()
    cases = cases[: args.max_cases] if args.max_cases else cases
    rows = []
    builder = FrozenStockGeometryCacheBuilder()
    adapter = None
    if not args.smoke_from_label:
        torch.set_num_threads(4)
        adapter = StockNNUNetFeatureAdapter(fold=1, map_location=args.device)
        adapter.to(args.device)
    for cid in cases:
        if args.smoke_from_label:
            seg = load_seg(cid)
            p_lv = (seg == 2).float().view(1, 1, *seg.shape)
            p_wall = ((seg == 1) | (seg == 4) | (seg == 5)).float().view(1, 1, *seg.shape)
        else:
            assert adapter is not None
            sample = load_patch(cid, adapter.patch_size).to(args.device)
            with torch.no_grad():
                out = adapter(sample)
            p_lv = out["p_lv"].detach().cpu()
            p_wall = out["p_wall"].detach().cpu()
        spacing = (1.0, 1.0, 1.0)
        geom = builder.build_from_probabilities(p_lv, p_wall, spacing_zyx=spacing)
        metric = builder.metrics(geom)
        rt = roundtrip_metrics(p_wall.cpu(), geom, spacing_zyx=spacing)
        rows.append(
            {
                "case_id": cid,
                "raw_valid_angle_fraction": metric["raw_valid_angle_fraction"],
                "valid_angle_fraction": metric["valid_angle_fraction"],
                "valid_slice_fraction": metric["valid_slice_fraction"],
                "active_slice_count": metric["active_slice_count"],
                "geometry_valid": metric["geometry_valid"],
                "wall_roundtrip_dice": "" if rt["wall_roundtrip_dice"] is None else rt["wall_roundtrip_dice"],
                "wall_roundtrip_hd95_mm": "" if rt["wall_roundtrip_hd95_mm"] is None else rt["wall_roundtrip_hd95_mm"],
                "geometry_source": "label_smoke_zero_credit" if args.smoke_from_label else "frozen_stock_fold1_probabilities",
            }
        )
    write_csv(RESULT_ROOT / "geometry_casewise_metrics.csv", rows)
    cache_status = "ZERO_CREDIT_SMOKE" if args.smoke_from_label else "FORMAL_GEOMETRY_BUILT"
    write_csv(RESULT_ROOT / "geometry_cache_manifest.csv", [{"case_id": row["case_id"], "cache_status": cache_status, "geometry_source": row["geometry_source"]} for row in rows])
    dice_values = [float(r["wall_roundtrip_dice"]) for r in rows if r["wall_roundtrip_dice"] != ""]
    hd_values = [float(r["wall_roundtrip_hd95_mm"]) for r in rows if r["wall_roundtrip_hd95_mm"] != ""]
    valid_rate = sum(float(r["valid_angle_fraction"]) >= 0.95 for r in rows) / max(len(rows), 1)
    median_dice = percentile(dice_values, 50)
    p05_dice = percentile(dice_values, 5)
    median_hd95 = percentile(hd_values, 50)
    formal_pass = (
        (not args.smoke_from_label)
        and len(rows) == len(cases)
        and valid_rate >= 0.95
        and median_dice is not None
        and median_dice >= 0.96
        and p05_dice is not None
        and p05_dice >= 0.90
        and median_hd95 is not None
        and median_hd95 <= 2.0
    )
    report = {
        "status": "ZERO_CREDIT_SMOKE" if args.smoke_from_label else ("PASS" if formal_pass else "FAIL"),
        "formal_geometry_gate": "NOT_SATISFIED_WITH_LABEL_SMOKE" if args.smoke_from_label else ("PASS" if formal_pass else "FAIL"),
        "case_list": args.case_list,
        "case_count": len(rows),
        "case_geometry_valid_rate": valid_rate,
        "median_wall_roundtrip_dice": median_dice,
        "fifth_percentile_wall_roundtrip_dice": p05_dice,
        "median_roundtrip_hd95_mm": median_hd95,
        "geometry_source": "label_smoke_zero_credit" if args.smoke_from_label else "frozen_stock_fold1_probabilities",
        "stock_checkpoint_path": None if adapter is None else str(adapter.checkpoint_path.relative_to(REPO_ROOT)),
        "lv_probability_threshold": builder.lv_threshold,
        "wall_probability_threshold": builder.wall_threshold,
        "valid_angle_rate_denominator": "active_predicted_wall_lv_slices",
    }
    write_json(RESULT_ROOT / "geometry_gate_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
