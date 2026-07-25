#!/usr/bin/env python3
"""Train all models on full data (no fold held out) for final submission.

Usage:
    CUDA_VISIBLE_DEVICES=0 python scripts/train_full.py --tracks myops --gpu 0
    CUDA_VISIBLE_DEVICES=1 python scripts/train_full.py --tracks cine --gpu 1
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, required=True, help="Path to Myo_train data directory")
    parser.add_argument("--tracks", type=str, nargs="+", default=["myops", "cine"],
                        choices=["myops", "cine"])
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()

    cmd = [
        sys.executable, str(ROOT / "scripts" / "5fold_train_all.py"),
        "--data-dir", args.data_dir,
        "--mode", "full",
        "--tracks", *args.tracks,
        "--gpu", str(args.gpu),
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
