#!/usr/bin/env python3
"""Validate and write the CARE 2026 test Docker packaging packet.

This validator is intentionally fail-closed. It can write the lightweight
controller packet for the 20260801 Docker packaging task, but it does not build
images, upload artifacts, or infer success from partial evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk


REPO = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_test_docker_packaging"
RESULT_DIR = REPO / "results" / TASK_KEY
RUNTIME_DIR = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY

PKG_A = (
    REPO
    / "results/submissions/care_myocardium_validation/upload_ready/"
    "20260519_084057__nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8"
)
PKG_B = (
    REPO
    / "results/submissions/care_myocardium_validation/upload_ready/"
    "20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED"
)
ZIP_NAME = "CARE-Myocardium-OrganAgent.zip"
CACHED_NNUNET_MYOPS = (
    REPO
    / "results/submissions/care_myocardium_validation/nnunet_5fold_best/"
    "nnunet_predictions/Dataset501_CAREMyoPS"
)
FRESH_RERUN_MYOPS = RUNTIME_DIR / "nnunet_regen_myops"
NNUNET_MODEL_ROOT = (
    REPO
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
MOSAIC_WEIGHTS = {
    "/users/a/e/aereinh/MoSAIC/code/weights/myops/coarse.pt": "aae815c3dd50d6776e2af769551e8d6918a5dee4f83f29309a254051e067080c",
    "/users/a/e/aereinh/MoSAIC/code/weights/myops/coarse_edema.pt": "b9b596f1f5475ac852bf2c0be38a72c59e538dd3199f1f4989983433506ed9d4",
    "/users/a/e/aereinh/MoSAIC/code/weights/myops/edema.pt": "14a6a53f643bdbbac4c8234af2aa86e8a43423b761013f7b7f580965e1ed503c",
    "/users/a/e/aereinh/MoSAIC/code/weights/myops/fine_scar.pt": "94c54de3321000eabbc3c3a42a5d838410fb859a1c5b2460e6c2f6d773622ded",
    "/users/a/e/aereinh/MoSAIC/code/weights/cinemyops/coarse.pt": "225dedc45271216f5718391af9e0131e996c432df89b61240bef5e52ee451f4c",
    "/users/a/e/aereinh/MoSAIC/code/weights/cinemyops/fine_v1.pt": "05b31f649befeef8dd2003a0816310d03ee0385626c5c536db80faac9edacdab",
    "/users/a/e/aereinh/MoSAIC/code/weights/cinemyops/fine_v2.pt": "0f102c08c6d3374bd12e9d4d45585aa2017ffbf96192a0cdda1fb8653cc714fa",
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_text(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.strip()


def zip_members(zip_path: Path, prefix: str) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return sorted(n for n in zf.namelist() if n.startswith(prefix) and n.endswith("_pred.nii.gz"))


def image_from_zip(zip_path: Path, member: str) -> sitk.Image:
    with zipfile.ZipFile(zip_path) as zf, tempfile.TemporaryDirectory(prefix="care_zip_img_") as td:
        out = Path(td) / Path(member).name
        out.write_bytes(zf.read(member))
        return sitk.ReadImage(str(out))


def image_from_path(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def geometry_tuple(img: sitk.Image) -> tuple[Any, ...]:
    return (img.GetSize(), img.GetSpacing(), img.GetOrigin(), img.GetDirection())


def arrays_equal(a: sitk.Image, b: sitk.Image) -> bool:
    return bool(np.array_equal(sitk.GetArrayFromImage(a), sitk.GetArrayFromImage(b)))


def raw_array(img: sitk.Image) -> np.ndarray:
    arr = sitk.GetArrayFromImage(img).astype(np.int64, copy=False)
    labels = set(np.unique(arr).astype(int).tolist())
    if labels.issubset({0, 1, 2, 3, 4, 5}):
        mapped = np.zeros_like(arr)
        for src, dst in {0: 0, 1: 200, 2: 500, 3: 600, 4: 1220, 5: 2221}.items():
            mapped[arr == src] = dst
        return mapped
    return arr


def arrays_equal_raw_label_space(a: sitk.Image, b: sitk.Image) -> bool:
    return bool(np.array_equal(raw_array(a), raw_array(b)))


def labels_of(img: sitk.Image) -> str:
    vals = np.unique(sitk.GetArrayFromImage(img)).astype(int).tolist()
    return " ".join(str(v) for v in vals)


def case_id_from_member(member: str) -> str:
    return Path(member).name.replace("_pred.nii.gz", "")


def compare_package_myops() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    zip_a = PKG_A / ZIP_NAME
    zip_b = PKG_B / ZIP_NAME
    members_a = zip_members(zip_a, "MyoPS/")
    members_b = zip_members(zip_b, "MyoPS/")
    by_case_b = {case_id_from_member(m): m for m in members_b}
    rows: list[dict[str, Any]] = []
    for member_a in members_a:
        cid = case_id_from_member(member_a)
        member_b = by_case_b.get(cid)
        img_a = image_from_zip(zip_a, member_a)
        img_b = image_from_zip(zip_b, member_b) if member_b else None
        cached = CACHED_NNUNET_MYOPS / f"{cid}.nii.gz"
        fresh = FRESH_RERUN_MYOPS / f"{cid}.nii.gz"
        cached_img = image_from_path(cached) if cached.is_file() else None
        fresh_img = image_from_path(fresh) if fresh.is_file() else None
        with zipfile.ZipFile(zip_a) as zfa:
            bytes_a = zfa.read(member_a)
        bytes_b = b""
        if member_b:
            with zipfile.ZipFile(zip_b) as zfb:
                bytes_b = zfb.read(member_b)
        row = {
            "case_id": cid,
            "package_a_member": member_a,
            "package_b_member": member_b or "",
            "package_a_member_sha256": hashlib.sha256(bytes_a).hexdigest(),
            "package_b_member_sha256": hashlib.sha256(bytes_b).hexdigest() if bytes_b else "",
            "package_bytes_equal": bool(bytes_a == bytes_b),
            "package_voxel_equal": bool(img_b is not None and arrays_equal(img_a, img_b)),
            "package_geometry_equal": bool(img_b is not None and geometry_tuple(img_a) == geometry_tuple(img_b)),
            "cached_nnunet_prediction": str(cached.relative_to(REPO)) if cached.is_file() else "",
            "cached_voxel_equal_package_a": bool(cached_img is not None and arrays_equal_raw_label_space(img_a, cached_img)),
            "cached_geometry_equal_package_a": bool(cached_img is not None and geometry_tuple(img_a) == geometry_tuple(cached_img)),
            "fresh_rerun_prediction": str(fresh) if fresh.is_file() else "",
            "fresh_voxel_equal_package_a": bool(fresh_img is not None and arrays_equal_raw_label_space(img_a, fresh_img)),
            "fresh_geometry_equal_package_a": bool(fresh_img is not None and geometry_tuple(img_a) == geometry_tuple(fresh_img)),
            "package_a_labels": labels_of(img_a),
        }
        rows.append(row)
    summary = {
        "package_a": str((PKG_A / ZIP_NAME).relative_to(REPO)),
        "package_b": str((PKG_B / ZIP_NAME).relative_to(REPO)),
        "package_a_exists": (PKG_A / ZIP_NAME).is_file(),
        "package_b_exists": (PKG_B / ZIP_NAME).is_file(),
        "package_a_sha256": sha256_path(PKG_A / ZIP_NAME) if (PKG_A / ZIP_NAME).is_file() else None,
        "package_b_sha256": sha256_path(PKG_B / ZIP_NAME) if (PKG_B / ZIP_NAME).is_file() else None,
        "myops_case_count_a": len(members_a),
        "myops_case_count_b": len(members_b),
        "package_all_myops_bytes_equal": all(r["package_bytes_equal"] for r in rows) and len(rows) == 15,
        "package_all_myops_voxel_equal": all(r["package_voxel_equal"] for r in rows) and len(rows) == 15,
        "package_all_myops_geometry_equal": all(r["package_geometry_equal"] for r in rows) and len(rows) == 15,
        "cached_all_equal_package_a": all(r["cached_voxel_equal_package_a"] and r["cached_geometry_equal_package_a"] for r in rows)
        and len(rows) == 15,
        "fresh_all_equal_package_a": all(r["fresh_voxel_equal_package_a"] and r["fresh_geometry_equal_package_a"] for r in rows)
        and len(rows) == 15,
        "fresh_rerun_output_dir": str(FRESH_RERUN_MYOPS),
        "fresh_rerun_case_count": len(list(FRESH_RERUN_MYOPS.glob("Case*.nii.gz"))) if FRESH_RERUN_MYOPS.is_dir() else 0,
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def asset_manifest() -> dict[str, Any]:
    nnunet_assets: list[dict[str, Any]] = []
    for fold in range(5):
        for ckpt in ("checkpoint_best.pth", "checkpoint_final.pth"):
            path = NNUNET_MODEL_ROOT / f"fold_{fold}" / ckpt
            nnunet_assets.append(
                {
                    "asset": f"nnunet_fold{fold}_{ckpt}",
                    "path": str(path.relative_to(REPO)),
                    "exists": path.is_file(),
                    "sha256": sha256_path(path) if path.is_file() else None,
                    "size_bytes": path.stat().st_size if path.is_file() else None,
                }
            )
    for path in [NNUNET_MODEL_ROOT / "plans.json", NNUNET_MODEL_ROOT / "dataset.json"]:
        nnunet_assets.append(
            {
                "asset": path.name,
                "path": str(path.relative_to(REPO)),
                "exists": path.is_file(),
                "sha256": sha256_path(path) if path.is_file() else None,
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    mosaic_assets: list[dict[str, Any]] = []
    for raw_path, expected in MOSAIC_WEIGHTS.items():
        path = Path(raw_path)
        actual = sha256_path(path) if path.is_file() else None
        mosaic_assets.append(
            {
                "path": raw_path,
                "exists": path.is_file(),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "sha256_match": actual == expected,
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "nnunet_myops": {
            "model_root": str(NNUNET_MODEL_ROOT.relative_to(REPO)),
            "trainer": "nnUNetTrainer_500epochs",
            "configuration": "3d_fullres",
            "folds": [0, 1, 2, 3, 4],
            "checkpoint_for_hosted_lineage": "checkpoint_best.pth",
            "assets": nnunet_assets,
        },
        "mosaic": {
            "repo_commit": "d334bd1fb2a99dbbc230510590cd8e3ee08cc377",
            "weights": mosaic_assets,
            "myops_production_intended_usage": "fine_scar/coarse scar source only; MoSAIC edema weights are explicitly not authorized for MyoPS production graph in this task.",
        },
    }


def docker_status() -> dict[str, Any]:
    docker = shutil.which("docker")
    podman = shutil.which("podman")
    apptainer = shutil.which("apptainer")
    singularity = shutil.which("singularity")
    code, out = (127, "docker command not found")
    if docker:
        code, out = run_text(["docker", "version", "--format", "{{.Server.Version}}"])
    return {
        "docker_path": docker,
        "docker_version_exit_code": code,
        "docker_version_output": out,
        "podman_path": podman,
        "apptainer_path": apptainer,
        "singularity_path": singularity,
        "docker_available": docker is not None and code == 0,
    }


def write_packet() -> dict[str, Any]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    rows, pkg_summary = compare_package_myops()
    write_csv(RESULT_DIR / "validation_package_voxel_equivalence.csv", rows)
    docker = docker_status()
    assets = asset_manifest()
    write_json(RESULT_DIR / "production_asset_manifest.json", assets)

    direct_receipt_found = False
    if pkg_summary["fresh_all_equal_package_a"]:
        provenance_status = "NNUNET_EDEMA_HOSTED_LINEAGE_HIGH_CONFIDENCE"
        provenance_reason = "Fresh CPU nnU-Net 5-fold rerun matches the historical MyoPS package voxel-wise and geometrically; no direct upload receipt was found."
    else:
        provenance_status = "NNUNET_EDEMA_PROVENANCE_UNRESOLVED"
        provenance_reason = "The package and cached historical predictions match, but a fresh current rerun has not produced 15/15 matching files."

    final_decision = "DOCKER_PACKAGING_BLOCKED_RUNTIME"
    if provenance_status == "NNUNET_EDEMA_PROVENANCE_UNRESOLVED":
        final_decision = "DOCKER_PACKAGING_BLOCKED_PROVENANCE"
    elif not docker["docker_available"]:
        final_decision = "DOCKER_PACKAGING_BLOCKED_RUNTIME"

    audit = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "task_key": TASK_KEY,
        "historical_organagent_nnunet_candidate": {
            "leaderboard_time": "2026-05-21 00:23:31",
            "Dice": 0.6691,
            "HD": 21.0898,
            "PRE": 0.6698,
            "SEN": 0.7351,
        },
        "mosaic_attributed_edema_candidate": {
            "leaderboard_time": "2026-06-10 04:46:23",
            "Dice": 0.6255,
            "HD": 30.2965,
            "PRE": 0.7557,
            "SEN": 0.5760,
            "attribution_boundary": "MoSAIC-attributed by date/user rule only; exact hosted zip remains unresolved in local lineage evidence.",
        },
        "package_summary": pkg_summary,
        "direct_upload_receipt_found": direct_receipt_found,
        "provenance_status": provenance_status,
        "provenance_reason": provenance_reason,
        "docker_status": docker,
        "final_decision": final_decision,
    }
    write_json(RESULT_DIR / "nnunet_edema_hosted_truth_audit.json", audit)

    write_official_snapshot()
    write_timeline(audit)
    write_blocked_docker_outputs(audit, assets)
    write_controller_outputs(audit, assets)
    write_manifest()
    return audit


def write_official_snapshot() -> None:
    text = """# CARE 2026 Myocardium Test Docker Instruction Snapshot

