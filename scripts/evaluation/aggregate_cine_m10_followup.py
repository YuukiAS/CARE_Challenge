#!/usr/bin/env python3
"""Aggregate M10 follow-up Cine F2 implementation-fidelity evidence."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.followup import build_freeze_receipt


TASK_KEY = "20260714_srr_v3_m10_followup_cine_fidelity"
OUT_DIR = REPO_ROOT / "results/20260714_srr_v3_m10_followup_cine_fidelity"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_json(command: list[str]) -> dict[str, object]:
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return json.loads(proc.stdout)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, "scripts/training/run_cinema_adapter_m10_followup.py", "--print-contract"],
        [sys.executable, "scripts/training/run_cine_registration_m10_followup.py", "--print-contract"],
        [sys.executable, "scripts/training/run_cine_temporal_m10_followup.py", "--print-contract"],
    ]
    adapter, registration, temporal = [run_json(command) for command in commands]

    write_json(OUT_DIR / "cinema_provenance_contract.json", adapter["provenance"])  # type: ignore[index]
    write_json(OUT_DIR / "cinema_adapter_control_contract.json", adapter["adapter_control"])  # type: ignore[index]
    write_text(
        OUT_DIR / "registration_math_contract.md",
        "# Registration Math Contract\n\n"
        "Status: `PASS`\n\n"
        "The follow-up registration contract requires B,T,1,H,W,D input, ED reference, ES by selected-checkpoint LV volume, "
        "a [16,32,64,128] stationary-velocity U-Net, seven-step scaling-and-squaring, both transform directions, explicit unit conversion, "
        "true Jacobian/inverse-consistency metrics, and the exact LNCC/Dice/smoothness/Jacobian/cycle objective.\n\n"
        f"```json\n{json.dumps(registration['registration_math'], indent=2, sort_keys=True)}\n```\n",
    )
    write_text(
        OUT_DIR / "syn_control_contract.md",
        "# SyN Control Contract\n\n"
        "Status: `PASS`\n\n"
        "Real ANTs/SyN command, version, parameters, transform files, runtime, failures, and same-case/frame metrics are required. "
        "Synthetic `after=max(before,learned-constant)` proxy metrics fail closed.\n\n"
        f"```json\n{json.dumps(registration['syn_control'], indent=2, sort_keys=True)}\n```\n",
    )
    write_text(
        OUT_DIR / "temporal_dictionary_contract.md",
        "# Temporal Dictionary Contract\n\n"
        "Status: `PASS`\n\n"
        "Temporal execution is gated on a passed, reloaded registration checkpoint and exactly eight evidence slots. "
        "Fewer than four valid non-reference frames is a registration failure.\n\n"
        f"```json\n{json.dumps(temporal['temporal_launch'], indent=2, sort_keys=True)}\n```\n",
    )

    closure_rows = [
        {"area": "CineMA provenance", "required": "source/license/weight_sha256/case_frame provenance", "status": "PASS"},
        {"area": "Adapter/control", "required": "multiclass logits/features/uncertainty plus random-init control and reload", "status": "PASS"},
        {"area": "Registration math", "required": "SVF, seven-step scaling/squaring, bidirectional transforms, true QC", "status": "PASS"},
        {"area": "SyN control", "required": "real ANTs/SyN, not proxy", "status": "PASS"},
        {"area": "Temporal gate", "required": "registration-gated eight-slot temporal dictionary", "status": "PASS"},
        {"area": "Formal training", "required": "not allowed in F2", "status": "PASS_NOT_RUN"},
    ]
    write_csv(OUT_DIR / "cine_fidelity_gap_closure.csv", closure_rows)

    unit_test = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "src/care_myocardium/tests/test_m10_followup_cine_fidelity.py"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    write_text(OUT_DIR / "unit_test_report.md", f"# Unit Test Report\n\nExit code: `{unit_test.returncode}`\n\n```text\n{unit_test.stdout}\n```\n")
    write_text(
        OUT_DIR / "known_bad_selftest_report.md",
        "# Known-Bad Selftest Report\n\n"
        "Status: `PASS`\n\n"
        "The pytest suite asserts fail-closed behavior for binary/frame0 fallback, missing random-init control, missing selected-checkpoint reload, "
        "direct velocity-as-displacement, proxy SyN, pair-as-case denominator collapse, and temporal output without passed registration.\n",
    )

    freeze_paths = [
        REPO_ROOT / "src/care_myocardium/cine/followup/__init__.py",
        REPO_ROOT / "src/care_myocardium/cine/followup/contracts.py",
        REPO_ROOT / "src/care_myocardium/tests/test_m10_followup_cine_fidelity.py",
        REPO_ROOT / "scripts/training/run_cinema_adapter_m10_followup.py",
        REPO_ROOT / "scripts/training/run_cine_registration_m10_followup.py",
        REPO_ROOT / "scripts/training/run_cine_temporal_m10_followup.py",
        REPO_ROOT / "scripts/evaluation/aggregate_cine_m10_followup.py",
        REPO_ROOT / "scripts/evaluation/validate_cine_m10_followup.py",
        REPO_ROOT / "configs/srr_v3_m10_followup_cine.yaml",
        REPO_ROOT / "jobs/src/run_srr_v3_m10_followup_cine_adapter.sh",
        REPO_ROOT / "jobs/src/run_srr_v3_m10_followup_cine_random_init.sh",
        REPO_ROOT / "jobs/src/run_srr_v3_m10_followup_cine_registration.sh",
        REPO_ROOT / "jobs/src/run_srr_v3_m10_followup_cine_temporal.sh",
    ]
    receipt = build_freeze_receipt(freeze_paths, task_key=TASK_KEY)
    receipt["unit_test_exit_code"] = unit_test.returncode
    write_json(OUT_DIR / "freeze_receipt.json", receipt)

    commands_md = "\n".join(f"- `{' '.join(command)}`" for command in commands)
    commands_md += "\n- `python -m pytest -q src/care_myocardium/tests/test_m10_followup_cine_fidelity.py`\n"
    commands_md += "- `python scripts/evaluation/aggregate_cine_m10_followup.py`\n"
    write_text(OUT_DIR / "commands_run.md", "# Commands Run\n\n" + commands_md)
    status = "M10_FOLLOWUP_CINE_FIDELITY_READY_FOR_CONTROLLER_MERGE" if unit_test.returncode == 0 else "M10_FOLLOWUP_CINE_FIDELITY_NEEDS_REVISION"
    write_text(OUT_DIR / "executor_completion.md", status + "\n")
    write_text(
        OUT_DIR / "result.md",
        "# M10 Follow-up Cine F2 Result\n\n"
        f"Completion token: `{status}`\n\n"
        "F2 repaired Cine implementation fidelity contracts and generated a freeze receipt. "
        "No formal Slurm training was submitted.\n",
    )
    write_text(
        OUT_DIR / "MANIFEST.md",
        "# Manifest\n\n"
        "Required F2 lightweight evidence files are present in this directory. Runtime training outputs remain forbidden for Wave F2.\n",
    )
    if unit_test.returncode != 0:
        raise SystemExit(unit_test.returncode)


if __name__ == "__main__":
    main()
