#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TASK = "20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle"
CARE_ROOT = Path(__file__).resolve().parents[2]
RESULTS = CARE_ROOT / "results" / TASK
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK
TRANSFER = RUNTIME / "transfer"
MYOPS_CONTEXT = CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS"
CINE_SHA = "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136"
MYOPS_REF_SHA = "81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)


def run_git(args: list[str]) -> list[str]:
    out = subprocess.run(["git", *args], cwd=CARE_ROOT, text=True, capture_output=True, check=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def check_required_files(failures: list[str]) -> None:
    required = [
        "controller_context.json",
        "controller_ledger.csv",
        "revised_final_submission_model_contract.json",
        "nnunet_environment_fingerprint.json",
        "nnunet_source_manifest.json",
        "nnunet_dependency_freeze.txt",
        "collaborator_archive_manifest.json",
        "collaborator_myops_archive_audit.json",
        "collaborator_cinemyops_archive_audit.json",
        "pure_nnunet_myops_15case_manifest.json",
        "pure_nnunet_myops_sentinel_manifest.json",
        "pure_nnunet_myops_host_smoke_receipt.json",
        "pure_nnunet_myops_output_mapping_receipt.json",
        "transfer_bundle_receipt.json",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
        "notification_brief.json",
    ]
    for name in required:
        if not (RESULTS / name).exists():
            fail(f"missing result file: {name}", failures)
    transfer_required = [
        "SERVER_BUNDLE_READY.json",
        "TRANSFER_MANIFEST.json",
        "WORKSTATION_INSTRUCTIONS.md",
        "MyoPS-nnUNet-workstation-bundle.tar.gz",
        "MyoPS-nnUNet-workstation-bundle.tar.gz.sha256",
        "CineMyoPS-OrganAgent.tar.gz",
        "CineMyoPS-OrganAgent.tar.gz.sha256",
        "reference/collaborator_myops_archive_audit.json",
        "reference/collaborator_myops_remote_path.json",
    ]
    for name in transfer_required:
        if not (TRANSFER / name).exists():
            fail(f"missing transfer file: {name}", failures)


def check_myops_context(failures: list[str]) -> None:
    forbidden_names = {"coarse.pt", "fine_scar.pt", "coarse_edema.pt", "edema.pt"}
    forbidden_parts = {"vendor", "configs"}
    for path in MYOPS_CONTEXT.rglob("*"):
        rel = path.relative_to(MYOPS_CONTEXT)
        if path.name in forbidden_names:
            fail(f"MyoPS context contains forbidden weight: {rel}", failures)
        if any(part in forbidden_parts for part in rel.parts):
            fail(f"MyoPS context contains obsolete runtime directory: {rel}", failures)
    predict = (MYOPS_CONTEXT / "predict.py").read_text(encoding="utf-8")
    for token in [
        "nnUNetv2_predict",
        "nnUNetTrainer_500epochs",
        "checkpoint_best.pth",
        '"0"',
        '"1"',
        '"2"',
        '"3"',
        '"4"',
        "--disable_progress_bar",
        "Incomplete MyoPS input cases",
        "missing modalities",
    ]:
        if token not in predict:
            fail(f"MyoPS predict.py missing required token: {token}", failures)
    for token in ["--disable_tta", "checkpoint_final", "zero-fill", "overlay", "priority", "coarse.pt", "fine_scar.pt", "edema.pt"]:
        if token in predict:
            fail(f"MyoPS predict.py contains forbidden token: {token}", failures)
    label_map = load_json(RESULTS / "revised_final_submission_model_contract.json")["myops"]["official_label_map"]
    if label_map != {"0": 0, "1": 200, "2": 500, "3": 600, "4": 1220, "5": 2221}:
        fail(f"official label map mismatch: {label_map}", failures)
    dockerfile = (MYOPS_CONTEXT / "Dockerfile").read_text(encoding="utf-8")
    if "FROM python:3.12-slim" not in dockerfile:
        fail("Dockerfile is not bound to Python 3.12 minor line", failures)
    if "COPY vendor" in dockerfile or "COPY configs" in dockerfile:
        fail("Dockerfile still copies vendor/configs", failures)
    requirements = (MYOPS_CONTEXT / "requirements.lock").read_text(encoding="utf-8")
    for pin in ["nnunetv2==2.7.0", "torch==2.11.0", "numpy==1.26.4", "SimpleITK==2.5.0"]:
        if pin not in requirements:
            fail(f"requirements.lock missing exact pin {pin}", failures)


def check_contract_and_receipts(failures: list[str]) -> None:
    env = load_json(RESULTS / "nnunet_environment_fingerprint.json")
    if env["packages"].get("nnunetv2") != "2.7.0":
        fail("nnunetv2 version is not recorded as 2.7.0", failures)
    source = load_json(RESULTS / "nnunet_source_manifest.json")
    if source.get("python_file_count", 0) < 1:
        fail("nnU-Net source manifest does not enumerate Python files", failures)
    if len(source.get("dataset501_assets", [])) != 7:
        fail("Dataset501 asset manifest does not contain 5 checkpoints plus plans/dataset", failures)
    folds = [asset for asset in source.get("dataset501_assets", []) if asset["role"].startswith("fold_")]
    if len(folds) != 5:
        fail("fold count is not 5", failures)
    if any("checkpoint_final" in asset["path"] for asset in source.get("dataset501_assets", [])):
        fail("checkpoint_final appears in fixed asset manifest", failures)

    contract = load_json(RESULTS / "revised_final_submission_model_contract.json")
    if contract.get("selected_myops") != "dataset501_nnunet_v2_5fold_best_default_tta_all_six_classes":
        fail("MyoPS selected model is not pure Dataset501 5-fold nnU-Net", failures)
    myops = contract["myops"]
    if myops.get("folds") != [0, 1, 2, 3, 4]:
        fail("MyoPS contract folds are not 0-4", failures)
    if myops.get("checkpoint") != "checkpoint_best.pth":
        fail("MyoPS contract checkpoint is not checkpoint_best.pth", failures)
    if myops.get("tta") != "default":
        fail("MyoPS contract does not preserve default TTA", failures)
    if contract["collaborator_myops_reference"].get("selected_as_final"):
        fail("collaborator MyoPS reference is marked final", failures)
    if contract.get("server_docker_run_performed"):
        fail("contract claims server Docker run", failures)
    if contract.get("challenge_upload_performed") or contract.get("validation_upload_performed") or contract.get("organizer_email_sent"):
        fail("contract claims forbidden upload/email action", failures)

    manifest15 = load_json(RESULTS / "pure_nnunet_myops_15case_manifest.json")
    if manifest15.get("case_count") != 15:
        fail("pure nnU-Net 15-case manifest is not 15/15", failures)
    semantics = manifest15.get("command_semantics", {})
    if semantics.get("folds") != [0, 1, 2, 3, 4]:
        fail("fresh output provenance folds are not 0-4", failures)
    if semantics.get("checkpoint_name") != "checkpoint_best.pth":
        fail("fresh output provenance checkpoint is not checkpoint_best.pth", failures)
    if semantics.get("disable_tta"):
        fail("fresh output provenance disables TTA", failures)
    if manifest15.get("historical_package_a_used_as_model_input"):
        fail("historical package A is marked as model input", failures)

    sentinel = load_json(RESULTS / "pure_nnunet_myops_sentinel_manifest.json")
    if sentinel.get("sentinel_case_ids") != ["Case1012", "Case1001", "Case1004"]:
        fail(f"sentinel selection is not min/median/max expected cases: {sentinel.get('sentinel_case_ids')}", failures)
    smoke = load_json(RESULTS / "pure_nnunet_myops_host_smoke_receipt.json")
    if smoke.get("server_docker_run_performed"):
        fail("host smoke claims server Docker run", failures)
    if not smoke.get("fresh_3case_replay_performed"):
        fail("host smoke did not record fresh 3-case replay despite available allocation", failures)
    for case in smoke.get("cases", []):
        if case["changed_fraction"] > 1e-5:
            fail(f"{case['case_id']} changed fraction exceeds tolerance", failures)
        low = {label: dice for label, dice in case["per_label_dice"].items() if dice < 0.9999}
        if low:
            fail(f"{case['case_id']} per-label Dice below tolerance: {low}", failures)


def check_archives_and_transfer(failures: list[str]) -> None:
    myops_audit = load_json(RESULTS / "collaborator_myops_archive_audit.json")
    cine_audit = load_json(RESULTS / "collaborator_cinemyops_archive_audit.json")
    if myops_audit.get("sha256") != MYOPS_REF_SHA or myops_audit.get("status") != "PASS":
        fail("collaborator MyoPS reference archive audit failed or SHA mismatch", failures)
    if cine_audit.get("sha256") != CINE_SHA or cine_audit.get("status") != "PASS":
        fail("collaborator Cine archive audit failed or SHA mismatch", failures)
    if myops_audit.get("docker_run_performed") or cine_audit.get("docker_run_performed"):
        fail("static audit was misreported as Docker run", failures)
    if cine_audit.get("repo_tags") != ["care-myocardium-cinemyops:organagent"]:
        fail(f"Cine repo tag mismatch: {cine_audit.get('repo_tags')}", failures)
    if myops_audit.get("repo_tags") != ["care-myocardium-myops:organagent"]:
        fail(f"collaborator MyoPS reference repo tag mismatch: {myops_audit.get('repo_tags')}", failures)

    ready = load_json(TRANSFER / "SERVER_BUNDLE_READY.json")
    if ready.get("status") != "READY":
        fail("SERVER_BUNDLE_READY status is not READY", failures)
    if ready.get("selected_myops_scar") != "nnunet_raw_class5":
        fail("SERVER_BUNDLE_READY scar is not nnU-Net raw class5", failures)
    if ready.get("selected_myops_pure_edema") != "nnunet_raw_class4":
        fail("SERVER_BUNDLE_READY edema is not nnU-Net raw class4", failures)
    if ready.get("selected_myops_anatomy") != "nnunet_raw_classes123":
        fail("SERVER_BUNDLE_READY anatomy is not raw classes 1/2/3", failures)
    if ready.get("cinemyops_archive_sha256") != CINE_SHA:
        fail("SERVER_BUNDLE_READY Cine SHA mismatch", failures)
    if ready.get("server_docker_run_performed"):
        fail("SERVER_BUNDLE_READY claims server Docker run", failures)

    transfer = load_json(TRANSFER / "TRANSFER_MANIFEST.json")
    transfer_paths = {item["path"] for item in transfer.get("files", [])}
    required_paths = {
        "SERVER_BUNDLE_READY.json",
        "WORKSTATION_INSTRUCTIONS.md",
        "MyoPS-nnUNet-workstation-bundle.tar.gz",
        "MyoPS-nnUNet-workstation-bundle.tar.gz.sha256",
        "CineMyoPS-OrganAgent.tar.gz",
        "CineMyoPS-OrganAgent.tar.gz.sha256",
        "reference/collaborator_myops_archive_audit.json",
        "reference/collaborator_myops_remote_path.json",
    }
    missing = sorted(required_paths.difference(transfer_paths))
    if missing:
        fail(f"TRANSFER_MANIFEST missing files: {missing}", failures)
    if "MyoPS-OrganAgent-collaborator-reference.tar.gz" in transfer_paths:
        fail("collaborator MyoPS reference archive was copied into primary transfer", failures)


def check_git_staging(failures: list[str]) -> None:
    heavy_suffixes = (".pt", ".pth", ".nii", ".nii.gz", ".tar", ".tar.gz")
    staged = run_git(["diff", "--cached", "--name-only"])
    for path in staged:
        if path.endswith(heavy_suffixes) or "/downloads/" in path or "/transfer/" in path:
            fail(f"heavy or runtime artifact staged to Git: {path}", failures)


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    if not failures:
        check_myops_context(failures)
        check_contract_and_receipts(failures)
        check_archives_and_transfer(failures)
        check_git_staging(failures)

    report = {
        "task": TASK,
        "status": "PASS" if not failures else "FAIL",
        "checks": [
            "required files",
            "pure nnU-Net MyoPS context",
            "model contract and nnU-Net provenance",
            "collaborator archive static audits",
            "transfer completeness",
            "Git staged heavy artifact guard",
        ],
        "failures": failures,
    }
    (RESULTS / "strict_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
