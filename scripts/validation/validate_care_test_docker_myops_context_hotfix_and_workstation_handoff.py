#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

TASK = "20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff"
PREV_TASK = "20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle"
CARE_ROOT = Path(__file__).resolve().parents[2]
RESULTS = CARE_ROOT / "results" / TASK
PREV_RESULTS = CARE_ROOT / "results" / PREV_TASK
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK
TRANSFER = RUNTIME / "transfer"
MYOPS_CONTEXT = CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS"
CINE_SHA = "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136"
OFFICIAL_LABEL_MAP = {"0": 0, "1": 200, "2": 500, "3": 600, "4": 1220, "5": 2221}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(failures: list[str], msg: str) -> None:
    failures.append(msg)


def dockerfile_has_models_copy(text: str) -> bool:
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#"))
    return "COPY models /app/models" in normalized


def check_required_files(failures: list[str]) -> None:
    required_results = [
        "controller_context.json",
        "controller_ledger.csv",
        "docker_context_hotfix_receipt.json",
        "myops_bundle_manifest.json",
        "cine_sentinel_manifest.json",
        "transfer_receipt.json",
        "workstation_handoff_receipt.json",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
        "notification_brief.json",
    ]
    for name in required_results:
        if not (RESULTS / name).exists():
            fail(failures, f"missing result file: {name}")
    required_transfer = [
        "MyoPS-nnUNet-workstation-bundle.tar.gz",
        "MyoPS-nnUNet-workstation-bundle.tar.gz.sha256",
        "CineMyoPS-OrganAgent.tar.gz",
        "CineMyoPS-OrganAgent.tar.gz.sha256",
        "cine_sentinel_manifest.json",
        "WORKSTATION_HANDOFF.json",
        "SERVER_BUNDLE_READY.json",
        "TRANSFER_MANIFEST.json",
        "WORKSTATION_INSTRUCTIONS.md",
    ]
    for name in required_transfer:
        if not (TRANSFER / name).exists():
            fail(failures, f"missing transfer file: {name}")


def check_docker_context(failures: list[str]) -> None:
    dockerfile = (MYOPS_CONTEXT / "Dockerfile").read_text(encoding="utf-8")
    predict = (MYOPS_CONTEXT / "predict.py").read_text(encoding="utf-8")
    if not dockerfile_has_models_copy(dockerfile):
        fail(failures, "Dockerfile does not copy models into /app/models")
    known_bad = dockerfile.replace("COPY models /app/models", "")
    if dockerfile_has_models_copy(known_bad):
        fail(failures, "known-bad fixture did not fail after removing COPY models")
    for token in ["/app/models/nnunet/nnUNet_raw", "/app/models/nnunet/nnUNet_preprocessed"]:
        if token not in dockerfile:
            fail(failures, f"Dockerfile does not create {token}")
    dockerignore = MYOPS_CONTEXT / ".dockerignore"
    if dockerignore.exists():
        text = dockerignore.read_text(encoding="utf-8")
        bad = [line for line in text.splitlines() if line.strip().rstrip("/") == "models"]
        if bad:
            fail(failures, f".dockerignore excludes models: {bad}")
    for text_name, text in [("Dockerfile", dockerfile), ("predict.py", predict)]:
        for token in ["MoSAIC", "fine_scar.pt", "coarse.pt", "coarse_edema.pt", "edema.pt", "scar overlay", "priority overwrite", "--disable_tta"]:
            if token in text:
                fail(failures, f"{text_name} contains forbidden token {token}")
    req = (MYOPS_CONTEXT / "requirements.lock").read_text(encoding="utf-8")
    for pin in ["nnunetv2==2.7.0", "torch==2.11.0", "numpy==1.26.4", "SimpleITK==2.5.0"]:
        if pin not in req:
            fail(failures, f"requirements.lock missing {pin}")
    for token in ["-d", '"501"', "-tr", "nnUNetTrainer_500epochs", "-c", "3d_fullres", "-f", '"0"', '"1"', '"2"', '"3"', '"4"', "-chk", "checkpoint_best.pth"]:
        if token not in predict:
            fail(failures, f"predict.py missing fixed nnU-Net token {token}")


def check_contract_and_assets(failures: list[str]) -> None:
    prev_contract = load_json(PREV_RESULTS / "revised_final_submission_model_contract.json")
    if prev_contract["myops"]["official_label_map"] != OFFICIAL_LABEL_MAP:
        fail(failures, "previous revised contract label map is not the frozen map")
    hotfix = load_json(RESULTS / "docker_context_hotfix_receipt.json")
    if hotfix.get("model_contract_changed"):
        fail(failures, "hotfix receipt claims model contract changed")
    if not hotfix.get("dockerfile_contains_copy_models"):
        fail(failures, "hotfix receipt does not prove COPY models")
    prev_assets = {
        item["role"]: item
        for item in load_json(PREV_RESULTS / "nnunet_source_manifest.json")["dataset501_assets"]
        if item["role"].startswith("fold_")
    }
    manifest = load_json(RESULTS / "myops_bundle_manifest.json")
    models = manifest.get("models_manifest", [])
    checkpoints = [item for item in models if item["path"].endswith("checkpoint_best.pth")]
    if len(checkpoints) != 5:
        fail(failures, f"bundle checkpoint count is {len(checkpoints)}, expected 5")
    for fold in range(5):
        expected = prev_assets[f"fold_{fold}_checkpoint_best"]["sha256"]
        matches = [item for item in checkpoints if f"fold_{fold}/checkpoint_best.pth" in item["path"]]
        if len(matches) != 1:
            fail(failures, f"bundle missing fold_{fold}/checkpoint_best.pth")
            continue
        if matches[0]["sha256"] != expected:
            fail(failures, f"fold_{fold} checkpoint SHA mismatch")
    for rel in ["plans.json", "dataset.json"]:
        if not any(item["path"].endswith(rel) for item in models):
            fail(failures, f"bundle models missing {rel}")


