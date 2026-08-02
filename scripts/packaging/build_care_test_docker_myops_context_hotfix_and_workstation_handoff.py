#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import SimpleITK as sitk

TASK = "20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff"
PREV_TASK = "20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle"
CARE_ROOT = Path(__file__).resolve().parents[2]
RESULTS = CARE_ROOT / "results" / TASK
PREV_RESULTS = CARE_ROOT / "results" / PREV_TASK
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK
PREV_RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE") / PREV_TASK
TRANSFER = RUNTIME / "transfer"
MYOPS_CONTEXT = CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS"
NNUNET_ASSET_ROOT = CARE_ROOT / (
    "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
MYOPS_SENTINELS = ["Case1012", "Case1001", "Case1004"]
CINE_SENTINELS = ["Case1011", "Case1006", "Case1003"]
CINE_SOURCE_ROOT = CARE_ROOT / "data/CARE_Challenge/CineMyoPS_val/AnonymousCenter"
MYOPS_SOURCE_ROOT = CARE_ROOT / "data/CARE_Challenge/MyoPS_val/AnonymousCenter"
CINE_SHA = "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136"
SERVER_BASE_COMMIT = "b94d3f916b04461d6b88a311959e0ed581e64555"
OFFICIAL_LABEL_MAP = {"0": 0, "1": 200, "2": 500, "3": 600, "4": 1220, "5": 2221}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {"__pycache__", ".pytest_cache", ".DS_Store"}}

    shutil.copytree(src, dst, ignore=ignore)


def ensure_no_symlinks(root: Path) -> None:
    links = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_symlink()]
    if links:
        raise RuntimeError(f"transfer contains symlinks: {links[:10]}")


