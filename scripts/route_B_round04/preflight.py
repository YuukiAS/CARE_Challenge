#!/usr/bin/env python3
"""Compute/runtime preflight for Route B Round04 stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        import torch
        from torch import optim

        model = torch.nn.Conv3d(3, 3, 1)
        opt = optim.AdamW(model.parameters(), lr=1e-3)
        del opt
        torch_import = True
        torch_version = torch.__version__
        cuda_available = torch.cuda.is_available()
        cuda_device_count = torch.cuda.device_count()
    except Exception as exc:  # noqa: BLE001
        torch_import = False
        torch_version = ""
        cuda_available = False
        cuda_device_count = 0
        errors.append(f"torch_or_optimizer_import_failed:{exc}")

    snapshot_receipt = REPO_ROOT / "results/route_B/round04/planning_snapshot/materialization_receipt.json"
    if not snapshot_receipt.is_file():
        errors.append("planning_snapshot_receipt_missing")
    writable_roots = [
        REPO_ROOT / "results/route_B/round04" / "executors" / args.stage,
        REPO_ROOT / "results/route_B/runtime/round04" / args.stage,
        REPO_ROOT / "logs",
    ]
    for root in writable_roots:
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".preflight_write_probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"writable_root_failed:{root}:{exc}")

    payload = {
        "status": "PASS" if not errors else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": args.stage,
        "python_executable": sys.executable,
        "expected_python": "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python",
        "torch_import": torch_import,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "cuda_device_count": cuda_device_count,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "contract_path": str(args.contract),
        "contract_sha256": sha256_file(args.contract),
        "snapshot_receipt_present": snapshot_receipt.is_file(),
        "writable_roots": [str(path) for path in writable_roots],
        "errors": errors,
    }
    write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
