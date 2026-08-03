#!/usr/bin/env python3
"""Strict validator for the post-rclone full CARE Docker submission rehearsal."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


TASK = "20260803_care_test_docker_official_submission_resume_after_rclone"
STAGING_TASK = "20260803_care_test_docker_official_submission_rehearsal_and_staging"
ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / TASK
STAGING_RESULTS = ROOT / "results" / STAGING_TASK
FINAL_DIST = ROOT / "dist" / "20260803_care_test_docker_final"

EXPECTED_CASES = [f"Case{i:04d}" for i in range(1001, 1016)]
EXPECTED_MYOPS_SHA = "638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b"
EXPECTED_CINE_SHA = "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136"

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
    "only 3+3 public rehearsal marked as full 15+15",
    "15 inputs downloaded but fewer than 15 outputs written",
    "missing, duplicate, or unknown public validation case ID",
    "output path not /output/myops/<CaseID>_pred.nii.gz or /output/cinemyops/<CaseID>_pred.nii.gz",
    "MyoPS anatomy labels 200/500/600 absent in any case",
    "Cine anatomy labels 200/500 absent in any case",
    "all-background output accepted",
    "MyoPS pathology labels 1220/2221 absent across all 15 cases",
    "Cine pathology label 2221 absent across all 15 cases",
    "Cine float dtype with non-integer label values accepted",
    "array labels checked but geometry mismatch ignored",
    "input archive/output predictions uploaded to Google Drive",
    "Google Drive size/hash not verified",
    "public links created but not checked unauthenticated",
    "email draft still contains [pending upload]",
    "email ready while download links are unverified",
    "organizer email sent by automation",
    "challenge or validation predictions uploaded",
    "rclone.conf, OAuth token, Docker archive, checkpoint, or NIfTI staged to Git",
]


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fail_unless(condition: bool, message: str, failures: list[str]) -> None:
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


def check_full_rehearsal(failures: list[str]) -> None:
    input_manifest = load_json(RESULTS / "public_full_rehearsal_input_manifest.json")
    myops_run = load_json(RESULTS / "myops_full_rehearsal_run_receipt.json")
    cine_run = load_json(RESULTS / "cine_full_rehearsal_run_receipt.json")
    summary = load_json(RESULTS / "official_full_rehearsal_summary.json")
    label_summary = load_json(RESULTS / "official_label_volume_summary.json")
    integrity = load_json(RESULTS / "input_readonly_integrity_full_receipt.json")
    clean = load_json(RESULTS / "clean_archive_load_full_receipt.json")
    reference = load_json(RESULTS / "collaborator_reference_reuse_receipt.json")

    fail_unless(input_manifest["summary"].get("status") == "PASS", "input manifest failed", failures)
    fail_unless(input_manifest["summary"].get("myops_file_count") == 45, "MyoPS input file count is not 45", failures)
    fail_unless(input_manifest["summary"].get("cine_file_count") == 15, "Cine input file count is not 15", failures)

    for task, run in (("myops", myops_run), ("cinemyops", cine_run)):
        fail_unless(run.get("status") == "PASS" and run.get("exit_code") == 0, f"{task} run failed", failures)
        fail_unless(run.get("output_count") == 15, f"{task} output count is not 15", failures)
        expected_outputs = [f"{task}/{case}_pred.nii.gz" for case in EXPECTED_CASES]
        fail_unless(run.get("outputs") == expected_outputs, f"{task} output list is not the expected 15 cases", failures)

    fail_unless(summary.get("status") == "PASS", "full rehearsal summary failed", failures)
    fail_unless(summary.get("myops_output_count") == 15, "summary MyoPS output count is not 15", failures)
    fail_unless(summary.get("cine_output_count") == 15, "summary Cine output count is not 15", failures)
    fail_unless(summary.get("no_missing_duplicate_unknown_outputs") is True, "missing/duplicate/unknown output check failed", failures)
    fail_unless(summary.get("input_readonly_integrity") is True, "input readonly integrity flag failed", failures)
    fail_unless(summary.get("errors") == [], "full rehearsal summary has errors", failures)

    fail_unless(label_summary.get("status") == "PASS", "label volume audit failed", failures)
    fail_unless(label_summary.get("errors") == [], "label volume audit has errors", failures)
    fail_unless(label_summary.get("myops_pathology_positive_total_voxels", {}).get("1220", 0) > 0, "MyoPS label 1220 absent across 15 cases", failures)
    fail_unless(label_summary.get("myops_pathology_positive_total_voxels", {}).get("2221", 0) > 0, "MyoPS label 2221 absent across 15 cases", failures)
    fail_unless(label_summary.get("cine_pathology_positive_total_voxels", {}).get("2221", 0) > 0, "Cine label 2221 absent across 15 cases", failures)

    fail_unless(integrity.get("status") == "PASS" and integrity.get("checked_file_count") == 60, "input integrity receipt did not check all 60 files", failures)
    fail_unless(clean.get("status") == "PASS", "clean archive load receipt failed", failures)
    fail_unless(clean.get("myops_five_checkpoints_verified") is True, "MyoPS five checkpoint receipt missing", failures)
    for image in clean.get("images", []):
        fail_unless(image.get("os") == "linux" and image.get("architecture") == "amd64", f"image not linux/amd64: {image}", failures)
        fail_unless(bool(image.get("entrypoint")), f"image entrypoint empty: {image}", failures)
    fail_unless(reference.get("status") == "PASS", "collaborator reference reuse receipt failed", failures)
    fail_unless(reference.get("interface_conclusion") == "INTERFACE_MATCH", "collaborator interface was not matched", failures)


def check_drive_and_email(failures: list[str]) -> None:
    upload = load_json(RESULTS / "google_drive_upload_receipt.json")
    links = load_json(RESULTS / "google_drive_links.json")
    public = load_json(RESULTS / "google_drive_public_access_receipt.json")
    readiness = load_json(STAGING_RESULTS / "submission_readiness.json")
    fields = load_json(STAGING_RESULTS / "submission_email_fields.json")
    draft = (STAGING_RESULTS / "submission_email_draft.md").read_text(encoding="utf-8")

    fail_unless(upload.get("status") == "PASS", "Google Drive upload receipt failed", failures)
    by_name = {item["name"]: item for item in upload.get("files", [])}
    fail_unless(by_name.get("MyoPS-OrganAgent.tar.gz", {}).get("local_sha256") == EXPECTED_MYOPS_SHA, "MyoPS SHA mismatch in Drive receipt", failures)
    fail_unless(by_name.get("CineMyoPS-OrganAgent.tar.gz", {}).get("local_sha256") == EXPECTED_CINE_SHA, "Cine SHA mismatch in Drive receipt", failures)
    for name in ("MyoPS-OrganAgent.tar.gz", "CineMyoPS-OrganAgent.tar.gz", "SHA256SUMS"):
        item = by_name.get(name, {})
        fail_unless(item.get("size_match") is True and item.get("md5_match") is True, f"Drive size/hash mismatch for {name}", failures)

    fail_unless(links.get("status") == "PASS", "Google Drive links receipt failed", failures)
    fail_unless(len(links.get("links", [])) == 3, "not exactly three Drive links", failures)
    fail_unless(public.get("status") == "PASS" and public.get("unauthenticated") is True, "public unauthenticated access check failed", failures)
    for check in public.get("checks", []):
        fail_unless(check.get("public_access_ok") is True, f"public access failed for {check.get('name')}", failures)

    fail_unless("[pending upload]" not in draft, "email draft still contains pending placeholder", failures)
    fail_unless("https://drive.google.com/" in draft, "email draft lacks Drive links", failures)
    fail_unless(readiness.get("public_rehearsal_case_count_myops") == 15, "readiness MyoPS case count is not 15", failures)
    fail_unless(readiness.get("public_rehearsal_case_count_cinemyops") == 15, "readiness Cine case count is not 15", failures)
    for key in (
        "local_docker_ready",
        "official_format_ready",
        "public_rehearsal_ready",
        "all_expected_cases_written",
        "required_anatomy_labels_present",
        "pathology_label_volume_audit_complete",
        "collaborator_interface_checked",
        "google_drive_upload_ready",
        "google_drive_remote_size_hash_verified",
        "google_drive_public_links_verified",
        "email_draft_ready",
        "email_ready_to_send",
    ):
        fail_unless(readiness.get(key) is True, f"readiness {key} is not true", failures)
    for key in ("email_sent", "challenge_upload_performed", "validation_upload_performed", "email_send_authorized"):
        fail_unless(readiness.get(key) is False, f"readiness {key} is not false", failures)
    fail_unless(fields.get("email_sent") is False and fields.get("download_links_verified") is True, "email fields are inconsistent", failures)


def check_archives_packet_and_git(failures: list[str]) -> None:
    packet = load_json(RESULTS / "full_rehearsal_packet_receipt.json")
    remote = load_json(RESULTS / "remote_full_rehearsal_packet_receipt.json")
    fail_unless(packet.get("status") == "PASS", "full rehearsal packet receipt failed", failures)
    fail_unless(remote.get("status") == "PASS", "remote full rehearsal packet receipt failed", failures)
    fail_unless((FINAL_DIST / "MyoPS-OrganAgent.tar.gz").is_file(), "local MyoPS archive missing", failures)
    fail_unless((FINAL_DIST / "CineMyoPS-OrganAgent.tar.gz").is_file(), "local Cine archive missing", failures)

    staged = git_staged_files()
    for path in staged:
        lower = path.lower()
        if lower.endswith(FORBIDDEN_STAGED_SUFFIXES) or any(part in path for part in FORBIDDEN_STAGED_PARTS):
            failures.append(f"forbidden staged artifact: {path}")


def main() -> int:
    failures: list[str] = []
    try:
        check_full_rehearsal(failures)
        check_drive_and_email(failures)
        check_archives_packet_and_git(failures)
    except AssertionError as exc:
        failures.append(str(exc))

    report = {
        "task": TASK,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "known_bad_coverage": KNOWN_BAD_COVERAGE,
        "challenge_upload_performed": False,
        "validation_predictions_uploaded": False,
        "email_sent": False,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "strict_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
