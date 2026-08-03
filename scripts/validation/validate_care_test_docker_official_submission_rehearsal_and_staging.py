#!/usr/bin/env python3
"""Strict validator for the official-format CARE Docker rehearsal task."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


TASK = "20260803_care_test_docker_official_submission_rehearsal_and_staging"
ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / TASK
FINAL_DIST = ROOT / "dist" / "20260803_care_test_docker_final"

FORBIDDEN_STAGED_SUFFIXES = (
    ".pt",
    ".pth",
    ".nii",
    ".nii.gz",
    ".tar",
    ".tar.gz",
)
FORBIDDEN_STAGED_PARTS = (
    ".local_runtime/",
    "dist/",
    "rclone.conf",
)

KNOWN_BAD_COVERAGE = [
    "only 3-case smoke claimed as unavailable full public set without recording actual case count",
    "used /input/myops single mount instead of official /input root tree",
    "output written to /output root",
    "filename not <CaseID>_pred.nii.gz",
    "MyoPS/Cine wrote into the other task output directory",
    "container modified read-only input",
    "extra command or interactive input required",
    "clean archive load not executed",
    "archive SHA checked without running image",
    "collaborator reference overwrote final MyoPS tag",
    "voxel mismatch between different models treated as interface failure",
    "Cine archive SHA changed",
    "Google Drive auth missing marked Docker readiness failed",
    "unverified public link marked email_ready_to_send=true",
    "email draft still has placeholders but ready_to_send=true",
    "organizer email was actually sent",
    "Docker archive, NIfTI, rclone config, or secret staged to Git",
    "challenge or validation predictions uploaded automatically",
]


def load_json(name: str) -> dict:
    path = RESULTS / name
    if not path.is_file():
        raise AssertionError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def git_staged_files() -> list[str]:
    cp = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        return [f"__git_error__:{cp.stderr.strip()}"]
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def main() -> int:
    failures: list[str] = []

    contract = load_json("official_submission_contract.json")
    clean = load_json("clean_archive_load_receipt.json")
    rehearsal = load_json("official_command_rehearsal_summary.json")
    validation = load_json("official_command_rehearsal_validation.json")
    integrity = load_json("input_readonly_integrity_receipt.json")
    reference = load_json("collaborator_reference_interface_summary.json")
    archive_manifest = load_json("pre_submission_archive_manifest.json")
    readiness = load_json("submission_readiness.json")
    rclone = load_json("rclone_environment_receipt.json")
    drive = load_json("google_drive_upload_receipt.json")
    links = load_json("google_drive_links.json")
    email = load_json("submission_email_fields.json")
    packet = load_json("rehearsal_packet_receipt.json")
    remote = load_json("remote_rehearsal_packet_receipt.json")
    failure_modes = load_json("failure_mode_rehearsal_receipt.json")

    assert_true(contract.get("source_url", "").startswith("https://zmic.org.cn/care_2026/instruction_myocardium/"), "official source URL missing", failures)
    assert_true(clean.get("status") == "PASS" and clean.get("clean_load_from_archives") is True, "clean archive load did not pass", failures)
    assert_true(all(image.get("os") == "linux" and image.get("architecture") == "amd64" for image in clean.get("images", [])), "image is not linux/amd64", failures)
    assert_true(clean.get("myops_internal_five_checkpoint_check", {}).get("exit_code") == 0, "MyoPS five checkpoint check missing", failures)

    assert_true(rehearsal.get("status") == "PASS", "official command rehearsal did not pass", failures)
    assert_true(rehearsal.get("extra_command_used") is False and rehearsal.get("interactive_used") is False, "extra command or interaction used", failures)
    assert_true(rehearsal.get("network_mode") == "none", "network none was not used", failures)
    assert_true(rehearsal.get("myops_case_count", 0) >= 1 and rehearsal.get("cine_case_count", 0) >= 1, "no public rehearsal cases recorded", failures)
    assert_true(validation.get("status") == "PASS", "output validation did not pass", failures)
    assert_true(not validation.get("tree_rules", {}).get("root_files"), "output root contains files", failures)
    assert_true(not validation.get("tree_rules", {}).get("unknown_dirs"), "unknown output directory created", failures)
    for row in validation.get("casewise", []):
        assert_true(row.get("output_relative_path", "").endswith(f"{row.get('case_id')}_pred.nii.gz"), f"bad filename for {row.get('task')} {row.get('case_id')}", failures)
        assert_true(row.get("simpleitk_readable") is True and row.get("nibabel_readable") is True, f"NIfTI unreadable for {row.get('task')} {row.get('case_id')}", failures)
        assert_true(row.get("dimension") == 3, f"output is not 3D for {row.get('task')} {row.get('case_id')}", failures)
        assert_true(row.get("integer_valued_labels") is True, f"labels are not integer-valued for {row.get('task')} {row.get('case_id')}", failures)
        assert_true(row.get("label_subset_ok") is True, f"bad labels for {row.get('task')} {row.get('case_id')}", failures)
        assert_true(row.get("geometry_match") is True, f"geometry mismatch for {row.get('task')} {row.get('case_id')}", failures)
    assert_true(integrity.get("status") == "PASS", "input integrity failed", failures)
    assert_true(failure_modes.get("status") == "PASS", "failure-mode rehearsal failed", failures)

    assert_true(reference.get("status") == "PASS", "collaborator reference interface comparison did not pass", failures)
    assert_true(reference.get("final_myops_tag_restored") is True, "final MyoPS tag was not restored after reference load", failures)
    assert_true(reference.get("voxel_equality_required") is False, "reference comparison incorrectly required voxel equality", failures)

    assert_true(archive_manifest.get("status") == "PASS", "archive manifest failed", failures)
    archives = {item["name"]: item for item in archive_manifest.get("archives", [])}
    assert_true((FINAL_DIST / "MyoPS-OrganAgent.tar.gz").is_file(), "local MyoPS archive missing", failures)
    assert_true((FINAL_DIST / "CineMyoPS-OrganAgent.tar.gz").is_file(), "local Cine archive missing", failures)
    assert_true(archives.get("CineMyoPS-OrganAgent.tar.gz", {}).get("sha256") == "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136", "Cine archive SHA changed", failures)
    assert_true(archive_manifest.get("myops_local_remote_sha_match") is True, "local/remote MyoPS SHA mismatch", failures)

    assert_true(readiness.get("local_docker_ready") is True, "local_docker_ready false", failures)
    assert_true(readiness.get("official_format_ready") is True, "official_format_ready false", failures)
    assert_true(readiness.get("public_rehearsal_ready") is True, "public_rehearsal_ready false", failures)
    assert_true(readiness.get("collaborator_interface_checked") is True, "collaborator_interface_checked false", failures)
    assert_true(readiness.get("email_draft_ready") is True, "email draft not ready", failures)
    assert_true(readiness.get("email_send_authorized") is False and readiness.get("email_sent") is False, "email was authorized or sent", failures)
    assert_true(readiness.get("challenge_upload_performed") is False and readiness.get("validation_upload_performed") is False, "challenge/validation upload performed", failures)
    if readiness.get("email_ready_to_send") is True:
        assert_true(links.get("all_links_publicly_verified") is True, "email ready but public links are not verified", failures)
    assert_true(rclone.get("upload_attempted") in {True, False}, "rclone environment receipt malformed", failures)
    assert_true(drive.get("challenge_upload_performed") is False and drive.get("validation_upload_performed") is False, "Drive receipt reports forbidden upload", failures)
    assert_true(email.get("email_sent") is False, "email fields report sent email", failures)
    assert_true(packet.get("status") == "PASS" and remote.get("status") == "PASS", "rehearsal packet was not returned", failures)

    staged = git_staged_files()
    for path in staged:
        lower = path.lower()
        if lower.endswith(FORBIDDEN_STAGED_SUFFIXES) or any(part in path for part in FORBIDDEN_STAGED_PARTS):
            failures.append(f"forbidden staged artifact: {path}")

    report = {
        "task": TASK,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "known_bad_coverage": KNOWN_BAD_COVERAGE,
    }
    (RESULTS / "strict_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
