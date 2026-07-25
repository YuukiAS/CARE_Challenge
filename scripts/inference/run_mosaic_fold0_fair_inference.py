#!/usr/bin/env python3
"""MoSAIC fold0 fair-inference gate for CARE.

This wrapper records the protocol state and refuses to fabricate native MoSAIC
predictions when the native source/entrypoint is unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))

from mosaic_fair_protocol import (  # noqa: E402
    CARE_INPUT_ORDER,
    DEFAULT_CONFIG,
    DEFAULT_MOSAIC_ROOT,
    DEFAULT_MOSAIC_SOURCE_ROOT,
    DEFAULT_RESULT_ROOT,
    MOSAIC_INPUT_ORDER,
    find_native_mosaic_source,
    label_mapping_audit_rows,
    load_fold_val_cases,
    load_yaml,
    protocol_receipt,
    weight_inventory,
    write_csv,
    write_json,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--mosaic-root", type=Path, default=Path(os.environ.get("MOSAIC_ROOT", str(DEFAULT_MOSAIC_ROOT))))
    ap.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    ap.add_argument("--source-root", type=Path, default=DEFAULT_MOSAIC_SOURCE_ROOT)
    ap.add_argument("--native-entrypoint", type=Path, default=None)
    ap.add_argument("--val-dir", type=Path, default=None, help="MoSAIC validation-style root containing MyoPS_val and optionally CineMyoPS_val.")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="Write receipts only; do not run native inference.")
    ap.add_argument("--limit-cases", type=int, default=None)
    ap.add_argument("--print-contract", action="store_true")
    return ap.parse_args()


def write_preflight_outputs(result_root: Path, payload: dict[str, Any], cases: list[str]) -> None:
    write_json(result_root / "mosaic_inference_receipt.json", payload)
    write_csv(result_root / "label_mapping_audit.csv", label_mapping_audit_rows())
    write_csv(
        result_root / "geometry_audit.csv",
        [
            {
                "case_id": case_id,
                "model_id": "native_mosaic",
                "status": "NOT_RUN",
                "reason": payload["status"],
                "required_reference": "care_official_raw_case_geometry",
                "layout_required": "ZHW",
                "known_bad_layouts": "HWZ,HZW,WZH,WHZ,ZWH",
            }
            for case_id in cases
        ],
        fieldnames=[
            "case_id",
            "model_id",
            "status",
            "reason",
            "required_reference",
            "layout_required",
            "known_bad_layouts",
        ],
    )


def main() -> int:
    args = parse_args()
    config = load_yaml(args.config)
    split_path = REPO_ROOT / config["dataset"]["split_path"]
    cases = load_fold_val_cases(split_path, int(config["dataset"]["fold"]))
    if args.limit_cases is not None:
        cases = cases[: args.limit_cases]

    native = find_native_mosaic_source(args.mosaic_root, args.source_root)
    native_entrypoint = args.native_entrypoint or (args.source_root / "scripts/infer_and_submit.py")
    val_dir = args.val_dir or (args.result_root / "mosaic_runtime/fold0_val")
    weights = weight_inventory(args.mosaic_root) if args.mosaic_root.is_dir() else []
    missing_weights = [
        entry["path"]
        for entry in config.get("required_weights", [])
        if not (args.mosaic_root / entry["path"]).is_file()
    ]

    status = "READY_TO_START_INFERENCE" if args.dry_run else "RUN_NATIVE_INFERENCE"
    reason = "native source, entrypoint, and weights are present; dry run did not write predictions" if args.dry_run else "running upstream MoSAIC native inference"
    exit_code = 0
    if missing_weights:
        status = "NEEDS_MOSAIC_WEIGHTS"
        reason = "required MoSAIC weights missing"
        exit_code = 2
    elif native["source_status"] != "FOUND":
        status = "NEEDS_MOSAIC_SOURCE"
        reason = "MoSAIC weights are present but native source code was not found"
        exit_code = 0 if args.dry_run else 2
    elif not native_entrypoint.is_file():
        status = "NEEDS_NATIVE_ENTRYPOINT"
        reason = f"native entrypoint not found: {native_entrypoint}"
        exit_code = 0 if args.dry_run else 2
    elif not args.dry_run and not (val_dir / "MyoPS_val" / "AnonymousCenter").is_dir():
        status = "NEEDS_MOSAIC_INPUT"
        reason = f"MoSAIC validation-style MyoPS input not found under {val_dir}"
        exit_code = 2

    receipt = protocol_receipt(config, result_status=status, reason=reason)
    receipt.update(
        {
            "config_path": str(args.config.relative_to(REPO_ROOT)) if args.config.is_absolute() else str(args.config),
            "result_root": str(args.result_root.relative_to(REPO_ROOT)) if args.result_root.is_absolute() else str(args.result_root),
            "mosaic_root": str(args.mosaic_root),
            "dry_run": bool(args.dry_run),
            "case_count_requested": len(cases),
            "case_ids": cases,
            "native_source": native,
            "native_entrypoint": str(native_entrypoint),
            "val_dir": str(val_dir),
            "gpu": int(args.gpu),
            "missing_weights": missing_weights,
            "weight_count": len(weights),
            "weight_bytes": sum(int(row["bytes"]) for row in weights),
            "care_to_mosaic_channel_reorder": [CARE_INPUT_ORDER.index(name) for name in MOSAIC_INPUT_ORDER],
        }
    )
    write_preflight_outputs(args.result_root, receipt, cases)

    if args.print_contract:
        print(json.dumps(receipt, indent=2, sort_keys=True))

    if status in {"READY_TO_START_INFERENCE", "NEEDS_MOSAIC_SOURCE", "NEEDS_NATIVE_ENTRYPOINT", "NEEDS_MOSAIC_WEIGHTS", "NEEDS_MOSAIC_INPUT"}:
        return exit_code

    cmd = [sys.executable, str(native_entrypoint), "--val-dir", str(val_dir), "--gpu", str(args.gpu)]
    completed = subprocess.run(cmd, cwd=args.source_root, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
