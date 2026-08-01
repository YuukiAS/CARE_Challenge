#!/usr/bin/env python3
"""Audit target-domain gap-closure training checkpoints without running inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_checkpoint(path: Path) -> tuple[bool, str | None, dict[str, Any]]:
    try:
        obj = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:  # noqa: BLE001 - audit must record exact load failure.
        return False, repr(exc), {}
    if isinstance(obj, dict):
        keys = sorted(str(k) for k in obj.keys())
        summary: dict[str, Any] = {
            "top_level_keys": keys,
            "step": obj.get("step"),
            "fold": obj.get("fold"),
            "epoch": obj.get("epoch"),
        }
        model_state = obj.get("model") or obj.get("network_weights") or obj.get("state_dict")
        if isinstance(model_state, dict):
            summary["model_state_key_count"] = len(model_state)
        optimizer_state = obj.get("optimizer") or obj.get("optimizer_state")
        if isinstance(optimizer_state, dict):
            summary["optimizer_state_present"] = True
        return True, None, summary
    return True, None, {"object_type": type(obj).__name__}


def checkpoint_record(path: Path, lane: str, fold: int, do_torch_load: bool, do_hash: bool) -> dict[str, Any]:
    ok: bool | None
    error: str | None
    summary: dict[str, Any]
    if do_torch_load:
        ok, error, summary = load_checkpoint(path)
    else:
        ok, error, summary = None, None, {"torch_load_skipped": "not selected by load_policy"}
    match = re.search(r"step(\d+)", path.name)
    return {
        "lane": lane,
        "fold": fold,
        "path": str(path),
        "name": path.name,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() and do_hash else None,
        "sha256_skipped": path.exists() and not do_hash,
        "torch_load_success": ok,
        "torch_load_error": error,
        "parsed_step_from_name": int(match.group(1)) if match else None,
        "checkpoint_summary": summary,
    }


def receipt(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_lane_checkpoints(lane: str, fold: int) -> list[Path]:
    receipt_path = RESULT_ROOT / lane / f"fold{fold}_training_receipt.json"
    data = receipt(receipt_path)
    paths: list[Path] = []
    if data.get("checkpoint_final"):
        paths.append(Path(str(data["checkpoint_final"])))
    if data.get("output_folder"):
        paths.extend(sorted(Path(str(data["output_folder"])).glob("checkpoint*.pth")))
    if data.get("checkpoint_dir"):
        paths.extend(sorted(Path(str(data["checkpoint_dir"])).glob("checkpoint_step*.pt")))
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def expected_steps(lane: str) -> list[int]:
    if lane in {"m1_myopsnet_l_care", "m2_i_mmseg_care"}:
        return list(range(500, 6001, 500))
    if lane in {"m0r_faithful_control", "m3_care_tds"}:
        return list(range(500, 4001, 500))
    return []


def should_torch_load(path: Path, paths: list[Path], load_policy: str) -> bool:
    if load_policy == "none":
        return False
    if load_policy == "all":
        return True
    if path.name == "checkpoint_final.pth":
        return True
    stepped = [(p, re.search(r"step(\d+)", p.name)) for p in paths]
    numeric = [(p, int(m.group(1))) for p, m in stepped if m]
    return bool(numeric and path == max(numeric, key=lambda item: item[1])[0])


def should_hash(path: Path, paths: list[Path], hash_policy: str) -> bool:
    if hash_policy == "none":
        return False
    if hash_policy == "all":
        return True
    if path.name == "checkpoint_final.pth":
        return True
    stepped = [(p, re.search(r"step(\d+)", p.name)) for p in paths]
    numeric = [(p, int(m.group(1))) for p, m in stepped if m]
    return bool(numeric and path == max(numeric, key=lambda item: item[1])[0])


def audit(load_policy: str, hash_policy: str) -> dict[str, Any]:
    lanes = {
        "m0r_faithful_control": "M0R_FAITHFUL_CONTROL",
        "m1_myopsnet_l_care": "M1_MYOPSNET_L_CARE",
        "m2_i_mmseg_care": "M2_I_MMSEG_CARE",
        "m3_care_tds": "M3_CARE_TDS",
    }
    lane_reports: dict[str, Any] = {}
    all_errors: list[str] = []
    contract_gaps: list[str] = []
    for lane_dir, lane_id in lanes.items():
        fold_reports: dict[str, Any] = {}
        for fold in (2, 3):
            paths = discover_lane_checkpoints(lane_dir, fold)
            records = [
                checkpoint_record(
                    path,
                    lane_id,
                    fold,
                    should_torch_load(path, paths, load_policy),
                    should_hash(path, paths, hash_policy),
                )
                for path in paths
            ]
            loaded_steps = sorted(
                {
                    int(record["parsed_step_from_name"])
                    for record in records
                    if record["parsed_step_from_name"] is not None and record["exists"]
                }
            )
            missing_steps = [step for step in expected_steps(lane_dir) if step not in loaded_steps]
            if missing_steps:
                contract_gaps.append(
                    f"{lane_id} fold{fold} missing expected 500-step checkpoints: "
                    + ",".join(str(step) for step in missing_steps)
                )
            load_failures = [record for record in records if record["torch_load_success"] is False]
            for record in load_failures:
                all_errors.append(f"{lane_id} fold{fold} failed to torch.load {record['path']}: {record['torch_load_error']}")
            fold_reports[str(fold)] = {
                "checkpoint_count": len(records),
                "records": records,
                "loaded_named_steps": loaded_steps,
                "expected_named_steps": expected_steps(lane_dir),
                "missing_expected_named_steps": missing_steps,
                "all_discovered_checkpoints_torch_load": not load_failures,
                "contract_step_checkpoint_complete": not missing_steps,
            }
        lane_reports[lane_id] = fold_reports
    if all_errors:
        status = "LOAD_FAILURE"
    elif contract_gaps:
        status = "PASS_WITH_CONTRACT_GAPS"
    else:
        status = "PASS"
    return {
        "created_at": now_utc(),
        "task_key": TASK_KEY,
        "audit_scope": "checkpoint sha256, size, bounded torch.load, top-level keys, and expected 500-step checkpoint presence",
        "load_policy": load_policy,
        "hash_policy": hash_policy,
        "lanes": lane_reports,
        "status": status,
        "load_errors": all_errors,
        "known_contract_gaps": contract_gaps,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(RESULT_ROOT / "checkpoint_reload_audit.json"))
    parser.add_argument("--load-policy", choices=["final", "all", "none"], default="final")
    parser.add_argument("--hash-policy", choices=["final", "all", "none"], default="final")
    args = parser.parse_args()
    payload = audit(args.load_policy, args.hash_policy)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(output_path)}, indent=2, sort_keys=True))
    return 1 if payload["status"] == "LOAD_FAILURE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