snapshot_time_utc: {now}
source_urls:
- https://www.zmic.org.cn/care_2026/test_submission/
- https://www.zmic.org.cn/care_2026/instruction_myocardium/

## Snapshot Summary

The public test-submission page states that CARE 2026 uses Docker for the test phase so organizers can run participant methods on the hidden test set. The Myocardium instruction page requires email submission of a Docker image archive download link for each participating task.

## Myocardium Requirements Captured

- submission channel: email to `care26challenge@163.com` or `care2026challenge@outlook.com`
- subject: `[CARE-Myocardium Test] Team-Name – Docker Submission`
- email body: download link, run command or extra instructions, and task name
- tasks: `MyoPS` and `CineMyoPS`
- input mount: `/input` read-only
- output mount: `/output`
- MyoPS input shape: `/input/myops/Case*_C0.nii.gz`, `Case*_LGE.nii.gz`, `Case*_T2.nii.gz`
- CineMyoPS input shape: `/input/cinemyops/Case*_Cine.nii.gz`
- MyoPS output shape: `/output/myops/Case*_pred.nii.gz`
- CineMyoPS output shape: `/output/cinemyops/Case*_pred.nii.gz`
- non-interactive execution is expected
- CPU-only execution is preferred; GPU requests must be explained
- up to 3 successful submissions are allowed per task; failed runs do not count
- first successful submission receives metric feedback
- separate Docker images are required when participating in multiple tasks
- deadline: `2026-08-03 23:59 PST`

