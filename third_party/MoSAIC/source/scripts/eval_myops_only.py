#!/usr/bin/env python3
"""Run MyoPS-only 5-fold V4 eval."""
import sys, json, numpy as np, torch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.eval_5fold import eval_myops_fold_v4
from myops.data.labels import TRACK_MYOPS, EDEMA_CENTERS
from myops.data.splits import split_records_by_fold, filter_records
from myops.utils.io import read_jsonl

device = torch.device("cuda:0")
cache_root = str(Path(__file__).resolve().parent.parent / "cache")
root = Path(__file__).resolve().parent.parent

myops_records = filter_records(read_jsonl(str(root / "cache/manifest.jsonl")), TRACK_MYOPS)
edema_records = [r for r in myops_records if r.get("center") in EDEMA_CENTERS]

results = {}
for fold in range(5):
    fold_dir = root / "grid_output" / "5fold" / f"fold{fold}"
    _, val_recs = split_records_by_fold(edema_records, fold)
    print(f"\n--- Fold {fold} ({len(val_recs)} B+C val cases) ---")
    avg = eval_myops_fold_v4(fold, fold_dir, val_recs, cache_root, device)
    results[fold] = avg
    s, e = avg["scar_dice"], avg["edema_dice"]
    print(f"  -> scar={s:.4f} edema={e:.4f}")

print("\n" + "=" * 60)
print("  MYOPS 5-FOLD V4 SUMMARY (B+C only)")
print("=" * 60)
for fold in range(5):
    m = results[fold]
    parts = " ".join(f"{k}={v:.4f}" for k, v in m.items())
    print(f"  Fold {fold}: {parts}")

avg_all = {k: float(np.mean([results[f][k] for f in range(5)])) for k in results[0]}
parts = " ".join(f"{k}={v:.4f}" for k, v in avg_all.items())
print(f"  AVG:    {parts}")

out = root / "grid_output" / "5fold" / "myops_v4_eval.json"
json.dump({"fold_results": {str(k): v for k, v in results.items()}, "average": avg_all}, open(out, "w"), indent=2)
print(f"\nSaved to {out}")
