#!/usr/bin/env python3
"""Prepare ignored MoSAIC runtime links for CARE inference.

This script does not train or upload. It creates ignored symlinks for the
upstream MoSAIC hard-coded checkpoint paths and can stage CARE MyoPS fold0 val
cases into MoSAIC validation-style input layout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))

from mosaic_fair_protocol import (  # noqa: E402
    DEFAULT_MOSAIC_ROOT,
    DEFAULT_RESULT_ROOT,
    MOSAIC_SOURCE_COMMIT,
    load_fold_val_cases,
    write_json,
)

SOURCE_ROOT = REPO_ROOT / "third_party/MoSAIC/source"
SPLIT_PATH = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
TRAIN_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_train"

WEIGHT_LINKS = {
    "myops/coarse.pt": "full_train/myops/fold-1/coarse/best.pt",
    "myops/coarse_edema.pt": "checkpoints/myopsf/myops_coarse_full/best.pt",
    "myops/fine_scar.pt": "full_train/myops/fold-1/fine/best_scar.pt",
    "myops/edema.pt": "checkpoints/myopsf/myops_edema_full/last.pt",
    "cinemyops/coarse.pt": "checkpoints/myopsf/cine_coarse_full_v2/best.pt",
    "cinemyops/fine_v1.pt": "checkpoints/myopsf/cine_scar_full/best_pathology.pt",
    "cinemyops/fine_v2.pt": "checkpoints/myopsf/cine_scar_full_v2/best_pathology.pt",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", type=Path, default=SOURCE_ROOT)
    ap.add_argument("--mosaic-root", type=Path, default=Path(os.environ.get("MOSAIC_ROOT", str(DEFAULT_MOSAIC_ROOT))))
    ap.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    ap.add_argument("--stage-fold0", action="store_true")
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="Replace existing symlinks created by this script.")
    return ap.parse_args()


def safe_symlink(target: Path, link: Path, *, force: bool = False) -> dict[str, Any]:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        current = Path(os.readlink(link))
        if current == target:
            return {"link": str(link), "target": str(target), "status": "EXISTS"}
        if force:
            link.unlink()
        else:
            return {"link": str(link), "target": str(target), "status": "CONFLICT", "current": str(current)}
    elif link.exists():
        return {"link": str(link), "target": str(target), "status": "CONFLICT_EXISTS_NON_SYMLINK"}
    link.symlink_to(target)
    return {"link": str(link), "target": str(target), "status": "CREATED"}


def prepare_weight_links(source_root: Path, mosaic_root: Path, *, force: bool) -> list[dict[str, Any]]:
    rows = []
    for src_rel, dst_rel in sorted(WEIGHT_LINKS.items()):
        target = mosaic_root / src_rel
        link = source_root / dst_rel
        row = {"source_weight": src_rel, "expected_path": dst_rel, "target_exists": target.is_file()}
        if target.is_file():
            row.update(safe_symlink(target, link, force=force))
        else:
            row.update({"link": str(link), "target": str(target), "status": "MISSING_WEIGHT"})
        rows.append(row)
    return rows


def find_train_case_dir(case_id: str) -> Path:
    hits = sorted(TRAIN_ROOT.glob(f"*/{case_id}"))
    if not hits:
        raise FileNotFoundError(f"cannot find train case {case_id} under {TRAIN_ROOT}")
    return hits[0]


def stage_fold0_input(result_root: Path, *, limit_cases: int | None, force: bool) -> tuple[Path, list[dict[str, Any]]]:
    cases = load_fold_val_cases(SPLIT_PATH, 0)
    if limit_cases is not None:
        cases = cases[:limit_cases]
    val_root = result_root / "mosaic_runtime/fold0_val/MyoPS_val/AnonymousCenter"
    rows: list[dict[str, Any]] = []
    for case_id in cases:
        src_dir = find_train_case_dir(case_id)
        dst_dir = val_root / case_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        for modality in ["LGE", "C0", "T2"]:
            src = src_dir / f"{case_id}_{modality}.nii.gz"
            dst = dst_dir / f"{case_id}_{modality}.nii.gz"
            row = {"case_id": case_id, "modality": modality, "source": str(src), "dest": str(dst), "source_exists": src.is_file()}
            if src.is_file():
                row.update(safe_symlink(src, dst, force=force))
            else:
                row["status"] = "MISSING_MODALITY"
            rows.append(row)
    return val_root.parents[2], rows


def main() -> int:
    args = parse_args()
    weight_rows = prepare_weight_links(args.source_root, args.mosaic_root, force=args.force)
    stage_rows: list[dict[str, Any]] = []
    staged_val_dir = None
    if args.stage_fold0:
        staged_val_dir, stage_rows = stage_fold0_input(args.result_root, limit_cases=args.limit_cases, force=args.force)
    source_commit = MOSAIC_SOURCE_COMMIT
    receipt = {
        "schema_version": 1,
        "status": "READY_TO_START_INFERENCE" if all(r["status"] in {"CREATED", "EXISTS"} for r in weight_rows) and (not args.stage_fold0 or all(r.get("status") in {"CREATED", "EXISTS"} for r in stage_rows if r["source_exists"])) else "NEEDS_REPAIR",
        "training_authorized": False,
        "validation_upload_authorized": False,
        "production_path_dependency_authorized": False,
        "source_root": str(args.source_root),
        "mosaic_root": str(args.mosaic_root),
        "source_repository": "https://github.com/IndeedLiu/MoSAIC",
        "source_commit": source_commit,
        "weight_links": weight_rows,
        "stage_fold0": bool(args.stage_fold0),
        "staged_val_dir": str(staged_val_dir) if staged_val_dir else None,
        "staged_rows": stage_rows,
        "next_inference_command_official_val": "cd third_party/MoSAIC/source && ../../../envs/env_CARE/bin/python scripts/infer_and_submit.py --val-dir ../../../data/CARE_Challenge --gpu 0",
        "next_inference_command_fold0_staged": "cd third_party/MoSAIC/source && ../../../envs/env_CARE/bin/python scripts/infer_and_submit.py --val-dir ../../../results/20260725_care_m0_mosaic_fold0_fair_repro/mosaic_runtime/fold0_val --gpu 0",
    }
    write_json(args.result_root / "mosaic_runtime_preflight.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "READY_TO_START_INFERENCE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
