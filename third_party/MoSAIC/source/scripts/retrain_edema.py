#!/usr/bin/env python3
"""Retrain EdemaNet only (5-fold + full-data) with validation-based checkpoint selection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import numpy as np

from myops.data.labels import TRACK_MYOPS
from myops.data.splits import split_records_by_fold, filter_records
from myops.utils.io import read_jsonl
from scripts.five_fold_train_all_edema import train_edema_net


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--mode", choices=["cv", "full", "both"], default="both")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    cache_dir = str(root / "cache")
    manifest = str(root / "cache" / "manifest.jsonl")
    all_records = filter_records(read_jsonl(manifest), TRACK_MYOPS)

    if args.mode in ("cv", "both"):
        for fold in range(5):
            fold_dir = root / "grid_output" / "5fold" / f"fold{fold}"
            edema_dir = fold_dir / "edema"
            coarse_pred_dir = str(fold_dir / "coarse_predictions")

            if (edema_dir / "best.pt").exists():
                print(f"Fold {fold}: edema best.pt already exists, skipping")
                continue

            print(f"\n{'='*60}")
            print(f"  Retraining EdemaNet fold={fold}")
            print(f"{'='*60}")

            train_recs, val_recs = split_records_by_fold(all_records, fold)
            train_edema_net(train_recs, val_recs, cache_dir, coarse_pred_dir,
                           edema_dir, args.gpu)

    if args.mode in ("full", "both"):
        full_dir = root / "full_train" / "myops" / "fold-1"
        edema_dir = full_dir / "edema"
        coarse_pred_dir = str(full_dir / "coarse_predictions")

        if (edema_dir / "best.pt").exists():
            print("Full data: edema best.pt already exists, skipping")
        else:
            print(f"\n{'='*60}")
            print(f"  Retraining EdemaNet full-data")
            print(f"{'='*60}")
            train_edema_net(all_records, [], cache_dir, coarse_pred_dir,
                           edema_dir, args.gpu)


if __name__ == "__main__":
    main()
