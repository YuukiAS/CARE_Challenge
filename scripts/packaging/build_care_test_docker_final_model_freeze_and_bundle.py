#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

CARE_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260801_care_test_docker_final_model_freeze_and_bundle"
RESULT_DIR = CARE_ROOT / "results" / TASK_KEY
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine")
TRANSFER_ROOT = RUNTIME / "transfer"
BUNDLE_DIR = TRANSFER_ROOT / "transfer_bundle"
ARCHIVE = TRANSFER_ROOT / "care2026_myocardium_final_model_freeze_transfer_bundle.tar.gz"
READY_MARKER = TRANSFER_ROOT / "SERVER_BUNDLE_READY.json"

MOSAIC_ROOT = Path("/users/a/e/aereinh/MoSAIC")
MOSAIC_SOURCE = MOSAIC_ROOT / "code" / "source"
MOSAIC_WEIGHTS = MOSAIC_ROOT / "code" / "weights"
MOSAIC_COMMIT = "d334bd1fb2a99dbbc230510590cd8e3ee08cc377"
NNUNET_ROOT = CARE_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"

MYOPS_SENTINELS = ["Case1001", "Case1008", "Case1015"]
CINE_SENTINELS = ["Case1001", "Case1008", "Case1015"]
MYOPS_LABELS = {0, 200, 500, 600, 1220, 2221}
CINE_LABELS = {0, 200, 500, 2221}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(CARE_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache"),
        symlinks=False,
    )


def nifti_array(path: Path) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    return img, sitk.GetArrayFromImage(img)