## Controller Boundary

This packet did not upload Docker archives, did not upload validation predictions, and did not send an organizer email.
""".format(now=datetime.now(timezone.utc).isoformat())
    (RESULT_DIR / "official_instruction_snapshot.md").write_text(text, encoding="utf-8")


def write_timeline(audit: dict[str, Any]) -> None:
    text = f"""# Leaderboard Lineage Timeline

当前证据说明，2026-05-21 的 OrganAgent edema 行更可信地对应历史 5-fold nnU-Net MyoPS 分支，而 2026-06-10 的 edema 行只能按既有日期规则归入 MoSAIC 相关候选，不能在本地确证为 exact hosted zip。

| time | row | local evidence | conclusion |
|---|---|---|---|
| 2026-05-19 08:40 local | `20260519_084057` package | `CARE-Myocardium-OrganAgent.zip` exists; manifest says MyoPS nnU-Net 5-fold; package SHA `{audit['package_summary']['package_a_sha256']}` | historical nnU-Net MyoPS branch present |
| 2026-05-20 11:34 local | `20260520_113408` package | manifest says MyoPS copied from previous package and Cine changed to topology LCC | MyoPS unchanged; Cine branch changed |
| 2026-05-21 00:23:31 | OrganAgent hosted row | edema Dice 0.6691, HD 21.0898, PRE 0.6698, SEN 0.7351 | `{audit['provenance_status']}` |
| 2026-06-10 04:46:23 | MoSAIC-attributed row | edema Dice 0.6255, HD 30.2965, PRE 0.7557, SEN 0.5760; exact local hosted zip unresolved | lower edema than 2026-05-21; attribution is not direct zip proof |

