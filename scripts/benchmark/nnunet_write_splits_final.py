#!/usr/bin/env python3
"""
Write nnU-Net v2 splits_final.json from CARE protocol JSON (from generate_splits.py).

nnU-Net expects a list of dicts: [{"train": [...], "val": [...]}, ...] with case ids
matching imagesTr filename prefixes (e.g. Case001).

Set NNUNET_PREPROCESSED or pass --preprocessed-dir (default: $nnUNet_preprocessed or ~/nnUNet_preprocessed).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def load_protocol(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_dataset_dir(preprocessed_root: Path, dataset_name: str) -> Path:
    d = preprocessed_root / dataset_name
    if not d.is_dir():
        print(f"Dataset folder not found: {d}", file=sys.stderr)
        sys.exit(1)
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="Write nnU-Net v2 splits_final.json from protocol JSON")
    ap.add_argument(
        "--protocol-json",
        type=Path,
        required=True,
        help="Path to splits_MyoPS.json or splits_CineMyoPS.json",
    )
    ap.add_argument(
        "--dataset-name",
        type=str,
        required=True,
        help="Folder name under nnUNet_preprocessed, e.g. Dataset501_CAREMyoPS",
    )
    ap.add_argument(
        "--preprocessed-dir",
        type=Path,
        default=None,
        help="nnUNet_preprocessed root (default: env NNUNET_PREPROCESSED or ~/nnUNet_preprocessed)",
    )
    ap.add_argument(
        "--backup-existing",
        action="store_true",
        help="If splits_final.json exists, rename to splits_final.json.bak before writing",
    )
    args = ap.parse_args()

    root = args.preprocessed_dir
    if root is None:
        root = Path(os.environ.get("nnUNet_preprocessed", os.path.expanduser("~/nnUNet_preprocessed")))

    proto = load_protocol(args.protocol_json)
    folds = proto.get("folds")
    if not folds:
        print("Protocol JSON missing 'folds'", file=sys.stderr)
        sys.exit(1)

    nn_list: list[dict[str, list[str]]] = []
    for f in folds:
        nn_list.append(
            {
                "train": list(f["train"]),
                "val": list(f["val"]),
            }
        )

    ds_dir = resolve_dataset_dir(root, args.dataset_name)
    out_path = ds_dir / "splits_final.json"

    if out_path.is_file():
        if args.backup_existing:
            bak = out_path.with_suffix(".json.bak")
            shutil.copy2(out_path, bak)
            print(f"Backed up existing split to {bak}")
        else:
            print(
                f"Refusing to overwrite {out_path} without --backup-existing",
                file=sys.stderr,
            )
            sys.exit(1)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(nn_list, f, indent=2)

    print(f"Wrote {out_path} ({len(nn_list)} folds)")


if __name__ == "__main__":
    main()