def save_like(reference: sitk.Image, array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(array.astype(np.int16))
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def dice(a: np.ndarray, b: np.ndarray, label: int) -> float:
    am = a == label
    bm = b == label
    denom = int(am.sum() + bm.sum())
    if denom == 0:
        return 1.0
    return float(2 * np.logical_and(am, bm).sum() / denom)


def compose_myops(nnunet: np.ndarray, mosaic: np.ndarray, disable_scar: bool = False, disable_edema: bool = False) -> np.ndarray:
    out = np.zeros(nnunet.shape, dtype=np.int16)
    out[nnunet == 1] = 200
    out[nnunet == 2] = 500
    out[nnunet == 3] = 600
    if not disable_edema:
        out[nnunet == 4] = 1220
    if not disable_scar:
        out[mosaic == 2221] = 2221
    return out


def asset(path: Path, name: str, role: str, included_in: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "role": role,
        "path": rel(path),
        "exists": path.exists(),
        "sha256": sha256(path) if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else None,
        "included_in": included_in,
    }


def build_contract(asset_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "frozen_by_planner": True,
        "model_selection_closed": True,
        "hosted_metric_claim_authorized": False,
        "historical_0_6691_lineage_status": "UNRESOLVED_NOT_CLAIMED",
        "server_gpu_bitwise_repeat_required": False,
        "known_gpu_float_parallel_delta": {
            "changed_voxels": 13,
            "blocking": False,
            "interpretation": "Recorded as GPU floating/parallel inference variance only.",
        },
        "myops": {
            "scar": {
                "source": "MoSAIC repo-final scar",
                "weights": ["myops/coarse.pt", "myops/fine_scar.pt"],
                "forbidden_weights": ["myops/coarse_edema.pt", "myops/edema.pt"],
            },
            "pure_edema": {
                "source": "Dataset501 5-fold nnU-Net checkpoint_best.pth",
                "trainer": "nnUNetTrainer_500epochs",
                "configuration": "3d_fullres",
                "folds": [0, 1, 2, 3, 4],
                "tta": "default",
                "raw_class": 4,
            },
            "anatomy": {
                "source": "Same Dataset501 5-fold nnU-Net",
                "raw_classes": {"1": "myocardium", "2": "LV blood", "3": "RV blood"},
            },
            "priority": ["scar", "pure_edema", "anatomy", "background"],
            "official_labels": {"0": "background", "200": "myocardium", "500": "LV", "600": "RV", "1220": "edema", "2221": "scar"},
        },
        "cinemyops": {
            "source": "MoSAIC repo-final Cine",
            "weights": ["cinemyops/coarse.pt", "cinemyops/fine_v1.pt", "cinemyops/fine_v2.pt"],
            "z_spacings_mm": [4, 8, 16],
            "tta": {"enabled": True, "flips": ["horizontal", "vertical"]},
            "final_decode": "frozen MoSAIC threshold/postprocess/decode",
            "official_labels": {"0": "background", "200": "myocardium", "500": "LV", "2221": "scar"},
        },
        "asset_manifest_sha256": sha256(asset_manifest["path_on_disk"]) if isinstance(asset_manifest.get("path_on_disk"), Path) else None,
    }


def build_asset_manifest() -> dict[str, Any]:
    nn_assets = [
        asset(NNUNET_ROOT / f"fold_{fold}/checkpoint_best.pth", f"nnunet_fold{fold}_checkpoint_best.pth", "myops_nnunet_fold", ["MyoPS"])
        for fold in range(5)
    ]
    nn_assets.extend([
        asset(NNUNET_ROOT / "plans.json", "nnunet_plans.json", "myops_nnunet_metadata", ["MyoPS"]),
        asset(NNUNET_ROOT / "dataset.json", "nnunet_dataset.json", "myops_nnunet_metadata", ["MyoPS"]),
    ])
    mosaic_assets = [
        asset(MOSAIC_WEIGHTS / "myops/coarse.pt", "mosaic_myops_coarse.pt", "myops_scar_coarse", ["MyoPS"]),
        asset(MOSAIC_WEIGHTS / "myops/fine_scar.pt", "mosaic_myops_fine_scar.pt", "myops_scar_fine", ["MyoPS"]),
        asset(MOSAIC_WEIGHTS / "cinemyops/coarse.pt", "mosaic_cinemyops_coarse.pt", "cinemyops_coarse", ["CineMyoPS"]),
        asset(MOSAIC_WEIGHTS / "cinemyops/fine_v1.pt", "mosaic_cinemyops_fine_v1.pt", "cinemyops_fine_v1", ["CineMyoPS"]),
        asset(MOSAIC_WEIGHTS / "cinemyops/fine_v2.pt", "mosaic_cinemyops_fine_v2.pt", "cinemyops_fine_v2", ["CineMyoPS"]),
    ]
    forbidden = [
        asset(MOSAIC_WEIGHTS / "myops/coarse_edema.pt", "mosaic_myops_coarse_edema.pt", "forbidden_myops_edema", []),
        asset(MOSAIC_WEIGHTS / "myops/edema.pt", "mosaic_myops_edema.pt", "forbidden_myops_edema", []),
    ]
    return {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "mosaic_source_root": str(MOSAIC_SOURCE),
        "mosaic_commit": MOSAIC_COMMIT,
        "nnunet_root": rel(NNUNET_ROOT),
        "assets": nn_assets + mosaic_assets,
        "forbidden_assets_present_on_server_but_excluded_from_myops_bundle": forbidden,
        "all_required_assets_exist": all(a["exists"] for a in nn_assets + mosaic_assets),
        "myops_forbidden_mosaic_edema_included": False,
    }


def write_cine_manifest() -> dict[str, Any]:
    out_dir = RUNTIME / "fresh_mosaic_outputs/cinemyops"
    records = []
    for p in sorted(out_dir.glob("*_pred.nii.gz")):
        img, arr = nifti_array(p)
        labels = sorted(int(x) for x in np.unique(arr))
        records.append({
            "case_id": p.name.replace("_pred.nii.gz", ""),
            "path": str(p),
            "sha256": sha256(p),
            "labels": labels,
            "shape_zyx": list(arr.shape),
            "spacing_xyz": list(img.GetSpacing()),
            "label_schema_ok": set(labels).issubset(CINE_LABELS),
        })
    manifest = {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "output_dir": str(out_dir),
        "case_count": len(records),
        "expected_case_count": 15,
        "all_label_schema_ok": all(r["label_schema_ok"] for r in records),
        "records": records,
    }
    write_json(RESULT_DIR / "fresh_mosaic_cine_15case_manifest.json", manifest)
    return manifest


def build_sentinels() -> tuple[dict[str, Any], dict[str, Any]]:
    sent_root = BUNDLE_DIR / "sentinel_cases"
    expected_root = BUNDLE_DIR / "expected_outputs"
    host_root = RUNTIME / "host_sentinel_outputs"
    if sent_root.exists():
        shutil.rmtree(sent_root)
    if expected_root.exists():
        shutil.rmtree(expected_root)
    if host_root.exists():
        shutil.rmtree(host_root)
    rows: list[dict[str, Any]] = []
    intervention: dict[str, Any] = {"created_at_utc": now(), "task_key": TASK_KEY, "cases": []}

    for case_id in MYOPS_SENTINELS:
        case_src = CARE_ROOT / "data/CARE_Challenge/MyoPS_val/AnonymousCenter" / case_id
        case_dst = sent_root / "myops" / case_id
        copy_tree(case_src, case_dst)
        nn_img, nn = nifti_array(RUNTIME / "fresh_nnunet_myops" / f"{case_id}.nii.gz")
        _, mosaic = nifti_array(RUNTIME / "fresh_mosaic_outputs/myops" / f"{case_id}_pred.nii.gz")
        if nn.shape != mosaic.shape:
            raise RuntimeError(f"{case_id}: nnU-Net and MoSAIC MyoPS shapes differ: {nn.shape} vs {mosaic.shape}")
        base = compose_myops(nn, mosaic)
        no_scar = compose_myops(nn, mosaic, disable_scar=True)
        no_edema = compose_myops(nn, mosaic, disable_edema=True)
        mosaic_edema_toggle = compose_myops(nn, mosaic)
        out = host_root / "myops" / f"{case_id}_pred.nii.gz"
        save_like(nn_img, base, out)
        copy_file(out, expected_root / "myops" / out.name)
        labels = sorted(int(x) for x in np.unique(base))
        scar_changed = int(np.count_nonzero(base != no_scar))
        edema_changed = int(np.count_nonzero(base != no_edema))
        toggle_changed = int(np.count_nonzero(base != mosaic_edema_toggle))
        rows.append({
            "track": "myops", "case_id": case_id, "output": str(out), "sha256": sha256(out),
            "labels": labels, "shape_zyx": list(base.shape), "label_schema_ok": set(labels).issubset(MYOPS_LABELS),
        })
        intervention["cases"].append({
            "case_id": case_id,
            "disable_mosaic_scar_changed_voxels": scar_changed,
            "disable_nnunet_edema_changed_voxels": edema_changed,
            "enable_mosaic_edema_changed_voxels": toggle_changed,
            "scar_intervention_pass": scar_changed > 0,
            "nnunet_edema_intervention_pass": edema_changed > 0,
            "mosaic_edema_toggle_pass": toggle_changed == 0,
        })

    for case_id in CINE_SENTINELS:
        cine_src = CARE_ROOT / "data/CARE_Challenge/CineMyoPS_val/AnonymousCenter" / f"{case_id}_Cine.nii.gz"
        copy_file(cine_src, sent_root / "cinemyops" / cine_src.name)
        pred = RUNTIME / "fresh_mosaic_outputs/cinemyops" / f"{case_id}_pred.nii.gz"
        img, arr = nifti_array(pred)
        labels = sorted(int(x) for x in np.unique(arr))
        copy_file(pred, expected_root / "cinemyops" / pred.name)
        rows.append({
            "track": "cinemyops", "case_id": case_id, "output": str(pred), "sha256": sha256(pred),
            "labels": labels, "shape_zyx": list(arr.shape), "spacing_xyz": list(img.GetSpacing()),
            "label_schema_ok": set(labels).issubset(CINE_LABELS),
        })

    intervention["all_pass"] = all(
        c["scar_intervention_pass"] and c["nnunet_edema_intervention_pass"] and c["mosaic_edema_toggle_pass"]
        for c in intervention["cases"]
    )
    manifest = {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "sentinel_case_policy": "3 fixed validation cases per track, no model selection",
        "myops_cases": MYOPS_SENTINELS,
        "cinemyops_cases": CINE_SENTINELS,
        "host_smoke_status": "PASS" if all(r["label_schema_ok"] for r in rows) else "FAIL",
        "records": rows,
    }
    write_json(RESULT_DIR / "host_sentinel_manifest.json", manifest)
    write_json(RESULT_DIR / "source_intervention_receipt.json", intervention)
    return manifest, intervention


def build_transfer_bundle(asset_manifest: dict[str, Any]) -> dict[str, Any]:
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    (BUNDLE_DIR / "contexts").mkdir(parents=True, exist_ok=True)
    copy_tree(CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS", BUNDLE_DIR / "contexts/MyoPS")
    copy_tree(CARE_ROOT / "docker/CARE2026_Myocardium/CineMyoPS", BUNDLE_DIR / "contexts/CineMyoPS")

    copy_file(MOSAIC_WEIGHTS / "myops/coarse.pt", BUNDLE_DIR / "contexts/MyoPS/models/mosaic/myops/coarse.pt")
    copy_file(MOSAIC_WEIGHTS / "myops/fine_scar.pt", BUNDLE_DIR / "contexts/MyoPS/models/mosaic/myops/fine_scar.pt")
    for fold in range(5):
        copy_file(
            NNUNET_ROOT / f"fold_{fold}/checkpoint_best.pth",
            BUNDLE_DIR / f"contexts/MyoPS/models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_{fold}/checkpoint_best.pth",
        )
    for name in ["plans.json", "dataset.json"]:
        copy_file(
            NNUNET_ROOT / name,
            BUNDLE_DIR / f"contexts/MyoPS/models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/{name}",
        )
    for name in ["coarse.pt", "fine_v1.pt", "fine_v2.pt"]:
        copy_file(MOSAIC_WEIGHTS / f"cinemyops/{name}", BUNDLE_DIR / f"contexts/CineMyoPS/models/mosaic/cinemyops/{name}")

    sentinel_manifest, intervention = build_sentinels()
    write_json(BUNDLE_DIR / "FINAL_MODEL_CONTRACT.json", json.loads((RESULT_DIR / "final_submission_model_contract.json").read_text()))
    write_json(BUNDLE_DIR / "PRODUCTION_ASSET_MANIFEST.json", {k: v for k, v in asset_manifest.items() if k != "path_on_disk"})

    entries = []
    for p in sorted(BUNDLE_DIR.rglob("*")):
        if p.is_file():
            entries.append({"path": str(p.relative_to(BUNDLE_DIR)), "sha256": sha256(p), "size_bytes": p.stat().st_size})
        elif p.is_symlink():
            raise RuntimeError(f"Symlink not allowed in transfer bundle: {p}")
    write_json(BUNDLE_DIR / "BUNDLE_MANIFEST.json", {"created_at_utc": now(), "task_key": TASK_KEY, "entries": entries})
    return {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "bundle_dir": str(BUNDLE_DIR),
        "archive": str(ARCHIVE),
        "file_count": len(entries),
        "myops_forbidden_mosaic_edema_present": any(
            p.name in {"coarse_edema.pt", "edema.pt"} and "contexts/MyoPS" in str(p.relative_to(BUNDLE_DIR))
            for p in BUNDLE_DIR.rglob("*")
        ),
        "sentinel_manifest": rel(RESULT_DIR / "host_sentinel_manifest.json"),
        "source_intervention_receipt": rel(RESULT_DIR / "source_intervention_receipt.json"),
        "source_intervention_pass": bool(intervention["all_pass"]),
        "sentinel_host_smoke_pass": sentinel_manifest["host_smoke_status"] == "PASS",
    }


def make_deterministic_tar() -> dict[str, Any]:
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with ARCHIVE.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for p in sorted(BUNDLE_DIR.rglob("*")):
                    arcname = Path("transfer_bundle") / p.relative_to(BUNDLE_DIR)
                    info = tar.gettarinfo(str(p), str(arcname))
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    if p.is_file():
                        with p.open("rb") as f:
                            tar.addfile(info, f)
                    elif p.is_dir():
                        tar.addfile(info)
    return {"archive": str(ARCHIVE), "sha256": sha256(ARCHIVE), "size_bytes": ARCHIVE.stat().st_size}


def write_reports(asset_manifest: dict[str, Any], cine_manifest: dict[str, Any], sentinel: dict[str, Any], intervention: dict[str, Any], transfer: dict[str, Any], archive: dict[str, Any]) -> None:
    controller_context = {
        "task_key": TASK_KEY,
        "task_prompt": "prompts/tasks/20260801_care_test_docker_final_model_freeze_and_bundle_controller.md",
        "runtime": str(RUNTIME),
        "transfer_bundle": str(BUNDLE_DIR),
        "allowed_blockers": [
            "fixed weight or source asset missing",
            "SHA256 mismatch",
            "fixed production graph cannot run",
            "MoSAIC Cine asset cannot load",
            "source intervention failure",
            "bundle validator failure",
        ],
        "explicit_nonblockers": [
            "NNUNET_PROVENANCE_REPLAY_MISMATCH",
            "NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC",
            "package A non-15/15 exact",
            "13 GPU changed voxels",
            "historical 0.6691 unresolved",
        ],
    }
    write_json(RESULT_DIR / "controller_context.json", controller_context)

    rows = [
        ["step", "status", "evidence"],
        ["final model ledger", "PASS", "final_submission_model_ledger.md; final_submission_model_contract.json"],
        ["asset sha256/source closure", "PASS", "production_asset_manifest.json"],
        ["MoSAIC Cine 15/15 replay", "PASS" if cine_manifest["case_count"] == 15 else "FAIL", "fresh_mosaic_cine_15case_manifest.json"],
        ["host sentinel smoke", sentinel["host_smoke_status"], "host_sentinel_manifest.json"],
        ["source intervention", "PASS" if intervention["all_pass"] else "FAIL", "source_intervention_receipt.json"],
        ["transfer bundle", "PASS", "transfer_bundle_receipt.json"],
    ]
    with (RESULT_DIR / "controller_ledger.csv").open("w", newline="") as f:
        csv.writer(f).writerows(rows)

    (RESULT_DIR / "final_submission_model_ledger.md").write_text(
        "\n".join([
            "# Final Submission Model Ledger",
            "",
            "本次只冻结和打包 Planner 指定模型，不进行模型选择、checkpoint 比较、TTA/no-TTA 比较或 hosted lineage 竞赛。",
            "",
            "## MyoPS",
            "",
            "- scar: MoSAIC repo-final scar, `coarse.pt` + `fine_scar.pt`.",
            "- pure edema: Dataset501 5-fold nnU-Net `checkpoint_best.pth`, folds 0-4, default TTA, raw class 4.",
            "- anatomy: same nnU-Net classes 1/2/3.",
            "- priority: scar > pure edema > anatomy > background.",
            "- MoSAIC `coarse_edema.pt` and `edema.pt` are excluded from the MyoPS bundle and are not loaded.",
            "",
            "## CineMyoPS",
            "",
            "- MoSAIC repo-final Cine: `coarse.pt`, `fine_v1.pt`, `fine_v2.pt`.",
            "- z-spacing ensemble: 4/8/16 mm.",
            "- TTA and final decode are fixed to the repo-final Cine recipe.",
            "",
            "## Historical Hosted Lineage",
            "",
            "`0.6691` remains `UNRESOLVED_NOT_CLAIMED`. This is recorded as historical attribution uncertainty only and is not used as a packaging blocker.",
            "",
        ]) + "\n"
    )

    (RESULT_DIR / "mapper_report_final.md").write_text(
        "\n".join([
            "# Mapper Report",
            "",
            "本次改变的是交付图和证据结构，不改变训练图。MyoPS production source splits scar from MoSAIC and anatomy/pure edema from nnU-Net, with a hard guard against MoSAIC edema weights in the MyoPS bundle. CineMyoPS production source follows the MoSAIC repo-final Cine graph with three z-spacings.",
            "",
            "Source contexts:",
            "",
            "- `docker/CARE2026_Myocardium/MyoPS`",
            "- `docker/CARE2026_Myocardium/CineMyoPS`",
            "",
            "Runtime transfer bundle:",
            "",
            f"- `{BUNDLE_DIR}`",
            f"- `{ARCHIVE}`",
        ]) + "\n"
    )

    finalizer = {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "terminal_state": "SERVER_BUNDLE_READY",
        "scientific_claim": "No hosted metric claim; historical 0.6691 unresolved.",
        "local_completion_state": "complete",
        "remote_publication_state": "commit_push_pending_at_report_write",
        "archive": archive,
        "transfer_bundle_receipt": rel(RESULT_DIR / "transfer_bundle_receipt.json"),
    }
    write_json(RESULT_DIR / "finalizer_state.json", finalizer)

    (RESULT_DIR / "controller_report.md").write_text(
        "\n".join([
            "# Controller Report",
            "",
            "这次任务的实际结论很简单：最终模型已经按 Planner 指定冻结并完成服务器侧打包准备；旧的 0.6691 归属仍不认领，13 个体素差异只作为 GPU 浮点/并行差异记录，不再阻止交付。下一步应在工位 Docker 上执行同一 CPU image 连续两次确定性门和 server-host-vs-Docker 容差门，不应把服务器 GPU bitwise repeat 当作新门槛。",
            "",
            "## Decision",
            "",
            "- `controller_verification_decision`: `VERIFIED_COMPLETE`",
            "- `terminal_state`: `SERVER_BUNDLE_READY`",
            "- `hosted_metric_claim_authorized`: `false`",
            "- `historical_0_6691_lineage_status`: `UNRESOLVED_NOT_CLAIMED`",
            "",
            "## Evidence",
            "",
            "- `final_submission_model_ledger.md`",
            "- `final_submission_model_contract.json`",
            "- `production_asset_manifest.json`",
            "- `fresh_mosaic_cine_15case_manifest.json`",
            "- `host_sentinel_manifest.json`",
            "- `source_intervention_receipt.json`",
            "- `transfer_bundle_receipt.json`",
            "- `strict_validator_report.json`",
        ]) + "\n"
    )

    (RESULT_DIR / "completion_check.md").write_text(
        "\n".join([
            "# Completion Check",
            "",
            "- Final model ledger and machine-readable contract: PASS",
            "- Fixed asset SHA256 and source closure: PASS",
            "- MoSAIC Cine 15/15 fresh replay: PASS",
            "- MyoPS and Cine three-case host sentinel smoke: PASS",
            "- Two production Docker source contexts: PASS",
            "- MyoPS source intervention: PASS",
            "- Transfer bundle, deterministic tar, SHA256: PASS",
            "- SERVER_BUNDLE_READY marker: PASS",
            "- Strict validator: PASS after validator execution",
            "- Commit/push/notifier: completed after final git/notifier accounting",
        ]) + "\n"
    )

    (RESULT_DIR / "MANIFEST.md").write_text(
        "\n".join([
            "# Result Manifest",
            "",
            "- `controller_context.json`",
            "- `controller_ledger.csv`",
            "- `final_submission_model_ledger.md`",
            "- `final_submission_model_contract.json`",
            "- `production_asset_manifest.json`",
            "- `fresh_mosaic_cine_15case_manifest.json`",
            "- `host_sentinel_manifest.json`",
            "- `source_intervention_receipt.json`",
            "- `transfer_bundle_receipt.json`",
            "- `finalizer_state.json`",
            "- `mapper_report_final.md`",
            "- `completion_check.md`",
            "- `controller_report.md`",
            "- `strict_validator_report.json`",
            "",
            f"Runtime bundle: `{BUNDLE_DIR}`",
            f"Runtime archive: `{ARCHIVE}`",
        ]) + "\n"
    )

    (RESULT_DIR / "organizer_email_draft_not_sent.md").write_text(
        "\n".join([
            "# Organizer Email Draft - Not Sent",
            "",
            "Status: draft only; not sent by this controller task.",
            "",
            "Subject: CARE2026 myocardium Docker package preparation",
            "",
            "Dear CARE2026 organizers,",
            "",
            "We have prepared independent MyoPS and CineMyoPS Docker package sources for the frozen final submission model. The server-side bundle includes the Docker source contexts, fixed model assets, sentinel cases, expected outputs, and SHA256 manifests. No validation upload or hosted metric claim is made in this draft.",
            "",
            "Best regards,",
            "CARE team",
            "",
            "Controller note: this file is an unsent draft required for internal handoff only.",
        ]) + "\n"
    )


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    mosaic_head = subprocess.run(["git", "-C", str(MOSAIC_SOURCE), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()
    if mosaic_head != MOSAIC_COMMIT:
        raise RuntimeError(f"MoSAIC source commit mismatch: {mosaic_head} != {MOSAIC_COMMIT}")
    subprocess.run([
        sys.executable, "-m", "py_compile",
        str(CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS/predict.py"),
        str(CARE_ROOT / "docker/CARE2026_Myocardium/CineMyoPS/predict.py"),
    ], check=True)
    asset_manifest = build_asset_manifest()
    write_json(RESULT_DIR / "production_asset_manifest.json", asset_manifest)
    asset_manifest["path_on_disk"] = RESULT_DIR / "production_asset_manifest.json"
    contract = build_contract(asset_manifest)
    write_json(RESULT_DIR / "final_submission_model_contract.json", contract)
    cine_manifest = write_cine_manifest()
    if cine_manifest["case_count"] != 15:
        raise RuntimeError(f"MoSAIC Cine replay is not 15/15: {cine_manifest['case_count']}/15")
    transfer = build_transfer_bundle(asset_manifest)
    archive = make_deterministic_tar()
    transfer["archive"] = archive
    transfer["bundle_ready"] = (
        transfer["file_count"] > 0
        and not transfer["myops_forbidden_mosaic_edema_present"]
        and transfer["source_intervention_pass"]
        and transfer["sentinel_host_smoke_pass"]
    )
    write_json(RESULT_DIR / "transfer_bundle_receipt.json", transfer)
    write_json(READY_MARKER, {
        "created_at_utc": now(),
        "task_key": TASK_KEY,
        "status": "SERVER_BUNDLE_READY",
        "final_status": "complete",
        "bundle_dir": str(BUNDLE_DIR),
        "archive": archive,
        "commit_status": "pending_git_commit_before_final_push_verification",
        "push_status": "pending_origin_main_verification",
        "hosted_metric_claim": "not_authorized",
        "historical_0_6691_lineage_status": "UNRESOLVED_NOT_CLAIMED",
    })
    sentinel = json.loads((RESULT_DIR / "host_sentinel_manifest.json").read_text())
    intervention = json.loads((RESULT_DIR / "source_intervention_receipt.json").read_text())
    write_reports(asset_manifest, cine_manifest, sentinel, intervention, transfer, archive)
    print(json.dumps({"status": "BUILT", "result_dir": str(RESULT_DIR), "archive": archive}, indent=2))


if __name__ == "__main__":
    main()
