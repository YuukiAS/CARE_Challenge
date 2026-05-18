#!/usr/bin/env python3
"""Build MyoPS-Net round6 modality-routed hybrid predictions.

For C0+LGE+T2 validation cases, use the round5 full-modality expert.
For T2-missing cases, keep the round4 safe/routed prediction.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def load_modalities(data_root: Path) -> dict[str, dict[str, bool]]:
    path = data_root / "modalities_present.json"
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {
        case_id: {
            "c0": bool(info.get("c0")),
            "lge": bool(info.get("lge")),
            "t2": bool(info.get("t2")),
        }
        for case_id, info in raw.items()
    }


def load_fold_cases(fold_json: Path | None, fold: int | None) -> list[str] | None:
    if fold_json is None:
        return None
    if fold is None:
        raise ValueError("--fold is required when --fold-json is provided")
    with fold_json.open(encoding="utf-8") as f:
        data = json.load(f)
    folds = data["folds"]
    if fold < 0 or fold >= len(folds):
        raise ValueError(f"fold {fold} out of range [0, {len(folds)})")
    return sorted(folds[fold]["val"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--fullmod-pred-dir", type=Path, required=True)
    ap.add_argument("--fallback-pred-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--summary-json", type=Path, required=True)
    ap.add_argument("--fold-json", type=Path, default=None, help="Optional protocol split JSON; routes only fold val cases")
    ap.add_argument("--fold", type=int, default=None)
    args = ap.parse_args()

    modalities = load_modalities(args.data_root)
    case_ids = load_fold_cases(args.fold_json, args.fold)
    if case_ids is None:
        case_ids = sorted(modalities)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for stale in args.output_dir.glob("*.nii.gz"):
        stale.unlink()

    summary: dict[str, object] = {
        "data_root": str(args.data_root),
        "fold_json": str(args.fold_json) if args.fold_json is not None else None,
        "fold": args.fold,
        "fullmod_pred_dir": str(args.fullmod_pred_dir),
        "fallback_pred_dir": str(args.fallback_pred_dir),
        "output_dir": str(args.output_dir),
        "cases": {},
        "counts": {"fullmod_t2_present": 0, "fallback_t2_missing": 0},
    }

    for case_id in case_ids:
        if case_id not in modalities:
            raise KeyError(f"Case {case_id} from fold list is missing from {args.data_root / 'modalities_present.json'}")
        info = modalities[case_id]
        use_fullmod = bool(info.get("c0") and info.get("lge") and info.get("t2"))
        src = (args.fullmod_pred_dir if use_fullmod else args.fallback_pred_dir) / f"{case_id}.nii.gz"
        if not src.is_file():
            raise FileNotFoundError(f"Missing routed source prediction for {case_id}: {src}")
        dst = args.output_dir / f"{case_id}.nii.gz"
        shutil.copy2(src, dst)
        route = "fullmod_t2_present" if use_fullmod else "fallback_t2_missing"
        summary["counts"][route] += 1
        summary["cases"][case_id] = {
            "modalities": info,
            "route": route,
            "source": str(src),
            "output": str(dst),
        }

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote hybrid predictions to {args.output_dir}")
    print(f"Wrote {args.summary_json}")


if __name__ == "__main__":
    main()