def check_tar_and_transfer(failures: list[str]) -> None:
    bundle = TRANSFER / "MyoPS-nnUNet-workstation-bundle.tar.gz"
    if sha256_file(bundle) != load_json(RESULTS / "myops_bundle_manifest.json")["bundle_sha256"]:
        fail(failures, "MyoPS bundle SHA does not match manifest")
    with tarfile.open(bundle, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            if member.issym():
                fail(failures, f"MyoPS bundle contains symlink: {member.name}")
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                fail(failures, f"MyoPS bundle contains unsafe path: {member.name}")
        required = [
            "contexts/MyoPS/Dockerfile",
            "contexts/MyoPS/entrypoint.sh",
            "contexts/MyoPS/predict.py",
            "contexts/MyoPS/requirements.lock",
            "contexts/MyoPS/models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/plans.json",
            "contexts/MyoPS/models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/dataset.json",
            "sentinel_inputs/myops/Case1012/Case1012_LGE.nii.gz",
            "expected_outputs/myops/Case1012_pred.nii.gz",
            "verification/verify_myops_outputs.py",
            "evidence/revised_final_submission_model_contract.json",
            "README.md",
        ]
        for name in required:
            if name not in names:
                fail(failures, f"MyoPS bundle missing {name}")
        for fold in range(5):
            name = f"contexts/MyoPS/models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_{fold}/checkpoint_best.pth"
            if name not in names:
                fail(failures, f"MyoPS bundle missing {name}")
    cine = TRANSFER / "CineMyoPS-OrganAgent.tar.gz"
    if sha256_file(cine) != CINE_SHA:
        fail(failures, "Cine archive SHA changed")
    cine_manifest = load_json(TRANSFER / "cine_sentinel_manifest.json")
    if cine_manifest.get("case_ids") != ["Case1011", "Case1006", "Case1003"]:
        fail(failures, f"Cine sentinel cases changed: {cine_manifest.get('case_ids')}")
    if cine_manifest.get("contains_ground_truth"):
        fail(failures, "Cine sentinel manifest claims GT included")
    if cine_manifest.get("server_expected_outputs_generated"):
        fail(failures, "Cine sentinel manifest claims server expected outputs")
    for case_id in cine_manifest.get("case_ids", []):
        if not (TRANSFER / "cine_sentinel_inputs" / f"{case_id}_Cine.nii.gz").exists():
            fail(failures, f"missing Cine sentinel input {case_id}")
    for path in TRANSFER.rglob("*"):
        if path.is_symlink():
            fail(failures, f"transfer contains symlink: {path.relative_to(TRANSFER)}")
    handoff = load_json(TRANSFER / "WORKSTATION_HANDOFF.json")
    for key in [
        "status",
        "server_commit",
        "server_transfer_root",
        "myops_bundle",
        "myops_bundle_sha256",
        "myops_image_tag",
        "cinemyops_archive",
        "cinemyops_archive_sha256",
        "cinemyops_image_tag",
        "myops_sentinel_cases",
        "cine_sentinel_manifest",
        "expected_workstation_root",
        "final_server_dist",
        "workstation_return_staging",
    ]:
        if key not in handoff:
            fail(failures, f"WORKSTATION_HANDOFF missing {key}")
    ready = load_json(TRANSFER / "SERVER_BUNDLE_READY.json")
    if not ready.get("workstation_build_authorized"):
        fail(failures, "SERVER_BUNDLE_READY does not authorize workstation build")
    if not ready.get("myops_context_models_copy_fixed"):
        fail(failures, "SERVER_BUNDLE_READY does not mark models copy fixed")
    if ready.get("server_docker_run_performed") or ready.get("new_training_performed"):
        fail(failures, "SERVER_BUNDLE_READY claims forbidden server execution")
    if not ready.get("cine_archive_byte_preserved"):
        fail(failures, "SERVER_BUNDLE_READY does not mark Cine byte preservation")


def check_heavy_not_staged(failures: list[str]) -> None:
    out = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=CARE_ROOT, text=True, capture_output=True, check=True)
    heavy_suffixes = (".pt", ".pth", ".nii", ".nii.gz", ".tar", ".tar.gz")
    for line in out.stdout.splitlines():
        if line.endswith(heavy_suffixes) or "/transfer/" in line or "/runtime/" in line or "/downloads/" in line:
            fail(failures, f"heavy/runtime artifact staged: {line}")


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    if not failures:
        check_docker_context(failures)
        check_contract_and_assets(failures)
        check_tar_and_transfer(failures)
        check_heavy_not_staged(failures)
    report = {
        "task": TASK,
        "status": "PASS" if not failures else "FAIL",
        "checks": [
            "Dockerfile COPY models and known-bad deletion fixture",
            "bundle context models/checkpoints",
            "checkpoint SHA equality",
            "fixed command and label map",
            "Cine archive SHA and sentinels",
            "transfer symlink/path safety",
            "WORKSTATION_HANDOFF/SERVER_BUNDLE_READY",
            "heavy staged artifact guard",
        ],
        "failures": failures,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "strict_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
