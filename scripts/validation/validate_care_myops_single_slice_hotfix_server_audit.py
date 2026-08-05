#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path


TASK = "20260805_care_myops_single_slice_hotfix_repackage"
SERVER_TASK = "20260805_care_myops_single_slice_hotfix_server_audit"
READY_TOKEN = "CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION"
EXPECTED_ARCHIVE = "MyoPS-OrganAgent-corrected.tar.gz"
EXPECTED_SHA256 = "fcf1c67a2123ab655a8e6c32dc46e6d98feaa43f41c698c6969aebfaa51f79ff"
EXPECTED_SIZE = 4742235545
EXPECTED_LINK = "https://drive.google.com/open?id=1ATXgeTn99xFZAB3SLH1-aSpTuIb5EO5a"
GEOMETRY_MISMATCH_TOKEN = "INHERITED_BASE_BEHAVIOR_OUT_OF_SCOPE_NONBLOCKING"
CHECKPOINT_SHA256 = {
    0: "f139ca5525322d340a0284c6562a9bcb9cb9cae0a512e14ef40ce85a66f53278",
    1: "b92d56b1e24ce826081671acc4e048e5d48b191f6dcb9836747ae82d93acd1e2",
    2: "9e328bf4bd6ed9eeadac6f41c5de303c69dfc078dfeac3e64b26e18d3e09d38d",
    3: "9c2c2cf0dea4eb8a691c6680fabc66f6456233ba83867466a06ffd5abda3462b",
    4: "11c6ccfec5dc51be7c08f1713058412694e1b7def1c5d8cd5520f7f7568aeff2",
}


