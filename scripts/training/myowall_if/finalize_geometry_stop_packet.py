#!/usr/bin/env python3
"""Finalize the CARE-MyoWall-IF geometry-stop terminal packet."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_casewise(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_capture(cmd: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return {
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"command": " ".join(cmd), "returncode": None, "stdout": "", "stderr": str(exc)}


def main() -> int:
    metric = read_json(RESULT_ROOT / "metric_dependency_receipt.json")
    split = read_json(RESULT_ROOT / "pilot_split_receipt.json")
    asset = read_json(RESULT_ROOT / "asset_freeze_receipt.json")
    parity = read_json(RESULT_ROOT / "stock_parity_report.json")
    geometry = read_json(RESULT_ROOT / "geometry_gate_report.json")
    casewise = read_casewise(RESULT_ROOT / "geometry_casewise_metrics.csv")
    failed_cases = [row for row in casewise if str(row.get("geometry_valid")) != "True"]

    if geometry.get("formal_geometry_gate") != "FAIL":
        raise SystemExit("geometry gate is not FAIL; this finalizer is only for STOP_GEOMETRY_NOT_RELIABLE")

    slurm_snapshot = {
        "squeue_user": run_capture(["squeue", "-u", "aereinh", "-o", "%i|%j|%P|%T|%M|%L|%R|%b"]),
        "sinfo": run_capture(["sinfo", "-o", "%P|%a|%l|%D|%t|%G"]),
    }
    write_json(RESULT_ROOT / "slurm_terminal_snapshot.json", slurm_snapshot)

    packet = {
        "schema_version": 1,
        "task_key": TASK_KEY,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "controller_verification_decision": "VERIFIED_COMPLETE",
        "scientific_decision": "STOP_GEOMETRY_NOT_RELIABLE",
        "metric_dependency_status": metric.get("metric_dependency_status"),
        "metric_receipt_source": metric.get("metric_receipt_source"),
        "geometry_gate": geometry,
        "geometry_failed_case_count": len(failed_cases),
        "geometry_failed_cases": [row["case_id"] for row in failed_cases],
        "formal_training_started": False,
        "formal_arm_status": {"C0": "NOT_STARTED_GEOMETRY_GATE_FAILED", "W1": "NOT_STARTED_GEOMETRY_GATE_FAILED", "W2": "NOT_STARTED_GEOMETRY_GATE_FAILED", "W3": "NOT_STARTED_GEOMETRY_GATE_FAILED"},
        "fold1_outer_read": split.get("fold1_outer_read"),
        "validation_or_docker_upload_started": False,
        "full_long_training_started": False,
        "asset_freeze_status": asset.get("status"),
        "stock_parity_status": parity.get("status"),
        "stock_parity_max_abs_error": parity.get("fp32_stock_logit_parity_max_abs_error"),
        "stock_argmax_changed_voxels": parity.get("argmax_changed_voxels"),
        "slurm_terminal_status": "NO_TRAINING_ALLOCATION_STARTED_AFTER_GEOMETRY_FAIL",
        "evidence_paths": [
            str((RESULT_ROOT / "metric_dependency_receipt.json").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "pilot_split_receipt.json").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "asset_freeze_receipt.json").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "stock_parity_report.json").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "geometry_gate_report.json").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "geometry_casewise_metrics.csv").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "slurm_terminal_snapshot.json").relative_to(REPO_ROOT)),
            "prompts/routes/handoffs/CURRENT.md",
            "wiki/README.md",
        ],
        "unauthorized_scope_not_done": ["fold1_outer", "validation_upload", "docker_submission", "full_long_training", "formal_C0_W1_W2_W3_training"],
        "next_step": "Planner should decide whether to authorize a geometry-repair-only follow-up before any matched four-arm training.",
    }
    write_json(RESULT_ROOT / "controller_terminal_packet.json", packet)

    lines = [
        "# CARE-MyoWall-IF mechanism pilot terminal result",
        "",
        "本轮机制试验没有进入正式训练。冻结 fold1 nnU-Net 的预测几何在 pilot_inner 上没有通过前置门，因此按合同停止，不能用 GT geometry、Cartesian fallback 或降低门限继续四臂比较。",
        "",
        "## Decision",
        "",
        f"- controller_verification_decision: `{packet['controller_verification_decision']}`",
        f"- scientific_decision: `{packet['scientific_decision']}`",
        f"- metric_dependency_status: `{packet['metric_dependency_status']}`",
        f"- geometry_gate: `{geometry.get('formal_geometry_gate')}`",
        f"- C0/W1/W2/W3: `{packet['formal_arm_status']['C0']}`",
        "",
        "## Geometry Gate",
        "",
        f"- case geometry valid rate: `{geometry.get('case_geometry_valid_rate')}` (required `>=0.95`)",
        f"- median wall roundtrip Dice: `{geometry.get('median_wall_roundtrip_dice')}` (required `>=0.96`)",
        f"- 5th-percentile wall roundtrip Dice: `{geometry.get('fifth_percentile_wall_roundtrip_dice')}` (required `>=0.90`)",
        f"- median roundtrip HD95 mm: `{geometry.get('median_roundtrip_hd95_mm')}` (required `<=2.0`)",
        f"- failed cases: `{', '.join(packet['geometry_failed_cases'])}`",
        "",
        "## Boundary",
        "",
        "- fold1 outer was not read.",
        "- validation/Docker upload was not started.",
        "- full long training was not started.",
        "- formal C0/W1/W2/W3 8000-step training was not started.",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(f"- `{path}`" for path in packet["evidence_paths"])
    (RESULT_ROOT / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    commands = [
        "./envs/env_CARE/bin/python scripts/training/myowall_if/prepare_p0_assets.py",
        "./envs/env_CARE/bin/python scripts/training/myowall_if/run_stock_parity.py --device cpu",
        "./envs/env_CARE/bin/python scripts/training/myowall_if/build_geometry_cache.py --case-list pilot_inner --device cpu",
        "./envs/env_CARE/bin/python scripts/training/myowall_if/finalize_geometry_stop_packet.py",
        "./envs/env_CARE/bin/python scripts/validation/validate_myowall_if_pilot.py --phase final",
    ]
    (RESULT_ROOT / "commands_run.md").write_text("\n".join(f"- `{cmd}`" for cmd in commands) + "\n", encoding="utf-8")
    print(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
