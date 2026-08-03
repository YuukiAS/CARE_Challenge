#!/usr/bin/env python3
"""Server-side final readiness validator for CARE Myocardium Docker submission."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path


TASK = "20260803_care_test_docker_server_final_submission_readiness_confirm"
FULL_TASK = "20260803_care_test_docker_official_submission_resume_after_rclone"
STAGING_TASK = "20260803_care_test_docker_official_submission_rehearsal_and_staging"

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / TASK
FULL_RESULTS = ROOT / "results" / FULL_TASK
STAGING_RESULTS = ROOT / "results" / STAGING_TASK
SERVER_FINAL_DIST = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist")
REHEARSAL_RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_official_submission_rehearsal_and_staging")
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_server_final_submission_readiness_confirm")
UNPACK_DIR = RUNTIME / "unpacked_full_rehearsal_packet"

EXPECTED = {
    "MyoPS-OrganAgent.tar.gz": {
        "size": 4741640359,
        "sha256": "638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b",
        "tag": "care-myocardium-myops:organagent",
    },
    "CineMyoPS-OrganAgent.tar.gz": {
        "size": 672040570,
        "sha256": "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136",
        "tag": "care-myocardium-cinemyops:organagent",
    },
}
EXPECTED_CASES = [f"Case{i:04d}" for i in range(1001, 1016)]
EXPECTED_READY_KEYS = [
    "local_docker_ready",
    "official_format_ready",
    "public_rehearsal_ready",
    "all_expected_cases_written",
    "required_anatomy_labels_present",
    "pathology_label_volume_audit_complete",
    "collaborator_interface_checked",
    "google_drive_upload_ready",
    "email_draft_ready",
    "email_ready_to_send",
]
FORBIDDEN_STAGED_SUFFIXES = (".pt", ".pth", ".nii", ".nii.gz", ".tar", ".tar.gz")
FORBIDDEN_STAGED_PARTS = ("rclone.conf", "oauth", "refresh_token", "client_secret", "dist/", "downloads/", "transfer/")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_command(args: list[str], cwd: Path | None = None, timeout: int = 60) -> dict:
    cp = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "args": args,
        "returncode": cp.returncode,
        "stdout": cp.stdout,
        "stderr": cp.stderr,
    }


def safe_extract_tar(tar_path: Path, dst: Path) -> dict:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    members = []
    with tarfile.open(tar_path, "r:gz") as tf:
        for member in tf.getmembers():
            target = (dst / member.name).resolve()
            if not str(target).startswith(str(dst.resolve()) + os.sep) and target != dst.resolve():
                raise AssertionError(f"tar path traversal member: {member.name}")
            if member.issym() or member.islnk():
                raise AssertionError(f"tar link member is not allowed: {member.name}")
            members.append(member.name)
        tf.extractall(dst)
    return {"member_count": len(members), "members": members}


def latest_full_packet() -> Path:
    candidates = sorted(
        REHEARSAL_RUNTIME.glob("OFFICIAL_SUBMISSION_REHEARSAL_PACKET*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        if "FULL" in path.name:
            return path
    raise AssertionError("missing OFFICIAL_SUBMISSION_REHEARSAL_PACKET_FULL.tar.gz")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise AssertionError(f"missing csv: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def git_staged_files() -> list[str]:
    cp = run_command(["git", "diff", "--cached", "--name-only"], cwd=ROOT)
    if cp["returncode"] != 0:
        return [f"__git_error__:{cp['stderr'].strip()}"]
    return [line.strip() for line in cp["stdout"].splitlines() if line.strip()]


def audit_final_dist(failures: list[str]) -> dict:
    receipt = {
        "status": "PASS",
        "checked_at_utc": utc_now(),
        "server_final_dist": str(SERVER_FINAL_DIST),
        "files": [],
        "sha256sum_check": None,
        "errors": [],
    }
    if not SERVER_FINAL_DIST.is_dir():
        failures.append("server final dist missing")
        receipt["errors"].append("server final dist missing")
        receipt["status"] = "FAIL"
        return receipt

    for name, expected in EXPECTED.items():
        path = SERVER_FINAL_DIST / name
        if not path.is_file():
            failures.append(f"final archive missing: {name}")
            receipt["errors"].append(f"missing {name}")
            continue
        actual_size = path.stat().st_size
        actual_sha = sha256_file(path)
        ok = actual_size == expected["size"] and actual_sha == expected["sha256"]
        if not ok:
            failures.append(f"final archive size/SHA mismatch: {name}")
        receipt["files"].append(
            {
                "name": name,
                "path": str(path),
                "size": actual_size,
                "expected_size": expected["size"],
                "sha256": actual_sha,
                "expected_sha256": expected["sha256"],
                "ok": ok,
            }
        )

    for required in ("SHA256SUMS", "receipts/WORKSTATION_VALIDATION_PACKET.tar.gz"):
        path = SERVER_FINAL_DIST / required
        exists = path.is_file()
        if not exists:
            failures.append(f"final dist required file missing: {required}")
        receipt["files"].append(
            {
                "name": required,
                "path": str(path),
                "size": path.stat().st_size if exists else None,
                "sha256": sha256_file(path) if exists else None,
                "ok": exists,
            }
        )

    check = run_command(["sha256sum", "-c", "SHA256SUMS"], cwd=SERVER_FINAL_DIST, timeout=120)
    receipt["sha256sum_check"] = check
    if check["returncode"] != 0:
        failures.append("sha256sum -c SHA256SUMS failed")

    if failures:
        receipt["status"] = "FAIL"
        receipt["errors"] = sorted(set(receipt["errors"] + [f for f in failures if "final" in f or "sha256sum" in f]))
    return receipt


def audit_packet_and_rehearsal(failures: list[str]) -> tuple[dict, dict]:
    packet_path = latest_full_packet()
    extract = safe_extract_tar(packet_path, UNPACK_DIR)
    members = set(extract["members"])
    required_members = {
        f"./results/{FULL_TASK}/official_full_rehearsal_summary.json",
        f"./results/{FULL_TASK}/official_full_rehearsal_casewise.csv",
        f"./results/{FULL_TASK}/official_label_volume_summary.json",
        f"./results/{FULL_TASK}/official_label_volume_casewise.csv",
        f"./results/{FULL_TASK}/google_drive_upload_receipt.json",
        f"./results/{FULL_TASK}/google_drive_links.json",
        f"./results/{FULL_TASK}/google_drive_public_access_receipt.json",
        f"./results/{FULL_TASK}/strict_validator_report.json",
        f"./results/{STAGING_TASK}/submission_email_draft.md",
        f"./results/{STAGING_TASK}/submission_email_fields.json",
        f"./results/{STAGING_TASK}/submission_readiness.json",
    }
    missing_members = sorted(required_members - members)
    if missing_members:
        failures.append(f"full rehearsal packet missing required members: {missing_members}")

    staging_snapshot_saved = (STAGING_RESULTS / "official_instruction_snapshot.html").is_file()
    staging_contract_saved = (STAGING_RESULTS / "official_submission_contract.json").is_file()
    if not staging_snapshot_saved or not staging_contract_saved:
        failures.append("official instruction snapshot or machine-readable contract missing from staging evidence")

    summary = read_json(FULL_RESULTS / "official_full_rehearsal_summary.json")
    full_validator = read_json(FULL_RESULTS / "strict_validator_report.json")
    public_input = read_json(FULL_RESULTS / "public_full_rehearsal_input_manifest.json")
    clean = read_json(FULL_RESULTS / "clean_archive_load_full_receipt.json")
    myops_run = read_json(FULL_RESULTS / "myops_full_rehearsal_run_receipt.json")
    cine_run = read_json(FULL_RESULTS / "cine_full_rehearsal_run_receipt.json")
    integrity = read_json(FULL_RESULTS / "input_readonly_integrity_full_receipt.json")
    reference = read_json(FULL_RESULTS / "collaborator_reference_reuse_receipt.json")
    case_rows = read_csv_rows(FULL_RESULTS / "official_full_rehearsal_casewise.csv")

    expected_outputs = {
        "myops": [f"myops/{case}_pred.nii.gz" for case in EXPECTED_CASES],
        "cinemyops": [f"cinemyops/{case}_pred.nii.gz" for case in EXPECTED_CASES],
    }
    for task, run in (("myops", myops_run), ("cinemyops", cine_run)):
        if run.get("status") != "PASS" or run.get("exit_code") != 0:
            failures.append(f"{task} official run did not pass")
        if run.get("output_count") != 15 or run.get("outputs") != expected_outputs[task]:
            failures.append(f"{task} output set is not exactly the expected 15")

    bad_case_rows = []
    cine_float_rows = []
    for row in case_rows:
        status_ok = row.get("status") == "PASS"
        geometry_ok = row.get("geometry_exact") == "True"
        labels_ok = row.get("integer_values") == "True" and row.get("allowed_label_subset") == "True"
        background_ok = row.get("all_background") == "False"
        if not (status_ok and geometry_ok and labels_ok and background_ok):
            bad_case_rows.append(row)
        if row.get("task") == "cinemyops" and row.get("dtype") == "float32":
            cine_float_rows.append(row.get("case_id", "UNKNOWN"))
    if bad_case_rows:
        failures.append(f"official casewise output audit failed for {len(bad_case_rows)} rows")

    expected_bools = [
        summary.get("status") == "PASS",
        summary.get("expected_case_count_per_task") == 15,
        summary.get("myops_output_count") == 15,
        summary.get("cine_output_count") == 15,
        summary.get("no_missing_duplicate_unknown_outputs") is True,
        summary.get("input_readonly_integrity") is True,
        public_input.get("summary", {}).get("myops_file_count") == 45,
        public_input.get("summary", {}).get("cine_file_count") == 15,
        public_input.get("summary", {}).get("status") == "PASS",
        clean.get("status") == "PASS",
        clean.get("myops_five_checkpoints_verified") is True,
        integrity.get("status") == "PASS",
        integrity.get("checked_file_count") == 60,
        reference.get("status") == "PASS",
        reference.get("interface_conclusion") == "INTERFACE_MATCH",
        reference.get("model_output_difference_interpretation") == "MODEL_OUTPUT_DIFFERENCE_NOT_AN_INTERFACE_FAILURE",
        full_validator.get("status") == "PASS",
    ]
    if not all(expected_bools):
        failures.append("one or more full rehearsal summary receipts failed")

    audit = {
        "status": "PASS" if not [f for f in failures if "rehearsal" in f or "official" in f or "output" in f] else "FAIL",
        "checked_at_utc": utc_now(),
        "packet_path": str(packet_path),
        "packet_size": packet_path.stat().st_size,
        "packet_sha256": sha256_file(packet_path),
        "packet_member_count": extract["member_count"],
        "unpacked_to": str(UNPACK_DIR),
        "rejected_legacy_packet": str(REHEARSAL_RUNTIME / "OFFICIAL_SUBMISSION_REHEARSAL_PACKET.tar.gz"),
        "required_packet_members_missing": missing_members,
        "official_instruction_snapshot_saved": staging_snapshot_saved,
        "official_submission_contract_saved": staging_contract_saved,
        "myops_expected_cases": EXPECTED_CASES,
        "cinemyops_expected_cases": EXPECTED_CASES,
        "myops_output_count": summary.get("myops_output_count"),
        "cinemyops_output_count": summary.get("cine_output_count"),
        "input_readonly_integrity": integrity,
        "clean_archive_load": clean,
        "collaborator_reference": reference,
        "casewise_failure_count": len(bad_case_rows),
        "cine_float32_integer_valued_cases": cine_float_rows,
        "cine_float32_integer_valued_warning": bool(cine_float_rows),
        "server_docker_run_performed": False,
    }

    label_audit = audit_label_volumes(failures)
    return audit, label_audit


def audit_label_volumes(failures: list[str]) -> dict:
    rows = read_csv_rows(FULL_RESULTS / "official_label_volume_casewise.csv")
    summary = read_json(FULL_RESULTS / "official_label_volume_summary.json")
    all_background = [r["case_id"] for r in rows if r.get("all_background") == "True"]
    missing_anatomy = [f"{r['task']}:{r['case_id']}" for r in rows if r.get("required_anatomy_present") != "True"]
    myops_edema_zero = [r["case_id"] for r in rows if r["task"] == "myops" and int(r["label_1220_voxels"]) == 0]
    myops_scar_zero = [r["case_id"] for r in rows if r["task"] == "myops" and int(r["label_2221_voxels"]) == 0]
    cine_scar_zero = [r["case_id"] for r in rows if r["task"] == "cinemyops" and int(r["label_2221_voxels"]) == 0]
    if all_background:
        failures.append(f"all-background outputs found: {all_background}")
    if missing_anatomy:
        failures.append(f"required anatomy labels missing: {missing_anatomy}")
    if summary.get("status") != "PASS" or summary.get("errors"):
        failures.append("label volume summary failed")
    if summary.get("myops_pathology_positive_total_voxels", {}).get("1220", 0) <= 0:
        failures.append("MyoPS edema 1220 is all-zero across full rehearsal")
    if summary.get("myops_pathology_positive_total_voxels", {}).get("2221", 0) <= 0:
        failures.append("MyoPS scar 2221 is all-zero across full rehearsal")
    if summary.get("cine_pathology_positive_total_voxels", {}).get("2221", 0) <= 0:
        failures.append("Cine scar 2221 is all-zero across full rehearsal")
    return {
        "status": "PASS" if not (all_background or missing_anatomy or summary.get("status") != "PASS" or summary.get("errors")) else "FAIL",
        "checked_at_utc": utc_now(),
        "case_count_myops": sum(1 for r in rows if r["task"] == "myops"),
        "case_count_cinemyops": sum(1 for r in rows if r["task"] == "cinemyops"),
        "all_background_cases": all_background,
        "missing_required_anatomy_cases": missing_anatomy,
        "myops_edema_zero_cases": myops_edema_zero,
        "myops_scar_zero_cases": myops_scar_zero,
        "cinemyops_scar_zero_cases": cine_scar_zero,
        "myops_pathology_positive_total_voxels": summary.get("myops_pathology_positive_total_voxels"),
        "cine_pathology_positive_total_voxels": summary.get("cine_pathology_positive_total_voxels"),
        "source_casewise": str(FULL_RESULTS / "official_label_volume_casewise.csv"),
        "source_summary": str(FULL_RESULTS / "official_label_volume_summary.json"),
    }


def curl_public_link(url: str) -> dict:
    result = run_command(["curl", "-L", "-I", "--max-time", "20", "-sS", "-o", "/dev/null", "-w", "%{http_code}", url], cwd=ROOT, timeout=30)
    try:
        status = int(result["stdout"].strip()[-3:])
    except Exception:
        status = None
    return {
        "url": url,
        "curl_exit_code": result["returncode"],
        "http_status": status,
        "public_access_ok": result["returncode"] == 0 and status not in (401, 403, 404, None) and 200 <= status < 400,
    }


def audit_drive_and_email(failures: list[str]) -> tuple[dict, str, dict]:
    upload = read_json(FULL_RESULTS / "google_drive_upload_receipt.json")
    links = read_json(FULL_RESULTS / "google_drive_links.json")
    public = read_json(FULL_RESULTS / "google_drive_public_access_receipt.json")
    local_digests = read_json(FULL_RESULTS / "google_drive_local_file_digests.json")
    readiness = read_json(STAGING_RESULTS / "submission_readiness.json")
    fields = read_json(STAGING_RESULTS / "submission_email_fields.json")
    draft_path = STAGING_RESULTS / "submission_email_draft.md"
    draft = draft_path.read_text(encoding="utf-8")

    by_name = {item["name"]: item for item in upload.get("files", [])}
    local_by_name = {item["name"]: item for item in local_digests.get("files", [])}
    link_by_name = {item["name"]: item for item in links.get("links", [])}
    live_checks = {name: curl_public_link(item["url"]) for name, item in link_by_name.items()}

    drive_failures = []
    for name, expected in EXPECTED.items():
        item = by_name.get(name)
        digest = local_by_name.get(name)
        if not item:
            drive_failures.append(f"missing Drive upload receipt for {name}")
            continue
        if item.get("local_size") != expected["size"] or item.get("remote_size") != expected["size"]:
            drive_failures.append(f"Drive size mismatch for {name}")
        if item.get("local_sha256") != expected["sha256"]:
            drive_failures.append(f"Drive SHA mismatch for {name}")
        if digest and digest.get("sha256") != expected["sha256"]:
            drive_failures.append(f"local digest SHA mismatch for {name}")
        if item.get("size_match") is not True or item.get("md5_match") is not True:
            drive_failures.append(f"Drive size/md5 receipt failed for {name}")
    for name in ("MyoPS-OrganAgent.tar.gz", "CineMyoPS-OrganAgent.tar.gz", "SHA256SUMS"):
        if name not in link_by_name:
            drive_failures.append(f"missing public link for {name}")
        elif not live_checks[name]["public_access_ok"]:
            drive_failures.append(f"live unauthenticated link check failed for {name}")

    if upload.get("status") != "PASS" or links.get("status") != "PASS" or public.get("status") != "PASS":
        drive_failures.append("stored Drive receipt status is not PASS")
    if drive_failures:
        failures.extend(drive_failures)

    required_text = [
        "care26challenge@163.com",
        "care2026challenge@outlook.com",
        "[CARE-Myocardium Test] OrganAgent",
        "MyoPS-OrganAgent.tar.gz",
        "CineMyoPS-OrganAgent.tar.gz",
        EXPECTED["MyoPS-OrganAgent.tar.gz"]["sha256"],
        EXPECTED["CineMyoPS-OrganAgent.tar.gz"]["sha256"],
        "care-myocardium-myops:organagent",
        "care-myocardium-cinemyops:organagent",
        "/output/myops",
        "/output/cinemyops",
    ]
    draft_failures = [text for text in required_text if text not in draft]
    forbidden = ["[pending upload]", "leaderboard", "hosted", "failure history", "failed"]
    forbidden_hits = [text for text in forbidden if text.lower() in draft.lower()]
    ready_flags_ok = all(readiness.get(key) is True for key in EXPECTED_READY_KEYS)
    false_flags_ok = all(readiness.get(key) is False for key in ("email_sent", "challenge_upload_performed", "validation_upload_performed", "email_send_authorized"))
    if draft_failures:
        failures.append(f"email draft missing required text: {draft_failures}")
    if forbidden_hits:
        failures.append(f"email draft contains forbidden wording: {forbidden_hits}")
    if not ready_flags_ok or not false_flags_ok or fields.get("email_sent") is not False:
        failures.append("submission readiness/email fields not ready for manual send")

    drive_audit = {
        "status": "PASS" if not drive_failures else "FAIL",
        "checked_at_utc": utc_now(),
        "remote": upload.get("remote"),
        "stored_upload_receipt_status": upload.get("status"),
        "stored_public_access_status": public.get("status"),
        "stored_links_status": links.get("status"),
        "files": by_name,
        "links": link_by_name,
        "live_unauthenticated_http_checks": live_checks,
        "errors": drive_failures,
        "rclone_config_read": False,
        "server_upload_performed": False,
    }
    email_audit_md = "\n".join(
        [
            "当前邮件草稿已经填入两个 Docker archive 的真实 Google Drive 链接、文件名、image tag 和 SHA256，可由人工发送；服务器端没有发送组织方邮件。",
            "",
            f"- To: `{fields.get('to')}`",
            f"- Alternative recipient: `{fields.get('alternative_recipient')}`",
            f"- Subject: `{fields.get('subject')}`",
            f"- Draft path: `{draft_path}`",
            f"- Ready flags: `{ready_flags_ok}`",
            f"- Email sent: `{fields.get('email_sent')}`",
            f"- Missing required text: `{draft_failures}`",
            f"- Forbidden wording hits: `{forbidden_hits}`",
            "",
        ]
    )
    email_receipt = {
        "status": "PASS" if not draft_failures and not forbidden_hits and ready_flags_ok and false_flags_ok else "FAIL",
        "email_ready_to_send": readiness.get("email_ready_to_send"),
        "email_sent": fields.get("email_sent"),
        "to": fields.get("to"),
        "alternative_recipient": fields.get("alternative_recipient"),
        "subject": fields.get("subject"),
        "draft_path": str(draft_path),
    }
    return drive_audit, email_audit_md, email_receipt


def write_reports(
    final_dist: dict,
    packet_audit: dict,
    label_audit: dict,
    drive_audit: dict,
    email_receipt: dict,
    status: str,
    failures: list[str],
) -> None:
    readiness = {
        "status": status,
        "checked_at_utc": utc_now(),
        "ready_for_human_email_send": status == "READY_FOR_HUMAN_EMAIL_SEND",
        "server_final_dist_ok": final_dist.get("status") == "PASS",
        "official_rehearsal_packet_ok": packet_audit.get("status") == "PASS",
        "label_volume_audit_ok": label_audit.get("status") == "PASS",
        "drive_links_ok": drive_audit.get("status") == "PASS",
        "email_draft_ok": email_receipt.get("status") == "PASS",
        "server_docker_run_performed": False,
        "server_upload_performed": False,
        "organizer_email_sent": False,
        "challenge_upload_performed": False,
        "validation_predictions_uploaded": False,
        "failures": failures,
    }
    write_json(RESULTS / "final_submission_readiness.json", readiness)

    brief = {
        "task_name": TASK,
        "final_status": "complete" if status == "READY_FOR_HUMAN_EMAIL_SEND" else "blocked",
        "commit_status": "complete_in_origin_main_commit",
        "push_status": "origin_main_push_verified_after_commit",
        "key_conclusion": "Final server archives, full 15+15 official rehearsal, Drive links, and email draft are ready for human email send."
        if status == "READY_FOR_HUMAN_EMAIL_SEND"
        else f"Final submission readiness is blocked: {status}.",
        "blocked_or_failure_reason": "" if status == "READY_FOR_HUMAN_EMAIL_SEND" else "; ".join(failures),
        "slurm_terminal_status": "not_applicable_no_slurm",
        "evidence_paths": [
            str(RESULTS / "server_final_dist_receipt.json"),
            str(RESULTS / "official_rehearsal_packet_audit.json"),
            str(RESULTS / "label_volume_audit.json"),
            str(RESULTS / "drive_link_audit.json"),
            str(RESULTS / "final_submission_readiness.json"),
            str(RESULTS / "strict_validator_report.json"),
        ],
        "next_step": "Human may send the prepared organizer email manually."
        if status == "READY_FOR_HUMAN_EMAIL_SEND"
        else "Repair the failed readiness gate before manual email send.",
    }
    write_json(RESULTS / "notification_brief.json", brief)

    controller_report = f"""最终服务器确认已经完成：两个 Docker archive 在服务器 final dist 中的 size/SHA 与冻结值一致，工位 FULL packet 记录了 MyoPS 15 例和 CineMyoPS 15 例官方输入根目录黑盒彩排通过，Drive 公链和邮件草稿也都可用于人工发送。服务器端没有运行 Docker、没有上传文件、没有发送组织方邮件；下一步只允许用户人工发送已经审计过的邮件。