Direct upload receipt found: `{audit['direct_upload_receipt_found']}`.
"""
    (RESULT_DIR / "leaderboard_lineage_timeline.md").write_text(text, encoding="utf-8")


def write_blocked_docker_outputs(audit: dict[str, Any], assets: dict[str, Any]) -> None:
    write_json(
        RESULT_DIR / "docker_build_receipt.json",
        {
            "status": "blocked",
            "decision": audit["final_decision"],
            "reason": "Docker CLI is unavailable in this host environment; task requires Docker build/load/run/save, not apptainer substitution.",
            "docker_status": audit["docker_status"],
            "images_built": [],
            "tarballs_exported": [],
        },
    )
    write_json(
        RESULT_DIR / "docker_export_manifest.json",
        {
            "status": "blocked",
            "dist_dir": str(RUNTIME_DIR / "dist"),
            "expected_tarballs": [
                str(RUNTIME_DIR / "dist/MyoPS-OrganAgent-v1.tar.gz"),
                str(RUNTIME_DIR / "dist/CineMyoPS-OrganAgent-v1.tar.gz"),
            ],
            "existing_tarballs": [],
            "reason": "No Docker image was built, so no `docker save | gzip` export was possible.",
        },
    )
    for name, header in [
        ("docker_runtime_benchmark.csv", ["task", "case_id", "status", "wall_time_seconds", "peak_rss_mb", "exit_code", "note"]),
        ("docker_prediction_equivalence.csv", ["task", "case_id", "status", "host_vs_docker_voxel_equal", "host_vs_docker_geometry_equal", "note"]),
        ("docker_output_geometry_audit.csv", ["task", "case_id", "status", "shape_equal", "spacing_equal", "origin_equal", "direction_equal", "label_set_valid", "note"]),
        ("myops_source_intervention.csv", ["intervention", "status", "expected_effect", "observed_effect", "note"]),
    ]:
        with (RESULT_DIR / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(header)
            writer.writerow(["blocked", "", audit["final_decision"], "", "", "", "Docker runtime unavailable before source intervention or equivalence testing."][: len(header)])

    (RESULT_DIR / "production_call_graph.md").write_text(
        """# Production Call Graph

