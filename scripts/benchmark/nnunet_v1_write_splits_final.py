#!/usr/bin/env python3
"""Write nnU-Net v1 splits_final.pkl from CARE protocol JSON."""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
import sys
from pathlib import Path


def load_protocol(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def collect_task_case_ids(task_dir: Path) -> list[str]:
    labels_dir = task_dir / "labelsTr"
    if not labels_dir.is_dir():
        raise FileNotFoundError(f"Missing labelsTr under {task_dir}")
    return sorted(p.name.replace(".nii.gz", "") for p in labels_dir.glob("*.nii.gz"))


def resolve_case_id(case_id: str, available: list[str]) -> str:
    if case_id in available:
        return case_id
    suffix_matches = [cid for cid in available if cid.endswith(f"_{case_id}")]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    raise KeyError(f"Cannot uniquely resolve protocol case '{case_id}' from task ids: {suffix_matches}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Write nnU-Net v1 splits_final.pkl from CARE protocol JSON")
    ap.add_argument("--protocol-json", type=Path, required=True)
    ap.add_argument("--task-dir", type=Path, required=True, help="Raw task dir containing labelsTr/")
    ap.add_argument("--preprocessed-task-dir", type=Path, required=True, help="Preprocessed task dir containing splits_final.pkl")
    ap.add_argument("--backup-existing", action="store_true")
    args = ap.parse_args()

    proto = load_protocol(args.protocol_json)
    folds = proto.get("folds")
    if not folds:
        print("Protocol JSON missing 'folds'", file=sys.stderr)
        sys.exit(1)

    available = collect_task_case_ids(args.task_dir)
    available_set = set(available)
    splits: list[dict[str, list[str]]] = []
    for fold in folds:
        train_ids = [resolve_case_id(cid, available) for cid in fold["train"]]
        val_ids = [resolve_case_id(cid, available) for cid in fold["val"]]
        if not set(train_ids).issubset(available_set) or not set(val_ids).issubset(available_set):
            print("Resolved ids not present in task case universe", file=sys.stderr)
            sys.exit(1)
        splits.append({"train": train_ids, "val": val_ids})

    out_path = args.preprocessed_task_dir / "splits_final.pkl"
    if out_path.exists():
        if args.backup_existing:
            bak = out_path.with_suffix(".pkl.bak")
            shutil.copy2(out_path, bak)
            print(f"Backed up existing split to {bak}")
        else:
            print(f"Refusing to overwrite {out_path} without --backup-existing", file=sys.stderr)
            sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        pickle.dump(splits, f)
    print(f"Wrote {out_path} ({len(splits)} folds)")


if __name__ == "__main__":
    main()