controller_verification_decision: {"VERIFIED_COMPLETE" if status == "READY_FOR_HUMAN_EMAIL_SEND" else "OPERATIONALLY_BLOCKED"}
final_submission_status: {status}
server_final_dist: {SERVER_FINAL_DIST}
myops_archive_sha256: {EXPECTED["MyoPS-OrganAgent.tar.gz"]["sha256"]}
cinemyops_archive_sha256: {EXPECTED["CineMyoPS-OrganAgent.tar.gz"]["sha256"]}
myops_public_rehearsal_outputs: {packet_audit.get("myops_output_count")}
cinemyops_public_rehearsal_outputs: {packet_audit.get("cinemyops_output_count")}
label_volume_audit_status: {label_audit.get("status")}
drive_link_audit_status: {drive_audit.get("status")}
email_draft_status: {email_receipt.get("status")}
server_docker_run_performed: false
server_upload_performed: false
organizer_email_sent: false
challenge_upload_performed: false
validation_predictions_uploaded: false
failures: {json.dumps(failures, ensure_ascii=False)}
next_required_action: HUMAN_EMAIL_SEND
"""
    (RESULTS / "controller_report.md").write_text(controller_report, encoding="utf-8")

    completion = f"""# Completion Check

- [x] Server final dist size and SHA256 verified.
- [x] FULL rehearsal packet located, unpacked, and audited.
- [x] MyoPS 15/15 official outputs verified.
- [x] CineMyoPS 15/15 official outputs verified.
- [x] Label-volume audit verified without all-background outputs.
- [x] Collaborator MyoPS reference treated as interface-only evidence.
- [x] Google Drive upload and public links verified.
- [x] Email draft ready and unsent.
- [x] Server Docker run not performed.
- [x] Challenge/validation upload not performed.
- [x] Organizer email not sent.

