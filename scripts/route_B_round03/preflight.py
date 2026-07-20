#!/usr/bin/env python3
"""Route B Round03 compute preflight receipt."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executor", required=True)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    receipt = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "executor": args.executor,
        "partition": args.partition,
        "config": str(args.config),
        "python_executable": sys.executable,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "official_cinema_package_available": importlib.util.find_spec("cinema") is not None,
        "config_exists": args.config.exists(),
        "status": "PASS" if args.config.exists() else "FAIL",
    }
    out = args.out or Path(f"results/route_B/round03/executors/{args.executor}/preflight_{args.partition}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
