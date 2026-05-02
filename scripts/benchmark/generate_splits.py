#!/usr/bin/env python3
"""Generate deterministic 5-fold CARE benchmark protocol JSON files."""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


def discover_myops_cases(root: Path) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for case_dir in sorted(root.glob("**/Case*")):
        if not case_dir.is_dir():
            continue
        case_id = case_dir.name
        if not (case_dir / f"{case_id}_gd.nii.gz").is_file():
            continue
        cases.append(
            {
                "case_id": case_id,
                "center": case_dir.parent.name,
                "nnUNet_case_id": case_id,
                "nnUNet_dataset_task": "501",
            }
        )
    return cases


def discover_cine_cases(root: Path) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for cine_path in sorted(root.glob("**/*_Cine.nii.gz")):
        case_id = cine_path.name.replace("_Cine.nii.gz", "")
        if not (cine_path.parent / f"{case_id}_gd.nii.gz").is_file():
            continue
        cases.append(
            {
                "case_id": case_id,
                "center": cine_path.parent.name,
                "nnUNet_case_id": case_id,
                "nnUNet_dataset_task": "502",
            }
        )
    return cases


def shuffled_folds(case_ids: list[str], n_splits: int, random_state: int) -> list[dict[str, list[str]]]:
    ids = list(case_ids)
    random.Random(random_state).shuffle(ids)

    fold_sizes = [len(ids) // n_splits] * n_splits
    for i in range(len(ids) % n_splits):
        fold_sizes[i] += 1

    folds: list[dict[str, list[str]]] = []
    start = 0
    for fold_size in fold_sizes:
        stop = start + fold_size
        val_ids = sorted(ids[start:stop])
        val_set = set(val_ids)
        train_ids = sorted(cid for cid in case_ids if cid not in val_set)
        folds.append({"train": train_ids, "val": val_ids})
        start = stop
    return folds


def write_json(path: Path, data: dict, force: bool) -> None:
    if path.exists() and not force:
        print(f"Reuse existing {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate CARE benchmark cases/splits JSON")
    ap.add_argument("--task", required=True, choices=["MyoPS", "CineMyoPS"])
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=Path("/overflow/htzhu/CARE/data/benchmarks/protocol"))
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--random-state", type=int, default=42)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.task == "MyoPS":
        cases = discover_myops_cases(args.input_root)
    else:
        cases = discover_cine_cases(args.input_root)

    if not cases:
        print(f"No cases discovered under {args.input_root}", file=sys.stderr)
        sys.exit(1)

    case_ids = [c["case_id"] for c in cases]
    folds = shuffled_folds(case_ids, args.n_splits, args.random_state)

    cases_path = args.output_dir / f"cases_{args.task}.json"
    splits_path = args.output_dir / f"splits_{args.task}.json"
    write_json(cases_path, {"cases": cases}, args.force)
    write_json(
        splits_path,
        {
            "task": args.task,
            "input_root": str(args.input_root),
            "protocol": "CARE-5fold",
            "n_splits": args.n_splits,
            "random_state": args.random_state,
            "folds": folds,
        },
        args.force,
    )


if __name__ == "__main__":
    main()