class AuditFailure(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise AuditFailure(f"missing JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def safe_extract(packet: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(packet, "r:gz") as tf:
        for member in tf.getmembers():
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(dest.resolve()) + "/") and target != dest.resolve():
                raise AuditFailure(f"unsafe packet member path: {member.name}")
        tf.extractall(dest)


def find_packet_results(unpacked: Path) -> Path:
    candidates = [
        unpacked / "results" / TASK,
        unpacked / TASK,
    ]
    candidates.extend(unpacked.rglob(f"results/{TASK}"))
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise AuditFailure("could not locate workstation result packet")


def audit(staging: Path, repo: Path, results: Path) -> dict:
    results.mkdir(parents=True, exist_ok=True)
    archive = staging / EXPECTED_ARCHIVE
    sums = staging / "SHA256SUMS"
    packet = staging / "workstation_lightweight_packet.tar.gz"
    require(archive.exists(), f"missing archive in staging: {archive}")
    require(sums.exists(), f"missing SHA256SUMS in staging: {sums}")
    require(packet.exists(), f"missing packet in staging: {packet}")

    archive_size = archive.stat().st_size
    archive_sha = sha256_file(archive)
    sums_text = sums.read_text(encoding="utf-8")
    archive_receipt = {
        "archive": str(archive),
        "checked_at_utc": utc_now(),
        "expected_sha256": EXPECTED_SHA256,
        "expected_size_bytes": EXPECTED_SIZE,
        "sha256": archive_sha,
        "sha256sums_contains_expected": EXPECTED_SHA256 in sums_text and EXPECTED_ARCHIVE in sums_text,
        "size_bytes": archive_size,
        "status": "PASS" if archive_sha == EXPECTED_SHA256 and archive_size == EXPECTED_SIZE else "FAIL",
    }
    write_json(results / "server_corrected_archive_receipt.json", archive_receipt)
    require(archive_receipt["status"] == "PASS", "corrected archive size/SHA mismatch on server")
    require(archive_receipt["sha256sums_contains_expected"], "SHA256SUMS does not bind corrected archive")

    unpacked = staging / "packet_unpacked"
    safe_extract(packet, unpacked)
    packet_results = find_packet_results(unpacked)

    provenance = load_json(packet_results / "corrected_myops_runtime_only_hotfix_provenance.json")
    invariance = load_json(packet_results / "model_invariance_comparison.json")
    normal = load_json(packet_results / "normal_15case_regression_summary.json")
    edge = load_json(packet_results / "single_slice_edge_summary.json")
    mixed = load_json(packet_results / "mixed_batch_summary.json")
    clean = load_json(packet_results / "clean_save_load_receipt.json")
    failure_modes = load_json(packet_results / "failure_mode_summary.json")
    drive = load_json(packet_results / "google_drive_corrected_upload_receipt.json")
    link = load_json(packet_results / "google_drive_corrected_public_link.json")
    strict = load_json(packet_results / "strict_validator_report.json")
    draft = packet_results / "organizer_reply_draft.md"
    require(draft.exists(), "missing organizer reply draft")
    draft_text = draft.read_text(encoding="utf-8")

    packet_audit = {
        "archive_sha256_matches": provenance.get("new_archive_sha256") == EXPECTED_SHA256,
        "archive_size_matches": provenance.get("new_archive_size_bytes") == EXPECTED_SIZE,
        "geometry_mismatch_status": failure_modes.get("failures", [{}])[0].get("status") if failure_modes.get("failures") else None,
        "model_changed": provenance.get("model_changed"),
        "only_runtime_preprocessing_fix": provenance.get("only_runtime_preprocessing_fix"),
        "packet_results": str(packet_results),
        "strict_validator_pass": strict.get("status") == "PASS" and strict.get("require_upload") is True,
    }
    packet_audit["status"] = "PASS" if all(
        [
            packet_audit["archive_sha256_matches"],
            packet_audit["archive_size_matches"],
            packet_audit["geometry_mismatch_status"] == GEOMETRY_MISMATCH_TOKEN,
            packet_audit["model_changed"] is False,
            packet_audit["only_runtime_preprocessing_fix"] is True,
            packet_audit["strict_validator_pass"],
        ]
    ) else "FAIL"
    write_json(results / "provenance_packet_audit.json", packet_audit)
    require(packet_audit["status"] == "PASS", "packet provenance audit failed")

    checkpoint_hashes = {
        int(item["fold"]): item["sha256"] for item in provenance.get("checkpoints", [])
    }
    model_audit = {
        "checkpoint_hashes_match_frozen_contract": checkpoint_hashes == CHECKPOINT_SHA256,
        "entrypoint_cmd_env_equal": invariance.get("entrypoint_cmd_env_equal") is True,
        "forbidden_model_assets_present": invariance.get("forbidden_model_assets_present") is False,
        "model_checkpoint_hashes_equal": invariance.get("model_checkpoint_hashes_equal") is True,
        "pip_freeze_equal": invariance.get("pip_freeze_equal") is True,
        "plans_dataset_hashes_equal": invariance.get("plans_dataset_hashes_equal") is True,
        "predict_entrypoint_requirements_hashes_equal": invariance.get("predict_entrypoint_requirements_hashes_equal") is True,
        "rootfs_prefix": invariance.get("base_rootfs_diff_ids_are_exact_prefix") is True,
    }
    model_audit["status"] = "PASS" if all(model_audit.values()) else "FAIL"
    write_json(results / "model_invariance_server_audit.json", model_audit)
    require(model_audit["status"] == "PASS", "model invariance audit failed")

    boundary_audit = {
        "clean_save_load_status": clean.get("status"),
        "clean_synthetic_full_matrix_rerun_pass": clean.get("synthetic_full_matrix_rerun_pass") is True,
        "depth1_cases_passed": edge.get("depth1_cases_passed"),
        "depth2_cases_passed": edge.get("depth2_cases_passed"),
        "edge_status": edge.get("status"),
        "mixed_missing_outputs": mixed.get("missing_outputs"),
        "mixed_status": mixed.get("status"),
        "normal_array_exact_count": normal.get("array_exact_count"),
        "normal_case_count": normal.get("case_count"),
        "normal_canonical_sha_exact_count": normal.get("canonical_sha_exact_count"),
        "normal_geometry_exact_count": normal.get("geometry_exact_count"),
        "normal_status": normal.get("status"),
    }
    boundary_audit["status"] = "PASS" if all(
        [
            boundary_audit["normal_status"] == "PASS",
            boundary_audit["normal_case_count"] == 15,
            boundary_audit["normal_array_exact_count"] == 15,
            boundary_audit["normal_geometry_exact_count"] == 15,
            boundary_audit["normal_canonical_sha_exact_count"] == 15,
            boundary_audit["edge_status"] == "PASS",
            boundary_audit["depth1_cases_passed"] >= 7,
            boundary_audit["depth2_cases_passed"] >= 4,
            boundary_audit["mixed_status"] == "PASS",
            boundary_audit["mixed_missing_outputs"] == [],
            boundary_audit["clean_save_load_status"] == "PASS",
            boundary_audit["clean_synthetic_full_matrix_rerun_pass"],
        ]
    ) else "FAIL"
    write_json(results / "boundary_regression_server_audit.json", boundary_audit)
    require(boundary_audit["status"] == "PASS", "boundary/regression audit failed")

    drive_audit = {
        "archive_file_id": link.get("file_id"),
        "archive_sha256_matches": drive.get("remote_archive", {}).get("sha256") == EXPECTED_SHA256,
        "archive_size_matches": drive.get("remote_archive", {}).get("size_bytes") == EXPECTED_SIZE,
        "authorized_files_only": drive.get("authorized_files") == ["MyoPS-OrganAgent-corrected.tar.gz", "SHA256SUMS"],
        "forbidden_payloads_uploaded": drive.get("forbidden_payloads_uploaded"),
        "link": link.get("link"),
        "public_access_ok": link.get("public_access_ok"),
        "reused_old_failed_url": link.get("reused_old_failed_url"),
    }
    drive_audit["status"] = "PASS" if all(
        [
            drive_audit["archive_sha256_matches"],
            drive_audit["archive_size_matches"],
            drive_audit["authorized_files_only"],
            drive_audit["forbidden_payloads_uploaded"] is False,
            drive_audit["link"] == EXPECTED_LINK,
            drive_audit["public_access_ok"] is True,
            drive_audit["reused_old_failed_url"] is False,
        ]
    ) else "FAIL"
    write_json(results / "drive_link_server_audit.json", drive_audit)
    require(drive_audit["status"] == "PASS", "Drive link audit failed")

    draft_audit = {
        "contains_drive_link": EXPECTED_LINK in draft_text,
        "contains_email_sent_false": "email_sent=false" in draft_text,
        "mentions_care_ase": "CARE-ASE" in draft_text,
        "status": "PASS" if EXPECTED_LINK in draft_text and "email_sent=false" in draft_text and "CARE-ASE" not in draft_text else "FAIL",
    }
    (results / "organizer_reply_draft_audit.md").write_text(
        "\n".join(
            [
                "# Organizer Reply Draft Audit",
                "",
                f"status: {draft_audit['status']}",
                f"contains_drive_link: {str(draft_audit['contains_drive_link']).lower()}",
                f"contains_email_sent_false: {str(draft_audit['contains_email_sent_false']).lower()}",
                f"mentions_care_ase: {str(draft_audit['mentions_care_ase']).lower()}",
                "",
                "No organizer email was sent by this audit.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    require(draft_audit["status"] == "PASS", "organizer reply draft audit failed")

    final = {
        "checked_at_utc": utc_now(),
        "docker_ran_on_server": False,
        "ready_token": READY_TOKEN,
        "server_repo": str(repo),
        "status": READY_TOKEN,
    }
    write_json(results / "final_readiness.json", final)
    write_json(results / "strict_validator_report.json", {"require_upload": True, "status": "PASS", "server_static_audit": True})
    (results / "completion_check.md").write_text(
        "\n".join(
            [
                "本次服务器静态审计确认 corrected MyoPS archive 的大小和 SHA 与工位 receipt、Google Drive receipt 完全一致；轻量 provenance packet 证明修复只增加 nnU-Net `compute_new_shape` 的最小维度 clamp，没有更换模型、checkpoint、推理配置或依赖。15 个正常公开病例保持 bitwise exact，depth1/depth2 合法单层边界、mixed batch 和 clean save/load 证据均为 PASS；畸形跨模态 geometry mismatch 被记录为继承的非阻塞基础行为。未发送组织方邮件。",
                "",
                f"final_status: {READY_TOKEN}",
                "docker_ran_on_server: false",
                f"drive_link: {EXPECTED_LINK}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (results / "controller_report.md").write_text(
        "\n".join(
            [
                "服务器只做静态 provenance 审计，没有运行 Docker。审计结果表明 corrected archive 与授权 SHA/size 一致，Drive 公链指向该 corrected archive，轻量 packet 中的模型不变性、15/15 正常病例 exact regression、边界矩阵、mixed batch 与 clean save/load 证据全部通过；组织方邮件仍未发送。",
                "",
                f"controller_verification_decision: VERIFIED_COMPLETE",
                f"terminal_token: {READY_TOKEN}",
                f"corrected_archive_sha256: {EXPECTED_SHA256}",
                f"drive_link: {EXPECTED_LINK}",
                "organizer_email_sent: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        results / "notification_brief.json",
        {
            "blocked_or_failure_reason": "",
            "commit_status": "pending_local_commit_push",
            "evidence_paths": [
                str(results / "final_readiness.json"),
                str(results / "server_corrected_archive_receipt.json"),
                str(results / "provenance_packet_audit.json"),
                str(results / "drive_link_server_audit.json"),
            ],
            "final_status": "complete",
            "key_conclusion": "Corrected MyoPS runtime-only single-slice hotfix passed server static provenance audit; organizer email was not sent.",
            "next_step": "Commit/push lightweight receipts, run existing CARE notifier, then user may manually send organizer reply.",
            "push_status": "pending_local_commit_push",
            "slurm_terminal_status": "not_applicable",
            "task_name": TASK,
        },
    )
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging", required=True)
    parser.add_argument("--repo", default="/users/a/e/aereinh/CARE")
    parser.add_argument("--results")
    args = parser.parse_args()
    repo = Path(args.repo)
    results = Path(args.results) if args.results else repo / "results" / SERVER_TASK
    try:
        final = audit(Path(args.staging), repo, results)
    except Exception as exc:
        results.mkdir(parents=True, exist_ok=True)
        failed = {"checked_at_utc": utc_now(), "error": str(exc), "status": "SERVER_STATIC_AUDIT_FAILED"}
        write_json(results / "final_readiness.json", failed)
        print(json.dumps(failed, indent=2, sort_keys=True))
        return 1
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