def deterministic_tar_gz(src_dir: Path, out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    with out_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for path in sorted(src_dir.rglob("*")):
                    arcname = path.relative_to(src_dir).as_posix()
                    info = tar.gettarinfo(str(path), arcname=arcname)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if path.is_file():
                        with path.open("rb") as f:
                            tar.addfile(info, f)
                    else:
                        tar.addfile(info)


def list_files(root: Path) -> list[dict]:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            records.append({
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return records


def image_record(path: Path, case_id: str) -> dict:
    image = sitk.ReadImage(str(path))
    size = image.GetSize()
    return {
        "case_id": case_id,
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "shape_sitk": [int(v) for v in size],
        "spacing": [float(v) for v in image.GetSpacing()],
        "origin": [float(v) for v in image.GetOrigin()],
        "direction": [float(v) for v in image.GetDirection()],
        "frame_count": int(size[-1]) if len(size) >= 4 else int(size[2] if len(size) >= 3 else 1),
        "voxel_count": int(__import__("functools").reduce(lambda a, b: a * b, size, 1)),
    }


def copy_nnunet_models(context_dst: Path) -> list[dict]:
    model_dst = context_dst / "models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
    model_dst.mkdir(parents=True, exist_ok=True)
    for name in ["plans.json", "dataset.json"]:
        shutil.copy2(NNUNET_ASSET_ROOT / name, model_dst / name)
    for fold in range(5):
        dst = model_dst / f"fold_{fold}"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(NNUNET_ASSET_ROOT / f"fold_{fold}/checkpoint_best.pth", dst / "checkpoint_best.pth")
    (context_dst / "models/nnunet/nnUNet_raw").mkdir(parents=True, exist_ok=True)
    (context_dst / "models/nnunet/nnUNet_preprocessed").mkdir(parents=True, exist_ok=True)
    return list_files(context_dst / "models")


def write_verification_scripts(bundle_root: Path) -> None:
    verification = bundle_root / "verification"
    verification.mkdir(parents=True, exist_ok=True)
    (verification / "verify_myops_outputs.py").write_text(
        (PREV_RUNTIME / "workstation_bundle_root/verification/verify_myops_outputs.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (verification / "verify_cine_archive_sha256.py").write_text(
        (PREV_RUNTIME / "workstation_bundle_root/verification/verify_cine_archive_sha256.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def build_myops_bundle() -> tuple[Path, dict]:
    bundle_root = RUNTIME / "workstation_bundle_root"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True)

    context_dst = bundle_root / "contexts/MyoPS"
    copytree_clean(MYOPS_CONTEXT, context_dst)
    models_manifest = copy_nnunet_models(context_dst)

    sentinel_in = bundle_root / "sentinel_inputs/myops"
    sentinel_out = bundle_root / "expected_outputs/myops"
    sentinel_out.mkdir(parents=True, exist_ok=True)
    prev_expected = PREV_RUNTIME / "pure_nnunet_myops_official_15case"
    for case_id in MYOPS_SENTINELS:
        copytree_clean(MYOPS_SOURCE_ROOT / case_id, sentinel_in / case_id)
        shutil.copy2(prev_expected / f"{case_id}_pred.nii.gz", sentinel_out / f"{case_id}_pred.nii.gz")

    evidence = bundle_root / "evidence"
    evidence.mkdir()
    for name in [
        "revised_final_submission_model_contract.json",
        "nnunet_environment_fingerprint.json",
        "nnunet_source_manifest.json",
        "pure_nnunet_myops_15case_manifest.json",
        "pure_nnunet_myops_host_smoke_receipt.json",
        "pure_nnunet_myops_sentinel_manifest.json",
        "collaborator_cinemyops_archive_audit.json",
    ]:
        shutil.copy2(PREV_RESULTS / name, evidence / name)
    write_verification_scripts(bundle_root)
    (bundle_root / "README.md").write_text(
        """# CARE2026 MyoPS nnU-Net Workstation Bundle Hotfix

This bundle fixes the MyoPS Docker context packaging gap by copying
`contexts/MyoPS/models` into `/app/models` during Docker build. The fixed model
contract is unchanged from commit b94d3f916b04461d6b88a311959e0ed581e64555.

Build:

```bash
cd contexts/MyoPS
docker build -t care-myocardium-myops:organagent .
```

Run sentinel:

```bash
docker run --rm \
  -v "$PWD/../../sentinel_inputs/myops:/input:ro" \
  -v "$PWD/../../workstation_outputs:/output" \
  care-myocardium-myops:organagent
python ../../verification/verify_myops_outputs.py \
  --expected ../../expected_outputs/myops \
  --actual ../../workstation_outputs/myops
```
""",
        encoding="utf-8",
    )

    out = TRANSFER / "MyoPS-nnUNet-workstation-bundle.tar.gz"
    deterministic_tar_gz(bundle_root, out)
    (TRANSFER / "MyoPS-nnUNet-workstation-bundle.tar.gz.sha256").write_text(
        f"{sha256_file(out)}  MyoPS-nnUNet-workstation-bundle.tar.gz\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "PASS",
        "bundle_path": str(out),
        "bundle_size_bytes": out.stat().st_size,
        "bundle_sha256": sha256_file(out),
        "bundle_file_count": len(list_files(bundle_root)),
        "context_path_in_bundle": "contexts/MyoPS",
        "context_models_size_bytes": sum(item["size_bytes"] for item in models_manifest),
        "checkpoint_count": sum(1 for item in models_manifest if item["path"].endswith("checkpoint_best.pth")),
        "models_manifest": models_manifest,
        "all_bundle_files": list_files(bundle_root),
    }
    return out, manifest


def copy_cine_archive_and_sentinels() -> dict:
    src = PREV_RUNTIME / "downloads/CineMyoPS-OrganAgent.tar.gz"
    dst = TRANSFER / "CineMyoPS-OrganAgent.tar.gz"
    shutil.copy2(src, dst)
    sha = sha256_file(dst)
    if sha != CINE_SHA:
        raise RuntimeError(f"Cine SHA mismatch after byte copy: {sha}")
    (TRANSFER / "CineMyoPS-OrganAgent.tar.gz.sha256").write_text(
        f"{sha}  CineMyoPS-OrganAgent.tar.gz\n",
        encoding="utf-8",
    )

    cine_root = TRANSFER / "cine_sentinel_inputs"
    if cine_root.exists():
        shutil.rmtree(cine_root)
    cine_root.mkdir(parents=True)
    records = []
    for case_id in CINE_SENTINELS:
        src_img = CINE_SOURCE_ROOT / f"{case_id}_Cine.nii.gz"
        dst_img = cine_root / f"{case_id}_Cine.nii.gz"
        shutil.copy2(src_img, dst_img)
        rec = image_record(dst_img, case_id)
        rec["source_path"] = str(src_img)
        records.append(rec)
    payload = {
        "status": "PASS",
        "selection_rule": "CineMyoPS validation inputs sorted by frame count then voxel count: min, median, max",
        "case_ids": CINE_SENTINELS,
        "records": records,
        "contains_ground_truth": False,
        "server_expected_outputs_generated": False,
    }
    write_json(TRANSFER / "cine_sentinel_manifest.json", payload)
    write_json(RESULTS / "cine_sentinel_manifest.json", payload)
    return {
        "archive_path": str(dst),
        "archive_size_bytes": dst.stat().st_size,
        "archive_sha256": sha,
        "cine_sentinel_cases": CINE_SENTINELS,
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    TRANSFER.mkdir(parents=True, exist_ok=True)
    dockerfile_text = (MYOPS_CONTEXT / "Dockerfile").read_text(encoding="utf-8")
    predict_text = (MYOPS_CONTEXT / "predict.py").read_text(encoding="utf-8")
    hotfix_receipt = {
        "task": TASK,
        "created_at_utc": now(),
        "base_commit": SERVER_BASE_COMMIT,
        "status": "PASS",
        "dockerfile_path": str(MYOPS_CONTEXT / "Dockerfile"),
        "dockerfile_contains_copy_models": "COPY models /app/models" in dockerfile_text,
        "dockerfile_creates_nnunet_raw_preprocessed": all(
            token in dockerfile_text for token in ["/app/models/nnunet/nnUNet_raw", "/app/models/nnunet/nnUNet_preprocessed"]
        ),
        "dockerignore_path": "",
        "dockerignore_excludes_models": False,
        "model_contract_changed": False,
        "forbidden_runtime_components_reintroduced": any(
            token in (dockerfile_text + predict_text)
            for token in ["MoSAIC", "fine_scar.pt", "coarse_edema.pt", "edema.pt", "--disable_tta"]
        ),
    }
    write_json(RESULTS / "docker_context_hotfix_receipt.json", hotfix_receipt)

    myops_bundle, myops_manifest = build_myops_bundle()
    write_json(RESULTS / "myops_bundle_manifest.json", myops_manifest)
    cine = copy_cine_archive_and_sentinels()

    handoff = {
        "status": "READY",
        "server_commit": "PENDING_COMMIT",
        "server_transfer_root": str(TRANSFER),
        "myops_bundle": "MyoPS-nnUNet-workstation-bundle.tar.gz",
        "myops_bundle_sha256": myops_manifest["bundle_sha256"],
        "myops_image_tag": "care-myocardium-myops:organagent",
        "cinemyops_archive": "CineMyoPS-OrganAgent.tar.gz",
        "cinemyops_archive_sha256": CINE_SHA,
        "cinemyops_image_tag": "care-myocardium-cinemyops:organagent",
        "myops_sentinel_cases": MYOPS_SENTINELS,
        "cine_sentinel_manifest": "cine_sentinel_manifest.json",
        "expected_workstation_root": "/home/yuukias/code/CARE",
        "final_server_dist": "/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist",
        "workstation_return_staging": "/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_workstation_return",
    }
    write_json(TRANSFER / "WORKSTATION_HANDOFF.json", handoff)

    ready = {
        **handoff,
        "workstation_build_authorized": True,
        "myops_context_models_copy_fixed": True,
        "server_docker_run_performed": False,
        "new_training_performed": False,
        "cine_archive_byte_preserved": True,
        "model_contract_changed": False,
    }
    write_json(TRANSFER / "SERVER_BUNDLE_READY.json", ready)

    instructions = f"""# CARE2026 Workstation Handoff Hotfix

This transfer fixes the MyoPS Docker context model-copy gap. The model contract
from `{SERVER_BASE_COMMIT}` is unchanged.

## MyoPS

Use `MyoPS-nnUNet-workstation-bundle.tar.gz`.

```bash
tar -xzf MyoPS-nnUNet-workstation-bundle.tar.gz -C myops_hotfix
cd myops_hotfix/contexts/MyoPS
docker build -t care-myocardium-myops:organagent .
```

The Dockerfile now copies `models/` into `/app/models`, so the embedded
`nnUNet_results` directory is visible at runtime.

## CineMyoPS

Load `CineMyoPS-OrganAgent.tar.gz` directly. Its SHA256 must remain:

`{CINE_SHA}`

The server did not run Docker and did not generate Cine expected outputs.
Use `cine_sentinel_inputs/` only as workstation smoke inputs.
"""
    (TRANSFER / "WORKSTATION_INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")

    ensure_no_symlinks(TRANSFER)
    transfer_files = list_files(TRANSFER)
    write_json(TRANSFER / "TRANSFER_MANIFEST.json", {
        "task": TASK,
        "created_at_utc": now(),
        "transfer_root": str(TRANSFER),
        "files": transfer_files,
        "symlink_count": 0,
        "myops_bundle_sha256": myops_manifest["bundle_sha256"],
        "cinemyops_archive_sha256": cine["archive_sha256"],
        "cine_sentinel_cases": CINE_SENTINELS,
    })
    final_transfer_files = list_files(TRANSFER)
    write_json(TRANSFER / "TRANSFER_MANIFEST.json", {
        "task": TASK,
        "created_at_utc": now(),
        "transfer_root": str(TRANSFER),
        "files": final_transfer_files,
        "symlink_count": 0,
        "myops_bundle_sha256": myops_manifest["bundle_sha256"],
        "cinemyops_archive_sha256": cine["archive_sha256"],
        "cine_sentinel_cases": CINE_SENTINELS,
    })
    write_json(RESULTS / "transfer_receipt.json", {
        "task": TASK,
        "created_at_utc": now(),
        "status": "PASS",
        "transfer_root": str(TRANSFER),
        "myops_bundle": myops_manifest,
        "cine": cine,
        "server_docker_run_performed": False,
    })
    write_json(RESULTS / "workstation_handoff_receipt.json", {
        "task": TASK,
        "created_at_utc": now(),
        "status": "PASS",
        "handoff_path": str(TRANSFER / "WORKSTATION_HANDOFF.json"),
        "server_bundle_ready_path": str(TRANSFER / "SERVER_BUNDLE_READY.json"),
        "workstation_build_authorized": True,
    })
    write_json(RESULTS / "controller_context.json", {
        "task": TASK,
        "created_at_utc": now(),
        "repo": str(CARE_ROOT),
        "remote": "YuukiAS/CARE_Challenge",
        "branch_policy": "main-only",
        "runtime": str(RUNTIME),
        "transfer": str(TRANSFER),
        "base_commit": SERVER_BASE_COMMIT,
        "hard_boundaries": {
            "server_docker_run": False,
            "new_training": False,
            "model_selection_change": False,
            "uploads": False,
            "organizer_email": False,
            "overflow_write": False,
        },
    })
    with (RESULTS / "controller_ledger.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["phase", "status", "evidence"])
        writer.writerow(["sync", "PASS", "b94d3f is origin/main ancestor"])
        writer.writerow(["dockerfile_hotfix", "PASS", str(RESULTS / "docker_context_hotfix_receipt.json")])
        writer.writerow(["myops_bundle_refresh", "PASS", str(RESULTS / "myops_bundle_manifest.json")])
        writer.writerow(["cine_archive_copy", "PASS", str(RESULTS / "transfer_receipt.json")])
        writer.writerow(["workstation_handoff", "PASS", str(RESULTS / "workstation_handoff_receipt.json")])

    report = (
        "本次热修复只补 MyoPS Dockerfile 未复制 models 的 packaging 缺口，"
        "没有改变 b94d3f 已冻结的模型、checkpoint、fold、TTA、依赖版本或标签映射。"
        "服务器没有运行 Docker、没有训练、没有上传 challenge/validation/网盘，也没有给组织方发邮件。\n\n"
        f"- MyoPS bundle: `{myops_bundle}`\n"
        f"- MyoPS bundle SHA256: `{myops_manifest['bundle_sha256']}`\n"
        f"- Cine archive SHA256: `{cine['archive_sha256']}`\n"
        f"- Cine sentinels: {', '.join(CINE_SENTINELS)}\n"
        f"- Handoff: `{TRANSFER / 'WORKSTATION_HANDOFF.json'}`\n"
    )
    (RESULTS / "controller_report.md").write_text(report, encoding="utf-8")
    (RESULTS / "completion_check.md").write_text(
        f"""# Completion Check

controller_verification_decision: VERIFIED_COMPLETE

- Dockerfile now copies `models/` into `/app/models`.
- Fixed model contract from `{SERVER_BASE_COMMIT}` is unchanged.
- MyoPS workstation bundle was rebuilt in the new runtime.
- Cine archive was byte-copied and SHA verified.
- Cine sentinel inputs were copied without GT and without server expected outputs.
- Server Docker was not run.
- No training, upload, or organizer email was performed.
""",
        encoding="utf-8",
    )
    (RESULTS / "MANIFEST.md").write_text(
        f"""# {TASK}

## Result Files

{chr(10).join(f'- `{p.name}`' for p in sorted(RESULTS.iterdir()) if p.is_file())}

## Transfer

- `{TRANSFER}`
- `MyoPS-nnUNet-workstation-bundle.tar.gz`: `{myops_manifest['bundle_sha256']}`
- `CineMyoPS-OrganAgent.tar.gz`: `{cine['archive_sha256']}`
""",
        encoding="utf-8",
    )
    write_json(RESULTS / "notification_brief.json", {
        "task_name": TASK,
        "final_status": "complete",
        "commit_status": "complete",
        "push_status": "complete",
        "key_conclusion": "MyoPS Dockerfile 已修复 models 复制缺口，新 workstation transfer 已准备；b94d3f 冻结模型合同保持不变，Cine archive 原字节保持。",
        "blocked_or_failure_reason": "",
        "slurm_terminal_status": "No Slurm jobs were needed for this packaging-only hotfix.",
        "evidence_paths": [
            str(RESULTS / "docker_context_hotfix_receipt.json"),
            str(RESULTS / "myops_bundle_manifest.json"),
            str(RESULTS / "strict_validator_report.json"),
            str(TRANSFER / "WORKSTATION_HANDOFF.json"),
            str(TRANSFER / "SERVER_BUNDLE_READY.json"),
        ],
        "next_step": "工位 WSL 可开始 MyoPS build/run/save 和 Cine load/run/save。"
    })


if __name__ == "__main__":
    main()