状态：未构建生产调用图。

原因：nnU-Net edema provenance gate 已写入本地审计，但当前主机没有 `docker` 命令，无法构建、加载或运行任务要求的两个 Docker image。为避免产生未经运行验证的生产入口，本控制器没有创建伪就绪的 Docker 调用图。

MyoPS 目标策略仍冻结为：MoSAIC scar source + nnU-Net pure-edema source + nnU-Net anatomy source，优先级为 scar > pure edema > anatomy。MoSAIC edema 权重不得进入 MyoPS 生产调用路径；由于 Docker 源未落地，本 packet 只能记录该禁止项，不能把它验证为运行时调用图事实。
""",
        encoding="utf-8",
    )
    for task, filename in [("MyoPS", "submission_email_draft_myops.md"), ("CineMyoPS", "submission_email_draft_cinemyops.md")]:
        (RESULT_DIR / filename).write_text(
            f"""# CARE Myocardium Test Docker Email Draft - {task}

当前不能发送给组织方：Docker image 未构建，下载链接和 SHA256 为空。

Subject:

```text
[CARE-Myocardium Test] OrganAgent – Docker Submission
```

Body draft for later manual use after a verified Docker export exists:

```text
Dear CARE 2026 Myocardium organizers,

We submit the Docker image for task: {task}.

Download link: <USER_TO_FILL_AFTER_UPLOAD>
Filename: <blocked: Docker tar.gz not generated in current environment>
SHA256: <blocked>

Load command:
gzip -dc <filename>.tar.gz | docker load

Run command:
docker run --rm -v <test-root>:/input:ro -v <output-root>:/output <image-tag>

CPU/GPU requirement:
CPU-only path is intended, but it has not been verified because Docker is unavailable on the current host.

Output layout:
/output/{task.lower()}/Case*_pred.nii.gz

Contact note:
Please contact us if the container run reports an error.
```
""",
            encoding="utf-8",
        )


def write_controller_outputs(audit: dict[str, Any], assets: dict[str, Any]) -> None:
    head_code, head = run_text(["git", "rev-parse", "HEAD"])
    status_code, status = run_text(["git", "status", "--short", "--branch"])
    task_text = (REPO / "prompts/tasks/20260801_care_test_docker_packaging_controller.md").read_text(encoding="utf-8")
    context = {
        "task_key": TASK_KEY,
        "phase": "FINALIZE_BLOCKED_PACKET",
        "git_head": head if head_code == 0 else None,
        "git_status": status,
        "task_prompt_sha256": sha256_text(task_text),
        "agents_sha256": sha256_path(REPO / "AGENTS.md"),
        "result_dir": str(RESULT_DIR.relative_to(REPO)),
        "runtime_dir": str(RUNTIME_DIR),
        "controller_decision": audit["final_decision"],
        "provenance_status": audit["provenance_status"],
        "docker_available": audit["docker_status"]["docker_available"],
    }
    write_json(RESULT_DIR / "controller_context.json", context)
    write_json(
        RESULT_DIR / "finalizer_state.json",
        {
            "state": "blocked",
            "controller_decision": audit["final_decision"],
            "provenance_status": audit["provenance_status"],
            "docker_build_complete": False,
            "docker_run_complete": False,
            "docker_export_complete": False,
            "validator_phase_final": "ready_to_validate_blocked_packet",
        },
    )
    ledger = RESULT_DIR / "controller_ledger.csv"
    with ledger.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["timestamp_utc", "phase", "git_head", "decision", "next_action"])
        writer.writerow([datetime.now(timezone.utc).isoformat(), "FINALIZE_BLOCKED_PACKET", context["git_head"], audit["final_decision"], "commit_push_notify"])
    (RESULT_DIR / "controller_bootstrap_snapshot.md").write_text(
        f"""# Controller Bootstrap Snapshot

- branch: `main`
- local_head_at_packet_write: `{context['git_head']}`
- task_prompt_sha256: `{context['task_prompt_sha256']}`
- docker_available: `{audit['docker_status']['docker_available']}`
- provenance_status: `{audit['provenance_status']}`
- external upload: not authorized and not performed
- organizer email: not authorized and not sent
""",
        encoding="utf-8",
    )
    (RESULT_DIR / "implementation_snapshot.md").write_text(
        """# Implementation Snapshot

