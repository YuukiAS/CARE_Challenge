from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python"


def test_b0_validator_report_passes_current_packet() -> None:
    report = REPO_ROOT / "results/route_B/round04/executors/B0/validator_report.json"
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"


def test_b0_known_bad_matrix_passes() -> None:
    report = REPO_ROOT / "results/route_B/round04/executors/B0/known_bad_matrix_report.json"
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["fixture_count"] == 13


def test_b2_validator_report_passes_current_packet() -> None:
    report = REPO_ROOT / "results/route_B/round04/executors/B2/validator_report.json"
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"


def test_b3_formal_refuses_reduced_budget(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/training/route_B_round04/myops/B3/run_B3_representation.py",
            "--manifest",
            "configs/route_B_round04/manifests/myops_fold0_primary_44.json",
            "--b2",
            "results/route_B/round04/executors/B2",
            "--out",
            str(tmp_path / "B3"),
            "--steps",
            "1",
            "--min-train-seconds",
            "0",
            "--formal",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "B3 formal run cannot reduce planned minimum training budget" in proc.stderr


def test_b7_formal_refuses_reduced_budget(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/training/route_B_round04/cine/B7/run_B7_cinema_control.py",
            "--manifest",
            "configs/route_B_round04/manifests/cine_train12.json",
            "--b2",
            "results/route_B/round04/executors/B2",
            "--out",
            str(tmp_path / "B7"),
            "--steps-per-source",
            "1",
            "--min-train-seconds-per-source",
            "0",
            "--formal",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "B7 formal run cannot reduce planned minimum training budget" in proc.stderr


def test_b4_formal_refuses_reduced_budget(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/training/route_B_round04/myops/B4/run_B4_proposal.py",
            "--manifest",
            "configs/route_B_round04/manifests/myops_fold0_primary_44.json",
            "--b3",
            "results/route_B/round04/executors/B3",
            "--b0",
            "results/route_B/round04/executors/B0",
            "--out",
            str(tmp_path / "B4"),
            "--steps",
            "1",
            "--min-train-seconds",
            "0",
            "--formal",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "B4 formal run cannot reduce planned minimum training budget" in proc.stderr


def test_b5_formal_refuses_reduced_budget(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/training/route_B_round04/myops/B5/run_B5_refiner.py",
            "--b4",
            "results/route_B/round04/executors/B4",
            "--out",
            str(tmp_path / "B5"),
            "--steps",
            "1",
            "--min-train-seconds",
            "0",
            "--formal",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "B5 formal run cannot reduce planned minimum training budget" in proc.stderr


def test_b8_formal_refuses_reduced_budget(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/training/route_B_round04/cine/B8/run_B8_registration.py",
            "--manifest",
            "configs/route_B_round04/manifests/cine_train12.json",
            "--b7",
            "results/route_B/round04/executors/B7",
            "--out",
            str(tmp_path / "B8"),
            "--steps",
            "1",
            "--min-train-seconds",
            "0",
            "--validation-events",
            "1",
            "--formal",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "B8 formal run cannot reduce planned minimum training budget" in proc.stderr


def test_b6_formal_refuses_reduced_budget(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/training/route_B_round04/myops/B6/run_B6_joint.py",
            "--manifest",
            "configs/route_B_round04/manifests/myops_fold0_primary_44.json",
            "--b5",
            "results/route_B/round04/executors/B5",
            "--b0",
            "results/route_B/round04/executors/B0",
            "--out",
            str(tmp_path / "B6"),
            "--steps",
            "1",
            "--min-train-seconds",
            "0",
            "--validation-events",
            "1",
            "--formal",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode != 0
    assert "B6 formal run cannot reduce planned minimum training budget" in proc.stderr


def test_b10_validator_rejects_file_existence_only_packet(tmp_path: Path) -> None:
    packet = tmp_path / "B10"
    packet.mkdir()
    terminal_accounting = [
        {"job_id": "59546347", "state": "FAILED", "terminal_accounted": True},
        {"job_id": "59546548", "state": "CANCELLED by 397557", "terminal_accounted": True},
        {"job_id": "59548314", "state": "CANCELLED by 397557", "terminal_accounted": True},
        {"job_id": "59568601", "state": "COMPLETED", "terminal_accounted": True},
    ]
    branch = {
        "early_terminal_branches_reachable": True,
        "b1_failure_finalizer_launch_covered": True,
        "b2_external_blocker_finalizer_launch_covered": True,
        "b7_blocker_finalizer_launch_covered": True,
        "b8_registration_blocker_finalizer_launch_covered": True,
        "b6_terminal_accounted": True,
        "b9_absence_justified": True,
        "cine_lane_terminal_class": "B8_CINE_REGISTRATION_BLOCKER_NO_B9",
    }
    (packet / "routing_ledger.csv").write_text("phase\nB10\n", encoding="utf-8")
    (packet / "training_adequacy.csv").write_text(
        "stage,status\n"
        "B0,PASS\nB1,PASS\nB2,PASS\nB3,PASS\nB4,PASS\nB5,PASS\nB6,PASS\nB7,PASS\nB8,PASS\nB9,SKIPPED_DUE_B8_REGISTRATION_BLOCKER\n",
        encoding="utf-8",
    )
    for name, payload in {
        "terminal_branch_coverage.json": branch,
        "validator_packet_report.json": {"status": "PASS", "semantic_checks_performed": False, "only_file_existence": True},
        "known_bad_report.json": {"status": "PASS"},
        "heavy_artifact_scan.json": {"status": "PASS", "tracked_heavy_artifacts": []},
        "terminal_registry_snapshot.json": {"terminal_accounting": terminal_accounting, "superseded_attempts_reconciled": True},
        "root_packet_manifest.json": {name: {"present": True} for name in ["result.md", "controller_report.md", "completion_check.md", "review_request.md", "MANIFEST.md"]},
    }.items():
        (packet / name).write_text(json.dumps(payload), encoding="utf-8")
    state = {
        "status": "PASS",
        "completion_token": "ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW",
        "aggregation_command_exit_code": 0,
        "finalizer_dependency_coverage": {
            "dependency": "afterany_all_started_attempts",
            "covered_job_ids": [row["job_id"] for row in terminal_accounting],
        },
        "forbidden_actions": {"push": False, "review_md_written_by_controller": False},
    }
    (packet / "finalizer_state.json").write_text(json.dumps(state), encoding="utf-8")
    (packet / "completion.json").write_text(json.dumps({"status": "PASS", "completion_token": "ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW"}), encoding="utf-8")
    proc = subprocess.run(
        [
            PYTHON,
            "scripts/validation/route_B_round04/validate_B10_terminal_packet.py",
            "--strict",
            "--input",
            str(packet),
            "--report",
            str(packet / "validator_report.json"),
            "--require-token",
            "ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 1
    report = json.loads((packet / "validator_report.json").read_text(encoding="utf-8"))
    assert "VALIDATOR_FILE_EXISTENCE_ONLY" in report["failure_keys"]
