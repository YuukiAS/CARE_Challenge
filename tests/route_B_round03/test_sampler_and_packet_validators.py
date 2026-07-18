from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.route_B_round03.runtime_common import FrozenMyoPSSampler, expected_frozen_sampler_counts


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_frozen_sampler_draw_cycle_and_counts() -> None:
    sampler = FrozenMyoPSSampler(Path("configs/route_B_round03/manifests/myops_sampler_strata.json"))
    labels = [sampler.draw(step)[0] for step in range(1, 13)]
    assert labels == ["E", "E", "S", "R"] * 3
    assert expected_frozen_sampler_counts(12) == {"E": 6, "S": 3, "R": 3}
    assert expected_frozen_sampler_counts(14) == {"E": 8, "S": 3, "R": 3}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str = "ok\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_packet_validator_rejects_unfaithful_b3_sampler(tmp_path: Path) -> None:
    route_root = tmp_path / "results/route_B"
    b3 = route_root / "round03/executors/B3"
    b10 = route_root / "round03/executors/B10"
    for name in ("completion_check.md", "result.md", "controller_report.md", "review_request.md", "MANIFEST.md"):
        _write_text(route_root / name, "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW\n")
    ledger = (
        "timestamp_utc,event,executor,stage,partition,job_id,state,exit_code,output_root,credit,lineage_note\n"
        "2026-07-18T00:00:00Z,slurm_submitted,B3,evidence_warmup,htzhulab,1,SUBMITTED,,out,pending,start\n"
        "2026-07-18T00:10:00Z,terminal_accounting,B3,evidence_warmup,htzhulab,1,FAILED,2:0,out,terminal_negative,done\n"
    )
    _write_text(route_root / "round03/controller_ledger.csv", ledger)
    _write_text(b10 / "routing_ledger.csv", ledger)
    _write_json(
        b3 / "completion.json",
        {
            "stage": "evidence_warmup",
            "status": "FAIL",
            "completion_token": "ROUTE_B_ROUND03_B3_SCIENTIFIC_GATE_FAILED",
            "optimizer_steps": 6000,
            "required_optimizer_steps": 6000,
            "train_loop_seconds": 1800.0,
            "required_train_loop_seconds": 1800.0,
            "validation_events": 3,
            "required_validation_events": 3,
            "sampler_counts": {"E": 100, "S": 200, "R": 5700},
        },
    )
    packet = {
        "status": "PASS",
        "completion_token": "ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW",
        "terminal_negative_packet": True,
        "blocked_at_stage": "B3",
        "blocked_completion_token": "ROUTE_B_ROUND03_B3_SCIENTIFIC_GATE_FAILED",
        "missing_stage_packets_justification": "B3 failed.",
        "missing_stage_packets": ["B4", "B5", "B6", "B7", "B8", "B9"],
        "nonpass_stage_packets": [],
        "heavy_artifact_scan": {"status": "PASS", "tracked_heavy_artifacts": []},
        "forbidden_actions": {"push": False},
        "validator_rows": [
            {"command": "git diff --check", "exit_code": 0},
            {"command": "python scripts/architecture/validate_care_architecture_wiki.py --strict", "exit_code": 0},
        ],
        "finalizer_dependency_coverage": {
            "dependency": "afterany_all_started_attempts",
            "covered_job_ids": ["1"],
        },
    }
    for name in (
        "finalizer_state.json",
        "completion.json",
        "validator_packet_report.json",
        "heavy_artifact_scan.json",
        "route_local_architecture_fingerprint.json",
    ):
        _write_json(b10 / name, {"status": "PASS", **packet} if name != "validator_packet_report.json" else {"status": "PASS"})
    for name in (
        "training_adequacy.csv",
        "metrics_summary.csv",
        "case_safety_matrix.csv",
        "help_harm_matrix.csv",
        "known_bad_selftest_report.md",
        "mapper_report_final.md",
    ):
        _write_text(b10 / name)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/validation/route_B_round03/validate_packet.py",
            "--strict",
            "--require-all-attempt-accounting",
            str(b10),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 1
    assert "b3_frozen_sampler_counts_mismatch" in proc.stdout