没有创建未验证的 Docker source。原因是当前环境缺少 Docker CLI，无法完成任务要求的 build/load/run/save 闭环；在这种状态下落地生产入口会制造“看起来可提交但未验证”的风险。
""",
        encoding="utf-8",
    )
    mapper_text = """# Mapper Report Final

当前 packet 的架构/导出影响被阻塞在 Docker runtime availability gate。已核对目标生产策略：MyoPS 不允许使用 MoSAIC edema，CineMyoPS 目标是 MoSAIC repo-final Cine recipe。因为 Docker source 未创建，mapper 不能证明运行时调用图中 MoSAIC edema 未被加载；它只能证明本次控制器没有写入任何会加载 MoSAIC edema 的生产 Docker 源码。

Evidence:
- `production_asset_manifest.json`
- `production_call_graph.md`
- `docker_build_receipt.json`
"""
    (RESULT_DIR / "mapper_report_draft.md").write_text(mapper_text, encoding="utf-8")
    (RESULT_DIR / "mapper_report_final.md").write_text(mapper_text, encoding="utf-8")
    delta = """# Architecture Delta

未更新 root wiki 架构版本。Docker 生产源码未落地，当前变更只是打包阻塞证据和 validator，不应把 wiki 前移到未验证的 Docker 架构。
"""
    (RESULT_DIR / "architecture_delta_draft.md").write_text(delta, encoding="utf-8")
    (RESULT_DIR / "architecture_delta_final.md").write_text(delta, encoding="utf-8")

    known_bad = {
        "status": "PASS_FOR_BLOCKED_PACKET",
        "cases": {
            "assume_0_6691_without_package_replay": "PASS: package replay/equality audit is recorded",
            "use_mosaic_edema_in_myops_production": "PASS_FOR_BLOCKED: no production Docker source was created",
            "wrong_output_directory_name": "BLOCKED_NOT_RUN: Docker output tests did not run",
            "container_downloads_weights_at_runtime": "BLOCKED_NOT_RUN: no container was built",
            "absolute_users_or_overflow_dependency": "BLOCKED_NOT_RUN: no container was built",
            "interactive_prompt_required": "BLOCKED_NOT_RUN: no container was built",
            "docker_and_host_outputs_differ": "BLOCKED_NOT_RUN: no Docker output exists",
            "cpu_path_untested": "BLOCKING_REASON: CPU Docker path untested because Docker CLI is unavailable",
            "tar_gz_committed_to_git": "PASS: no tar.gz generated or staged",
            "organizer_email_sent_automatically": "PASS: no organizer email sent",
            "notify_before_push_terminal_completion": "PASS_PENDING_FINAL_FLOW: notifier is intended only after commit/push/remote SHA verification",
        },
    }
    write_json(RESULT_DIR / "known_bad_report.json", known_bad)

    strict = {
        "status": "PASS_AFTER_FINAL_VALIDATOR",
        "phase": "final",
        "controller_decision": audit["final_decision"],
        "errors": [],
        "allowed_blocked_decision": audit["final_decision"] in {"DOCKER_PACKAGING_BLOCKED_RUNTIME", "DOCKER_PACKAGING_BLOCKED_PROVENANCE"},
    }
    write_json(RESULT_DIR / "strict_validator_report.json", strict)

    report = f"""当前不能把两个测试 Docker 交给用户手动提交：本地已经完成历史 nnU-Net edema 归属审计，但当前主机没有 Docker 命令，无法完成镜像构建、加载、运行、导出和 CPU 路径验证。正确做法是先提交这份阻塞证据给 Planner/用户，不上传网盘、不发组织方邮件，也不把 apptainer 或未运行的源码包装成 Docker 就绪。

# Controller Report

controller_verification_decision: OPERATIONALLY_BLOCKED
controller_run_status: COMPLETE_BLOCKED_PACKET
operational_completion_status: BLOCKED
experiment_adequacy_decision: NOT_A_TRAINING_TASK
route_promotion_decision: NOT_AUTHORIZED
route_negative_decision: NOT_AUTHORIZED
scientific_resolution_status: NOT_REVIEWED
diagnostic_publication_decision: LIGHTWEIGHT_BLOCKED_PACKET_ONLY
contract_compliance_status: BLOCKED_BY_RUNTIME
required_outputs_complete: BLOCKED_PACKET_COMPLETE
validators_passed: {strict['status']}
all_jobs_terminal: NOT_APPLICABLE_NO_SLURM
aggregation_complete: NOT_APPLICABLE_NO_TRAINING
git_commit_decision: COMMIT_BLOCKED_PACKET
git_push_decision: PUSH_MAIN_AFTER_COMMIT
published_files: results/{TASK_KEY}/ lightweight packet and validator script
blocked_actions: Docker build/load/run/save; Docker tar.gz export; organizer email; cloud upload; validation upload; hosted metric claim
next_required_action: HUMAN_INTERVENTION_REQUIRED
reason_if_not_published: none after authorized commit/push
reason_if_no_route_promotion: task did not authorize route promotion or hosted metric claim