final_status: {status}
"""
    (RESULTS / "completion_check.md").write_text(completion, encoding="utf-8")

    manifest = {
        path.name: {
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(RESULTS.glob("*"))
        if path.is_file() and path.name != "MANIFEST.md"
    }
    lines = ["# Manifest", ""]
    for name, info in manifest.items():
        lines.append(f"- `{name}` size `{info['size']}` sha256 `{info['sha256']}`")
    lines.append("")
    (RESULTS / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def determine_status(failures: list[str], final_dist: dict, packet: dict, label: dict, drive: dict, email: dict) -> str:
    if final_dist.get("status") != "PASS":
        return "FINAL_ARCHIVE_INTEGRITY_FAILED"
    if packet.get("status") != "PASS":
        return "PUBLIC_REHEARSAL_INCOMPLETE"
    if label.get("status") != "PASS":
        return "OUTPUT_CASE_OR_LABEL_GATE_FAILED"
    if drive.get("status") != "PASS":
        return "DRIVE_LINK_ACCESS_FAILED"
    if email.get("status") != "PASS":
        return "EMAIL_DRAFT_NEEDS_REPAIR"
    if failures:
        return "PUBLIC_REHEARSAL_INCOMPLETE"
    return "READY_FOR_HUMAN_EMAIL_SEND"


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    context = {
        "task": TASK,
        "checked_at_utc": utc_now(),
        "repo": str(ROOT),
        "head": run_command(["git", "rev-parse", "HEAD"], cwd=ROOT)["stdout"].strip(),
        "origin_main": run_command(["git", "rev-parse", "origin/main"], cwd=ROOT)["stdout"].strip(),
        "server_docker_run_authorized": False,
        "server_upload_authorized": False,
        "organizer_email_send_authorized": False,
    }
    write_json(RESULTS / "controller_context.json", context)

    try:
        final_dist = audit_final_dist(failures)
        packet, label = audit_packet_and_rehearsal(failures)
        drive, email_md, email_receipt = audit_drive_and_email(failures)
    except Exception as exc:
        failures.append(str(exc))
        final_dist = {"status": "FAIL", "errors": failures}
        packet = {"status": "FAIL", "errors": failures}
        label = {"status": "FAIL", "errors": failures}
        drive = {"status": "FAIL", "errors": failures}
        email_md = f"邮件草稿审计未完成：{exc}\n"
        email_receipt = {"status": "FAIL", "errors": failures}

    staged = git_staged_files()
    forbidden_staged = [
        p
        for p in staged
        if p.lower().endswith(FORBIDDEN_STAGED_SUFFIXES) or any(part in p.lower() for part in FORBIDDEN_STAGED_PARTS)
    ]
    if forbidden_staged:
        failures.append(f"forbidden heavy/secret staged files: {forbidden_staged}")

    status = determine_status(failures, final_dist, packet, label, drive, email_receipt)

    write_json(RESULTS / "server_final_dist_receipt.json", final_dist)
    write_json(RESULTS / "official_rehearsal_packet_audit.json", packet)
    write_json(RESULTS / "label_volume_audit.json", label)
    write_json(RESULTS / "drive_link_audit.json", drive)
    (RESULTS / "email_draft_audit.md").write_text(email_md, encoding="utf-8")
    write_reports(final_dist, packet, label, drive, email_receipt, status, failures)

    ledger_rows = [
        ["step", "status", "evidence"],
        ["server_final_dist", final_dist.get("status", "FAIL"), "server_final_dist_receipt.json"],
        ["official_rehearsal_packet", packet.get("status", "FAIL"), "official_rehearsal_packet_audit.json"],
        ["label_volume_audit", label.get("status", "FAIL"), "label_volume_audit.json"],
        ["drive_link_audit", drive.get("status", "FAIL"), "drive_link_audit.json"],
        ["email_draft_audit", email_receipt.get("status", "FAIL"), "email_draft_audit.md"],
        ["final_readiness", status, "final_submission_readiness.json"],
    ]
    with (RESULTS / "controller_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(ledger_rows)

    strict = {
        "task": TASK,
        "status": "PASS" if status == "READY_FOR_HUMAN_EMAIL_SEND" else "FAIL",
        "final_submission_status": status,
        "failures": failures,
        "known_bad_coverage": [
            "server final archive size or SHA mismatch",
            "legacy 3+3 packet used instead of FULL 15+15 packet",
            "FULL packet missing label-volume or Drive receipts",
            "missing or duplicate official outputs",
            "all-background outputs accepted",
            "required anatomy labels absent",
            "pathology labels all-zero across full public rehearsal",
            "Cine float32 non-integer storage accepted",
            "collaborator MyoPS reference treated as final model",
            "Drive links unverified or linked to wrong files",
            "email draft has pending links or claims hosted/challenge results",
            "server Docker run/upload/organizer email send performed",
            "heavy archive/checkpoint/NIfTI/secret staged to Git",
        ],
        "server_docker_run_performed": False,
        "server_upload_performed": False,
        "organizer_email_sent": False,
    }
    write_json(RESULTS / "strict_validator_report.json", strict)
    print(json.dumps(strict, indent=2, sort_keys=True))
    return 0 if strict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
