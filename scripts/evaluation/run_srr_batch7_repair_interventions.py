#!/usr/bin/env python3
"""Run Batch7 repair intervention modes with isolated prediction roots."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "envs/env_CARE/bin/python"


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_hash(cmd: list[str]) -> str:
    return hashlib.sha256(json.dumps(cmd, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def configured_modes(cfg: dict[str, Any]) -> list[str]:
    modes = cfg.get("intervention_execution", {}).get("modes", [])
    if not isinstance(modes, list) or not modes:
        raise ValueError("intervention_execution.modes is missing")
    return [str(mode) for mode in modes]


def run_mode(cfg: dict[str, Any], mode: str, *, device: str, max_cases: int, dry_run: bool) -> dict[str, Any]:
    result_root = repo_path(cfg["paths"]["result_root"])
    intervention_root = repo_path(cfg["paths"]["intervention_root"])
    checkpoint = repo_path(cfg["source_checkpoints"]["batch7"]["path"])
    summary = REPO_ROOT / "results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch7_formal300_htzhulab_59789651/variants/batch7_formal300_htzhulab_59789651/summary.json"
    cmd = [
        str(PYTHON),
        "scripts/srr_production/infer_myops.py",
        "--config",
        "configs/srr_production/myops_batch7_repair.yaml",
        "--mode",
        mode,
        "--fold",
        str(cfg["training_data"]["fold"]),
        "--checkpoint",
        str(checkpoint.relative_to(REPO_ROOT)),
        "--training-summary",
        str(summary.relative_to(REPO_ROOT)),
        "--output-root",
        str(intervention_root.relative_to(REPO_ROOT)),
        "--device",
        device,
    ]
    if max_cases > 0:
        cmd.extend(["--max-cases", str(max_cases)])
    receipt_path = intervention_root / mode / "commands.json"
    payload = {
        "mode": mode,
        "command": cmd,
        "command_hash": command_hash(cmd),
        "checkpoint_path": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256_expected": cfg["source_checkpoints"]["batch7"]["sha256"],
        "prediction_root": str((intervention_root / mode / "predictions").relative_to(REPO_ROOT)),
        "dry_run": bool(dry_run),
    }
    if dry_run:
        payload["status"] = "DRY_RUN"
        write_json(receipt_path, payload)
        return payload
    completed = subprocess.run(cmd, cwd=REPO_ROOT, text=True)
    payload["returncode"] = int(completed.returncode)
    payload["status"] = "PASS" if completed.returncode == 0 else "FAIL"
    write_json(receipt_path, payload)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, cmd)
    contract = intervention_root / f"batch3a_{mode}_inference_contract.json"
    if contract.is_file():
        mode_contract = json.loads(contract.read_text(encoding="utf-8"))
        write_json(intervention_root / mode / "prediction_manifest.json", mode_contract)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--result-root", default="")
    parser.add_argument("--mode", default="all")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    if args.result_root:
        cfg["paths"]["result_root"] = args.result_root
        cfg["paths"]["runtime_root"] = str(Path(args.result_root) / "runtime")
        cfg["paths"]["intervention_root"] = str(Path(args.result_root) / "runtime/interventions")
    modes = configured_modes(cfg) if args.mode == "all" else [args.mode]
    result_root = repo_path(cfg["paths"]["result_root"])
    result_root.mkdir(parents=True, exist_ok=True)
    rows = [run_mode(cfg, mode, device=args.device, max_cases=args.max_cases, dry_run=args.dry_run) for mode in modes]
    status = "DRY_RUN_NOT_COMPLETION" if args.dry_run else "PASS"
    contract_name = "intervention_runner_contract.json" if args.mode == "all" else f"intervention_runner_contract_{args.mode}.json"
    write_json(
        result_root / contract_name,
        {
            "status": status,
            "mode_count": len(rows),
            "dry_run": bool(args.dry_run),
            "completion_evidence": not bool(args.dry_run),
            "runs": rows,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