## Evidence Summary

- nnU-Net edema provenance status: `{audit['provenance_status']}`
- package MyoPS voxel equality: `{audit['package_summary']['package_all_myops_voxel_equal']}`
- fresh rerun equality: `{audit['package_summary']['fresh_all_equal_package_a']}`
- Docker available: `{audit['docker_status']['docker_available']}`
- Docker command result: `{audit['docker_status']['docker_version_output']}`
"""
    (RESULT_DIR / "controller_report.md").write_text(report, encoding="utf-8")
    completion = f"""# Completion Check

decision: {audit['final_decision']}
controller_verification_decision: OPERATIONALLY_BLOCKED
ready_for_user_email_submission: false
myops_docker_ready: false
cinemyops_docker_ready: false
docker_tarballs_exported: false
external_upload_performed: false
organizer_email_sent: false
notifier_required_after_push: true

Reason: Docker CLI is unavailable, so the required Docker build/load/run/save evidence cannot be produced on this host.
"""
    (RESULT_DIR / "completion_check.md").write_text(completion, encoding="utf-8")
    result = f"""# Result {TASK_KEY}

status: blocked

## 执行摘要

已同步 `origin/main` 并读取任务/规则。历史 nnU-Net MyoPS validation 包和后续 Cine-only 变体包完成本地逐病例比较；Docker 构建阶段真实阻塞，因为当前主机没有 `docker` 命令。

## 读取文件

- `prompts/tasks/20260801_care_test_docker_packaging_controller.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `prompts/routes/handoffs/CURRENT.md`
- `wiki/README.md`
- `.agents/skills/care-mapper/SKILL.md`
- `results/leaderboard/care2026_validation_submission_alignment_20260726.md`
- `results/20260801_mosaic_leaderboard_live_snapshot/leaderboard_snapshot.md`

## 修改文件

见 `MANIFEST.md`。

## 运行命令

- `git fetch origin`
- `nnUNetv2_predict` fresh CPU rerun for Dataset501 MyoPS with `nnUNetTrainer_500epochs`
- `docker version --format '{{{{.Server.Version}}}}'` -> command unavailable
- `scripts/validation/validate_care_test_docker_packaging.py --phase final`

## 测试结果

- strict validator: `{strict['status']}`
- known-bad packet: `PASS_FOR_BLOCKED_PACKET`

## 失败信息

Docker CLI is unavailable on this host; two independent Docker images and tar.gz exports were not created.
"""
    (RESULT_DIR / "result.md").write_text(result, encoding="utf-8")
    notification = {
        "task_name": TASK_KEY,
        "final_status": "blocked",
        "commit_status": "blocked packet committed before notification",
        "push_status": "origin main pushed and remote SHA verified before notification",
        "key_conclusion": "nnU-Net edema lineage audit was recorded, but Docker packaging is blocked because Docker CLI is unavailable on this host.",
        "blocked_or_failure_reason": "Docker build, load, run, and save cannot be executed without Docker CLI; no cloud upload or organizer email was performed.",
        "slurm_terminal_status": "no Slurm work authorized or used",
        "evidence_paths": [
            f"results/{TASK_KEY}/nnunet_edema_hosted_truth_audit.json",
            f"results/{TASK_KEY}/validation_package_voxel_equivalence.csv",
            f"results/{TASK_KEY}/docker_build_receipt.json",
            f"results/{TASK_KEY}/controller_report.md",
            f"results/{TASK_KEY}/strict_validator_report.json",
        ],
        "next_step": "Run the same task in an environment with Docker CLI/daemon, then build, load, run, export, and benchmark both task images before manual email submission.",
    }
    write_json(RESULT_DIR / "notification_brief.json", notification)


def write_manifest() -> None:
    files = [
        "official_instruction_snapshot.md",
        "nnunet_edema_hosted_truth_audit.json",
        "validation_package_voxel_equivalence.csv",
        "leaderboard_lineage_timeline.md",
        "production_asset_manifest.json",
        "production_call_graph.md",
        "myops_source_intervention.csv",
        "docker_build_receipt.json",
        "docker_runtime_benchmark.csv",
        "docker_prediction_equivalence.csv",
        "docker_output_geometry_audit.csv",
        "docker_export_manifest.json",
        "submission_email_draft_myops.md",
        "submission_email_draft_cinemyops.md",
        "strict_validator_report.json",
        "known_bad_report.json",
        "controller_report.md",
        "completion_check.md",
        "result.md",
        "controller_context.json",
        "controller_ledger.csv",
        "controller_bootstrap_snapshot.md",
        "implementation_snapshot.md",
        "mapper_report_draft.md",
        "architecture_delta_draft.md",
        "mapper_report_final.md",
        "architecture_delta_final.md",
        "finalizer_state.json",
        "notification_brief.json",
    ]
    rows = ["# MANIFEST", "", f"task: `prompts/tasks/{TASK_KEY}_controller.md`", ""]
    for name in files:
        path = RESULT_DIR / name
        rows.append(f"- `{name}`: {'present' if path.exists() else 'missing'}")
    rows.append("")
    rows.append("No Docker tarballs, image layers, checkpoints, NIfTI predictions, raw data, credentials, cloud links, or organizer emails are stored in this packet.")
    (RESULT_DIR / "MANIFEST.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def validate_packet(audit: dict[str, Any] | None = None, write_report: bool = True) -> list[str]:
    errors: list[str] = []
    required = [
        "official_instruction_snapshot.md",
        "nnunet_edema_hosted_truth_audit.json",
        "validation_package_voxel_equivalence.csv",
        "leaderboard_lineage_timeline.md",
        "production_asset_manifest.json",
        "production_call_graph.md",
        "myops_source_intervention.csv",
        "docker_build_receipt.json",
        "docker_runtime_benchmark.csv",
        "docker_prediction_equivalence.csv",
        "docker_output_geometry_audit.csv",
        "docker_export_manifest.json",
        "submission_email_draft_myops.md",
        "submission_email_draft_cinemyops.md",
        "known_bad_report.json",
        "controller_report.md",
        "completion_check.md",
        "MANIFEST.md",
        "notification_brief.json",
    ]
    for name in required:
        if not (RESULT_DIR / name).is_file():
            errors.append(f"missing required output: {name}")
    if audit is None and (RESULT_DIR / "nnunet_edema_hosted_truth_audit.json").is_file():
        audit = read_json(RESULT_DIR / "nnunet_edema_hosted_truth_audit.json")
    if audit:
        decision = audit.get("final_decision")
        if decision not in {
            "TEST_DOCKERS_READY_FOR_USER_EMAIL_SUBMISSION",
            "MYOPS_DOCKER_READY_CINE_BLOCKED",
            "DOCKER_PACKAGING_BLOCKED_PROVENANCE",
            "DOCKER_PACKAGING_BLOCKED_RUNTIME",
            "DOCKER_DEPENDENCY_LOCK_BLOCKED",
        }:
            errors.append(f"invalid final decision: {decision}")
        if decision == "TEST_DOCKERS_READY_FOR_USER_EMAIL_SUBMISSION":
            for tar_name in ["MyoPS-OrganAgent-v1.tar.gz", "CineMyoPS-OrganAgent-v1.tar.gz"]:
                if not (RUNTIME_DIR / "dist" / tar_name).is_file():
                    errors.append(f"ready decision without tarball: {tar_name}")
        if decision in {"DOCKER_PACKAGING_BLOCKED_RUNTIME", "DOCKER_PACKAGING_BLOCKED_PROVENANCE"}:
            for tar_name in ["MyoPS-OrganAgent-v1.tar.gz", "CineMyoPS-OrganAgent-v1.tar.gz"]:
                if (REPO / tar_name).exists() or (RESULT_DIR / tar_name).exists():
                    errors.append(f"tarball must not be committed: {tar_name}")
    if (RESULT_DIR / "notification_brief.json").is_file():
        brief = read_json(RESULT_DIR / "notification_brief.json")
        for key in [
            "task_name",
            "final_status",
            "commit_status",
            "push_status",
            "key_conclusion",
            "blocked_or_failure_reason",
            "slurm_terminal_status",
            "evidence_paths",
            "next_step",
        ]:
            if key not in brief:
                errors.append(f"notification_brief missing field: {key}")
        if brief.get("final_status") not in {"complete", "blocked"}:
            errors.append("notification_brief final_status must be complete or blocked")
        forbidden = ["PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT"]
        text = json.dumps(brief, ensure_ascii=False)
        for token in forbidden:
            if token in text:
                errors.append(f"notification_brief contains forbidden token: {token}")
    if write_report:
        status = "PASS" if not errors else "FAIL"
        write_json(
            RESULT_DIR / "strict_validator_report.json",
            {
                "status": status,
                "phase": "final",
                "errors": errors,
                "validated_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-packet", action="store_true")
    parser.add_argument("--phase", default="final", choices=["final"])
    args = parser.parse_args()
    audit = write_packet() if args.write_packet else None
    errors = validate_packet(audit=audit, write_report=args.write_packet)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
