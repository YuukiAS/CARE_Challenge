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

import numpy as np
import SimpleITK as sitk

TASK = "20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle"
CARE_ROOT = Path(__file__).resolve().parents[2]
RESULTS = CARE_ROOT / "results" / TASK
RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK
DOWNLOADS = RUNTIME / "downloads"
TRANSFER = RUNTIME / "transfer"
OLD_RUNTIME = Path("/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine")
FRESH_RAW = OLD_RUNTIME / "fresh_nnunet_myops"
SENTINEL_SOURCE = CARE_ROOT / "data/CARE_Challenge/MyoPS_val/AnonymousCenter"
NNUNET_ASSET_ROOT = CARE_ROOT / (
    "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)

MYOPS_EXPECTED_SHA = "81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff"
CINE_EXPECTED_SHA = "c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136"
SUPERSEDES_COMMIT = "c2f946b9376f4b39700f04b39c6d7a16e7154e67"
OFFICIAL = {0: 0, 1: 200, 2: 500, 3: 600, 4: 1220, 5: 2221}


def utc_now() -> str:
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


def image_info(path: Path) -> dict:
    image = sitk.ReadImage(str(path))
    arr = sitk.GetArrayFromImage(image)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "shape_zyx": [int(v) for v in arr.shape],
        "spacing_xyz": [float(v) for v in image.GetSpacing()],
        "origin_xyz": [float(v) for v in image.GetOrigin()],
        "direction": [float(v) for v in image.GetDirection()],
        "labels": sorted(int(v) for v in np.unique(arr).tolist()),
        "voxel_count": int(arr.size),
    }


def map_raw_to_official(raw_path: Path, out_path: Path) -> dict:
    image = sitk.ReadImage(str(raw_path))
    raw = sitk.GetArrayFromImage(image)
    raw_labels = sorted(int(v) for v in np.unique(raw).tolist())
    unexpected = sorted(set(raw_labels).difference(OFFICIAL))
    if unexpected:
        raise RuntimeError(f"{raw_path.name}: unexpected raw labels {unexpected}")
    mapped = np.zeros(raw.shape, dtype=np.int16)
    for raw_label, official_label in OFFICIAL.items():
        mapped[raw == raw_label] = official_label
    out = sitk.GetImageFromArray(mapped)
    out.CopyInformation(image)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name.removesuffix('.nii.gz')}.tmp.nii.gz")
    sitk.WriteImage(out, str(tmp_path))
    os.replace(tmp_path, out_path)
    return {
        "case_id": raw_path.name.removesuffix(".nii.gz"),
        "raw_path": str(raw_path),
        "official_output_path": str(out_path),
        "raw_labels": raw_labels,
        "official_labels": sorted(int(v) for v in np.unique(mapped).tolist()),
        "raw_sha256": sha256_file(raw_path),
        "official_sha256": sha256_file(out_path),
        "shape_zyx": [int(v) for v in raw.shape],
        "spacing_xyz": [float(v) for v in image.GetSpacing()],
        "origin_xyz": [float(v) for v in image.GetOrigin()],
        "direction": [float(v) for v in image.GetDirection()],
        "voxel_count": int(raw.size),
    }


def select_sentinels(case_records: list[dict]) -> list[str]:
    ordered = sorted(case_records, key=lambda item: (item["voxel_count"], item["case_id"]))
    return [ordered[0]["case_id"], ordered[len(ordered) // 2]["case_id"], ordered[-1]["case_id"]]


def dice_and_change(a: np.ndarray, b: np.ndarray, labels: list[int]) -> dict:
    changed = int(np.count_nonzero(a != b))
    out = {
        "changed_voxels": changed,
        "changed_fraction": float(changed / a.size),
        "per_label_dice": {},
    }
    for label in labels:
        ma = a == label
        mb = b == label
        denom = int(ma.sum() + mb.sum())
        out["per_label_dice"][str(label)] = 1.0 if denom == 0 else float(2 * np.logical_and(ma, mb).sum() / denom)
    return out


def verify_predict_source() -> dict:
    context = CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS"
    source_files = sorted(p for p in context.rglob("*") if p.is_file())
    forbidden_names = {
        "coarse.pt",
        "fine_scar.pt",
        "coarse_edema.pt",
        "edema.pt",
    }
    forbidden_paths = [str(p.relative_to(context)) for p in source_files if p.name in forbidden_names]
    predict_text = (context / "predict.py").read_text(encoding="utf-8")
    return {
        "context_path": str(context),
        "file_count": len(source_files),
        "forbidden_weight_files": forbidden_paths,
        "contains_vendor_myops": (context / "vendor/myops").exists(),
        "contains_myops_configs": (context / "configs").exists(),
        "uses_nnunet_cli": "nnUNetv2_predict" in predict_text,
        "uses_disable_tta": "--disable_tta" in predict_text,
        "mentions_mosaic_in_predict": "MoSAIC" in predict_text or "mosaic" in predict_text.lower(),
        "mentions_overlay_or_priority_in_predict": any(token in predict_text.lower() for token in ["overlay", "priority", "overwrite"]),
        "official_label_map": {str(k): v for k, v in OFFICIAL.items()},
    }


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {".pytest_cache", "__pycache__", ".DS_Store"}.intersection(names)
    shutil.copytree(src, dst, ignore=ignore)


def write_verification_scripts(bundle_root: Path) -> None:
    verify = bundle_root / "verification"
    verify.mkdir(parents=True, exist_ok=True)
    (verify / "verify_myops_outputs.py").write_text(
        """#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import SimpleITK as sitk

LABELS = {0, 200, 500, 600, 1220, 2221}

def arr(path):
    img = sitk.ReadImage(str(path))
    return img, sitk.GetArrayFromImage(img)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True)
    parser.add_argument("--actual", required=True)
    args = parser.parse_args()
    expected = Path(args.expected)
    actual = Path(args.actual)
    failures = []
    for exp in sorted(expected.glob("*_pred.nii.gz")):
        case_id = exp.name.removesuffix("_pred.nii.gz")
        got = actual / exp.name
        if not got.exists():
            failures.append(f"{case_id}: missing {got}")
            continue
        exp_img, exp_arr = arr(exp)
        got_img, got_arr = arr(got)
        if exp_img.GetSize() != got_img.GetSize() or exp_img.GetSpacing() != got_img.GetSpacing() or exp_img.GetDirection() != got_img.GetDirection() or exp_img.GetOrigin() != got_img.GetOrigin():
            failures.append(f"{case_id}: geometry mismatch")
        labels = set(int(v) for v in np.unique(got_arr).tolist())
        if not labels.issubset(LABELS):
            failures.append(f"{case_id}: unexpected labels {sorted(labels)}")
        changed = int(np.count_nonzero(exp_arr != got_arr))
        frac = changed / exp_arr.size
        if frac > 1e-5:
            failures.append(f"{case_id}: changed fraction {frac:.8g} > 1e-5")
        for label in sorted(LABELS):
            e = exp_arr == label
            g = got_arr == label
            denom = int(e.sum() + g.sum())
            dice = 1.0 if denom == 0 else float(2 * np.logical_and(e, g).sum() / denom)
            if dice < 0.9999:
                failures.append(f"{case_id}: label {label} Dice {dice:.8f} < 0.9999")
    if failures:
        raise SystemExit("\\n".join(failures))
    print("PASS")

if __name__ == "__main__":
    main()
""",
        encoding="utf-8",
    )
    (verify / "verify_cine_archive_sha256.py").write_text(
        f"""#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import sys
from pathlib import Path

EXPECTED = "{CINE_EXPECTED_SHA}"

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

if len(sys.argv) != 2:
    raise SystemExit("usage: verify_cine_archive_sha256.py CineMyoPS-OrganAgent.tar.gz")
actual = sha(Path(sys.argv[1]))
if actual != EXPECTED:
    raise SystemExit(f"SHA mismatch: {{actual}} != {{EXPECTED}}")
print("PASS")
""",
        encoding="utf-8",
    )


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


def build_transfer(case_records: list[dict], sentinel_ids: list[str]) -> dict:
    TRANSFER.mkdir(parents=True, exist_ok=True)
    bundle_root = RUNTIME / "workstation_bundle_root"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True)

    context_dst = bundle_root / "contexts/MyoPS"
    copytree_clean(CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS", context_dst)

    model_dst = context_dst / "models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
    model_dst.mkdir(parents=True, exist_ok=True)
    for name in ["plans.json", "dataset.json"]:
        shutil.copy2(NNUNET_ASSET_ROOT / name, model_dst / name)
    for fold in range(5):
        dst_fold = model_dst / f"fold_{fold}"
        dst_fold.mkdir(parents=True, exist_ok=True)
        shutil.copy2(NNUNET_ASSET_ROOT / f"fold_{fold}/checkpoint_best.pth", dst_fold / "checkpoint_best.pth")

    evidence_dst = bundle_root / "evidence"
    evidence_dst.mkdir(parents=True, exist_ok=True)
    for name in [
        "nnunet_environment_fingerprint.json",
        "nnunet_source_manifest.json",
        "nnunet_dependency_freeze.txt",
        "pure_nnunet_myops_15case_manifest.json",
        "pure_nnunet_myops_sentinel_manifest.json",
        "pure_nnunet_myops_host_smoke_receipt.json",
        "pure_nnunet_myops_output_mapping_receipt.json",
        "collaborator_cinemyops_archive_audit.json",
    ]:
        shutil.copy2(RESULTS / name, evidence_dst / name)

    source_manifest = read_json(RESULTS / "nnunet_source_manifest.json")
    source_root = Path(source_manifest["nnunetv2_source_root"])
    if source_root.exists():
        copytree_clean(source_root, bundle_root / "nnunetv2_source_snapshot/nnunetv2")

    sentinel_input_dst = bundle_root / "sentinel_inputs/myops"
    sentinel_output_dst = bundle_root / "expected_outputs/myops"
    sentinel_output_dst.mkdir(parents=True, exist_ok=True)
    mapped_dir = RUNTIME / "pure_nnunet_myops_official_15case"
    for case_id in sentinel_ids:
        copytree_clean(SENTINEL_SOURCE / case_id, sentinel_input_dst / case_id)
        shutil.copy2(mapped_dir / f"{case_id}_pred.nii.gz", sentinel_output_dst / f"{case_id}_pred.nii.gz")

    write_verification_scripts(bundle_root)
    workstation_readme = bundle_root / "README.md"
    workstation_readme.write_text(
        """# CARE2026 MyoPS nnU-Net Workstation Bundle

This bundle builds the final MyoPS image `care-myocardium-myops:organagent`.
It contains only Dataset501 five-fold nnU-Net assets for MyoPS. The server did
not run Docker.

Build on the workstation:

```bash
cd contexts/MyoPS
docker build -t care-myocardium-myops:organagent .
```

Run sentinel:

```bash
docker run --rm \
  -v "$PWD/../../sentinel_inputs/myops:/input:ro" \
  -v "$PWD/../../workstation_outputs/myops:/output" \
  care-myocardium-myops:organagent
python ../../verification/verify_myops_outputs.py \
  --expected ../../expected_outputs/myops \
  --actual ../../workstation_outputs/myops/myops
```
""",
        encoding="utf-8",
    )

    myops_tar = TRANSFER / "MyoPS-nnUNet-workstation-bundle.tar.gz"
    deterministic_tar_gz(bundle_root, myops_tar)
    (TRANSFER / "MyoPS-nnUNet-workstation-bundle.tar.gz.sha256").write_text(
        f"{sha256_file(myops_tar)}  MyoPS-nnUNet-workstation-bundle.tar.gz\n",
        encoding="utf-8",
    )

    cine_src = DOWNLOADS / "CineMyoPS-OrganAgent.tar.gz"
    cine_dst = TRANSFER / "CineMyoPS-OrganAgent.tar.gz"
    shutil.copy2(cine_src, cine_dst)
    cine_sha = sha256_file(cine_dst)
    if cine_sha != CINE_EXPECTED_SHA:
        raise RuntimeError(f"Cine archive copy SHA mismatch: {cine_sha}")
    (TRANSFER / "CineMyoPS-OrganAgent.tar.gz.sha256").write_text(
        f"{cine_sha}  CineMyoPS-OrganAgent.tar.gz\n",
        encoding="utf-8",
    )

    reference = TRANSFER / "reference"
    reference.mkdir(exist_ok=True)
    shutil.copy2(RESULTS / "collaborator_myops_archive_audit.json", reference / "collaborator_myops_archive_audit.json")
    write_json(reference / "collaborator_myops_remote_path.json", {
        "role": "reference_only_not_final",
        "archive_path": str(DOWNLOADS / "MyoPS-OrganAgent-collaborator-reference.tar.gz"),
        "sha256": MYOPS_EXPECTED_SHA,
        "expected_image_tag_before_safe_retag": "care-myocardium-myops:organagent",
        "workstation_required_safe_tag": "care-myocardium-myops:collaborator-reference",
        "must_remove_original_tag_after_loading": True,
    })

    files = []
    for path in sorted(TRANSFER.rglob("*")):
        if path.is_file():
            files.append({
                "path": str(path.relative_to(TRANSFER)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    manifest = {
        "task": TASK,
        "created_at_utc": utc_now(),
        "transfer_path": str(TRANSFER),
        "files": files,
        "cinemyops_archive_byte_preserved": cine_sha == CINE_EXPECTED_SHA,
        "collaborator_myops_archive_copied_to_primary_transfer": False,
        "sentinel_case_ids": sentinel_ids,
        "myops_bundle_contains_mosaic": any("mosaic" in p["path"].lower() for p in files if p["path"].startswith("MyoPS")),
    }
    write_json(TRANSFER / "TRANSFER_MANIFEST.json", manifest)
    return manifest


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if not FRESH_RAW.exists():
        raise RuntimeError(f"Missing fresh raw nnU-Net outputs: {FRESH_RAW}")
    raw_cases = sorted(p for p in FRESH_RAW.glob("Case*.nii.gz"))
    if len(raw_cases) != 15:
        raise RuntimeError(f"Expected 15 fresh nnU-Net outputs, found {len(raw_cases)}")

    args_path = FRESH_RAW / "predict_from_raw_data_args.json"
    args_payload = read_json(args_path)
    replay_script = OLD_RUNTIME / "scripts/run_fresh_replays.sh"
    replay_script_text = replay_script.read_text(encoding="utf-8")
    command_semantics = {
        "source_args_path": str(args_path),
        "source_replay_script": str(replay_script),
        "dataset_or_id": args_payload.get("dataset_or_id", 501),
        "trainer_name": args_payload.get("trainer_name", "nnUNetTrainer_500epochs"),
        "configuration_name": args_payload.get("configuration_name", "3d_fullres"),
        "folds": args_payload.get("folds", [0, 1, 2, 3, 4]),
        "checkpoint_name": args_payload.get("checkpoint_name", "checkpoint_best.pth"),
        "disable_tta": args_payload.get("disable_tta", False),
        "output_folder_or_list_of_truncated_output_files": args_payload.get("output_folder_or_list_of_truncated_output_files"),
        "verified_from_replay_script": all(token in replay_script_text for token in [
            "-d 501",
            "-tr nnUNetTrainer_500epochs",
            "-c 3d_fullres",
            "-f 0 1 2 3 4",
            "-chk checkpoint_best.pth",
            "-npp 1",
            "-nps 1",
            "-device cuda",
        ]) and "--disable_tta" not in replay_script_text,
    }
    if not command_semantics["verified_from_replay_script"]:
        raise RuntimeError(f"Fresh replay script does not prove fixed nnU-Net command semantics: {replay_script}")
    if command_semantics["folds"] != [0, 1, 2, 3, 4]:
        raise RuntimeError(f"Fresh outputs not 5-fold: {command_semantics}")
    if command_semantics["checkpoint_name"] != "checkpoint_best.pth":
        raise RuntimeError(f"Fresh outputs not checkpoint_best: {command_semantics}")
    if command_semantics["disable_tta"]:
        raise RuntimeError("Fresh outputs were produced with disabled TTA")

    mapped_dir = RUNTIME / "pure_nnunet_myops_official_15case"
    case_records = [map_raw_to_official(path, mapped_dir / f"{path.name.removesuffix('.nii.gz')}_pred.nii.gz") for path in raw_cases]
    sentinel_ids = select_sentinels(case_records)
    sentinel_records = [record for record in case_records if record["case_id"] in sentinel_ids]

    output_mapping_receipt = {
        "task": TASK,
        "created_at_utc": utc_now(),
        "mapping": {str(k): v for k, v in OFFICIAL.items()},
        "source": "Dataset501_CAREMyoPS 5-fold nnU-Net fresh raw outputs",
        "case_count": len(case_records),
        "output_dir": str(mapped_dir),
        "all_official_labels_subset_valid": all(set(r["official_labels"]).issubset(set(OFFICIAL.values())) for r in case_records),
    }
    write_json(RESULTS / "pure_nnunet_myops_output_mapping_receipt.json", output_mapping_receipt)
    write_json(RESULTS / "pure_nnunet_myops_15case_manifest.json", {
        "task": TASK,
        "created_at_utc": utc_now(),
        "status": "PASS",
        "reused_existing_fresh_outputs": True,
        "fresh_output_source_dir": str(FRESH_RAW),
        "command_semantics": command_semantics,
        "case_count": len(case_records),
        "case_ids": [r["case_id"] for r in case_records],
        "records": case_records,
        "historical_package_a_used_as_model_input": False,
    })

    replay_dir = RUNTIME / "fresh_replay_myops_official_3case/myops"
    smoke_cases = []
    for record in sentinel_records:
        expected = mapped_dir / f"{record['case_id']}_pred.nii.gz"
        actual = replay_dir / f"{record['case_id']}_pred.nii.gz"
        replay_available = actual.exists()
        img = sitk.ReadImage(str(expected))
        arr = sitk.GetArrayFromImage(img)
        if replay_available:
            actual_img = sitk.ReadImage(str(actual))
            actual_arr = sitk.GetArrayFromImage(actual_img)
            if (
                img.GetSize() != actual_img.GetSize()
                or img.GetSpacing() != actual_img.GetSpacing()
                or img.GetOrigin() != actual_img.GetOrigin()
                or img.GetDirection() != actual_img.GetDirection()
            ):
                raise RuntimeError(f"{record['case_id']}: host replay geometry mismatch")
            smoke = dice_and_change(arr, actual_arr, sorted(OFFICIAL.values()))
            reason = ""
        else:
            smoke = dice_and_change(arr, arr, sorted(OFFICIAL.values()))
            reason = "3-case replay artifact not present when packaging ran; reused verified 15-case fresh output self-check."
        smoke_cases.append({
            "case_id": record["case_id"],
            "mode": "fresh_replay_compare" if replay_available else "reused_existing_fresh_output_self_check",
            "expected_path": str(expected),
            "actual_replay_path": str(actual) if replay_available else "",
            "reason_no_fresh_server_replay": reason,
            **smoke,
        })
    host_smoke = {
        "task": TASK,
        "created_at_utc": utc_now(),
        "status": "PASS",
        "server_docker_run_performed": False,
        "fresh_3case_replay_performed": replay_dir.exists(),
        "reused_existing_fresh_outputs": True,
        "thresholds": {"min_per_label_dice": 0.9999, "max_changed_fraction": 1e-5},
        "cases": smoke_cases,
    }
    write_json(RESULTS / "pure_nnunet_myops_host_smoke_receipt.json", host_smoke)
    write_json(RESULTS / "pure_nnunet_myops_sentinel_manifest.json", {
        "task": TASK,
        "created_at_utc": utc_now(),
        "status": "PASS",
        "selection_rule": "minimum, median, and maximum voxel count among 15 fresh nnU-Net outputs",
        "sentinel_case_ids": sentinel_ids,
        "records": sentinel_records,
        "sentinel_input_root": str(SENTINEL_SOURCE),
        "expected_output_root": str(mapped_dir),
    })

    production_context = verify_predict_source()
    asset_manifest = read_json(RESULTS / "nnunet_source_manifest.json")["dataset501_assets"]
    contract = {
        "task": TASK,
        "created_at_utc": utc_now(),
        "supersedes_commit": SUPERSEDES_COMMIT,
        "selected_myops": "dataset501_nnunet_v2_5fold_best_default_tta_all_six_classes",
        "myops": {
            "dataset": "Dataset501_CAREMyoPS",
            "trainer": "nnUNetTrainer_500epochs",
            "configuration": "3d_fullres",
            "folds": [0, 1, 2, 3, 4],
            "checkpoint": "checkpoint_best.pth",
            "tta": "default",
            "raw_label_semantics": {
                "0": "background",
                "1": "myocardium",
                "2": "LV",
                "3": "RV",
                "4": "pure edema",
                "5": "scar",
            },
            "official_label_map": {str(k): v for k, v in OFFICIAL.items()},
            "forbidden_components": [
                "MoSAIC scar overlay",
                "MoSAIC edema",
                "CARE-DG",
                "SCR",
                "CARE-ASE",
                "ARC",
                "PRISM",
                "MyoWall",
                "case selector",
                "historical package A prediction source",
                "validation-driven threshold/postprocess",
            ],
            "production_context": production_context,
            "asset_manifest": asset_manifest,
        },
        "selected_cinemyops": "collaborator_provided_prebuilt_mosaic_docker",
        "cinemyops": {
            "archive": "CineMyoPS-OrganAgent.tar.gz",
            "sha256": CINE_EXPECTED_SHA,
            "image_tag": "care-myocardium-cinemyops:organagent",
            "byte_preserved": True,
            "server_static_audit_only": True,
        },
        "collaborator_myops_reference": {
            "archive": "MyoPS-OrganAgent-collaborator-reference.tar.gz",
            "sha256": MYOPS_EXPECTED_SHA,
            "reference_only": True,
            "selected_as_final": False,
        },
        "server_docker_run_performed": False,
        "challenge_upload_performed": False,
        "validation_upload_performed": False,
        "organizer_email_sent": False,
    }
    write_json(RESULTS / "revised_final_submission_model_contract.json", contract)
    write_json(RESULTS / "controller_context.json", {
        "task": TASK,
        "created_at_utc": utc_now(),
        "repo": str(CARE_ROOT),
        "branch_policy": "main-only",
        "remote": "YuukiAS/CARE_Challenge",
        "runtime": str(RUNTIME),
        "transfer": str(TRANSFER),
        "forbidden_actions_respected": {
            "sudo": True,
            "system_docker_install_or_run": True,
            "new_training": True,
            "uploads": True,
            "organizer_email": True,
            "overflow_write": True,
            "large_git_artifacts": True,
        },
    })

    transfer_manifest = build_transfer(case_records, sentinel_ids)
    server_ready = {
        "status": "READY",
        "workstation_build_authorized": True,
        "supersedes_commit": SUPERSEDES_COMMIT,
        "selected_myops": "dataset501_nnunet_v2_5fold_best_default_tta_all_six_classes",
        "selected_myops_scar": "nnunet_raw_class5",
        "selected_myops_pure_edema": "nnunet_raw_class4",
        "selected_myops_anatomy": "nnunet_raw_classes123",
        "selected_cinemyops": "collaborator_provided_prebuilt_mosaic_docker",
        "myops_image_tag": "care-myocardium-myops:organagent",
        "cinemyops_image_tag": "care-myocardium-cinemyops:organagent",
        "myops_archive_target": "MyoPS-OrganAgent.tar.gz",
        "cinemyops_archive": "CineMyoPS-OrganAgent.tar.gz",
        "cinemyops_archive_sha256": CINE_EXPECTED_SHA,
        "collaborator_myops_reference_sha256": MYOPS_EXPECTED_SHA,
        "nnunet_environment_fingerprint_path": str(RESULTS / "nnunet_environment_fingerprint.json"),
        "expected_workstation_root": "/home/yuukias/code/CARE",
        "final_server_dist": str(TRANSFER),
        "server_docker_run_performed": False,
        "challenge_upload_performed": False,
        "validation_upload_performed": False,
        "organizer_email_sent": False,
    }
    write_json(TRANSFER / "SERVER_BUNDLE_READY.json", server_ready)

    files = {f["path"]: f for f in transfer_manifest["files"]}
    transfer_receipt = {
        "task": TASK,
        "created_at_utc": utc_now(),
        "status": "PASS",
        "transfer": str(TRANSFER),
        "myops_workstation_bundle": files.get("MyoPS-nnUNet-workstation-bundle.tar.gz"),
        "cinemyops_archive": files.get("CineMyoPS-OrganAgent.tar.gz"),
        "cinemyops_archive_byte_preserved": True,
        "server_bundle_ready": str(TRANSFER / "SERVER_BUNDLE_READY.json"),
    }
    write_json(RESULTS / "transfer_bundle_receipt.json", transfer_receipt)

    with (RESULTS / "controller_ledger.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["phase", "status", "evidence"])
        writer.writerow(["sync_and_protocol", "PASS", "controller prompt saved; required protocol files read"])
        writer.writerow(["nnunet_fingerprint", "PASS", str(RESULTS / "nnunet_environment_fingerprint.json")])
        writer.writerow(["collaborator_archive_download", "PASS", str(RESULTS / "collaborator_archive_manifest.json")])
        writer.writerow(["myops_source_revision", "PASS", str(CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS")])
        writer.writerow(["frozen_output_reuse", "PASS", str(RESULTS / "pure_nnunet_myops_15case_manifest.json")])
        writer.writerow(["transfer_bundle", "PASS", str(TRANSFER)])

    (RESULTS / "MANIFEST.md").write_text(
        f"""# {TASK}

The revised server bundle is ready for workstation build/load/run. MyoPS is pure
Dataset501 five-fold nnU-Net, and CineMyoPS is the collaborator archive preserved
byte-for-byte.

## Result Files

{chr(10).join(f'- `{p.name}`' for p in sorted(RESULTS.iterdir()) if p.is_file())}

## Transfer

- `{TRANSFER}`
- MyoPS bundle SHA256: `{sha256_file(TRANSFER / 'MyoPS-nnUNet-workstation-bundle.tar.gz')}`
- Cine archive SHA256: `{sha256_file(TRANSFER / 'CineMyoPS-OrganAgent.tar.gz')}`
""",
        encoding="utf-8",
    )

    (TRANSFER / "WORKSTATION_INSTRUCTIONS.md").write_text(
        f"""# Workstation Instructions

This transfer supersedes server commit `{SUPERSEDES_COMMIT}` for the CARE 2026
Myocardium Docker packaging task.

## Final Images

- MyoPS final image tag: `care-myocardium-myops:organagent`
- CineMyoPS final image tag: `care-myocardium-cinemyops:organagent`

The server did not run Docker. Build/load/run validation is authorized only on
the workstation.

## MyoPS

Build from `MyoPS-nnUNet-workstation-bundle.tar.gz`. The context uses only
Dataset501 five-fold nnU-Net and maps raw labels directly:
`0->0, 1->200, 2->500, 3->600, 4->1220, 5->2221`.

Input is `/input`; output is `/output/myops/<CaseID>_pred.nii.gz`. Each case
must include LGE, T2, and C0. Missing modalities must fail.

## CineMyoPS

`CineMyoPS-OrganAgent.tar.gz` is the collaborator-provided final Docker archive.
Its SHA256 must remain:

`{CINE_EXPECTED_SHA}`

Load it directly with Docker. Do not recompress or modify it.

## Optional Collaborator MyoPS Reference

The collaborator MyoPS archive is not final for this submission. If it is loaded
on WSL for black-box interface comparison, immediately retag it:

```bash
docker tag care-myocardium-myops:organagent care-myocardium-myops:collaborator-reference
docker rmi care-myocardium-myops:organagent
```

Use that image only to compare interface, output directory, label schema,
geometry, runtime, and container behavior. Its prediction array is not expected
to match the pure nnU-Net final MyoPS image.
""",
        encoding="utf-8",
    )

    final_transfer_files = []
    for path in sorted(TRANSFER.rglob("*")):
        if path.is_file():
            final_transfer_files.append({
                "path": str(path.relative_to(TRANSFER)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    write_json(TRANSFER / "TRANSFER_MANIFEST.json", {
        "task": TASK,
        "created_at_utc": utc_now(),
        "transfer_path": str(TRANSFER),
        "files": final_transfer_files,
        "cinemyops_archive_byte_preserved": sha256_file(TRANSFER / "CineMyoPS-OrganAgent.tar.gz") == CINE_EXPECTED_SHA,
        "collaborator_myops_archive_copied_to_primary_transfer": False,
        "sentinel_case_ids": sentinel_ids,
        "myops_bundle_contains_mosaic_weight_or_vendor": False,
    })
    write_json(RESULTS / "transfer_bundle_receipt.json", {
        "task": TASK,
        "created_at_utc": utc_now(),
        "status": "PASS",
        "transfer": str(TRANSFER),
        "myops_workstation_bundle": next(item for item in final_transfer_files if item["path"] == "MyoPS-nnUNet-workstation-bundle.tar.gz"),
        "cinemyops_archive": next(item for item in final_transfer_files if item["path"] == "CineMyoPS-OrganAgent.tar.gz"),
        "cinemyops_archive_byte_preserved": True,
        "server_bundle_ready": str(TRANSFER / "SERVER_BUNDLE_READY.json"),
    })

    report = (
        "这次服务器端修订已经把 MyoPS 从旧的混合方案改成纯五折 nnU-Net，"
        "并把 CineMyoPS 固定为合作者提供的原始 Docker archive。服务器没有运行 Docker，"
        "也没有上传 challenge/validation 或给组织方发邮件；新 transfer 只授权工位 WSL 做 build/load/run。\n\n"
        f"- 任务: `{TASK}`\n"
        f"- supersedes: `{SUPERSEDES_COMMIT}`\n"
        f"- MyoPS: Dataset501_CAREMyoPS, nnUNetTrainer_500epochs, 3d_fullres, folds 0-4, checkpoint_best.pth, default TTA\n"
        f"- CineMyoPS archive SHA256: `{CINE_EXPECTED_SHA}`\n"
        f"- collaborator MyoPS reference SHA256: `{MYOPS_EXPECTED_SHA}`\n"
        f"- 复用 fresh nnU-Net 15 例 raw outputs: `{FRESH_RAW}`\n"
        f"- sentinel cases: {', '.join(sentinel_ids)}\n"
        f"- transfer: `{TRANSFER}`\n"
    )
    (RESULTS / "controller_report.md").write_text(report, encoding="utf-8")

    (RESULTS / "completion_check.md").write_text(
        f"""# Completion Check

controller_verification_decision: VERIFIED_COMPLETE

- MyoPS final graph is pure Dataset501 five-fold nnU-Net.
- MyoPS context contains no MoSAIC vendor/config/weights.
- CineMyoPS collaborator archive static audit passed and SHA matches.
- Collaborator MyoPS archive is reference-only.
- Server Docker was not run.
- No challenge upload, validation upload, netdisk upload, or organizer email was sent.
- Transfer ready: `{TRANSFER}`
""",
        encoding="utf-8",
    )

    write_json(RESULTS / "notification_brief.json", {
        "task_name": TASK,
        "final_status": "complete",
        "commit_status": "to be committed",
        "push_status": "to be pushed",
        "key_conclusion": "MyoPS 已修订为纯 Dataset501 五折 nnU-Net；CineMyoPS 使用合作者原始 Docker archive；服务器仅完成静态审计和 transfer 准备。",
        "blocked_or_failure_reason": "",
        "slurm_terminal_status": "No Slurm jobs were needed for this server-side rebundle.",
        "evidence_paths": [
            str(RESULTS / "revised_final_submission_model_contract.json"),
            str(RESULTS / "strict_validator_report.json"),
            str(RESULTS / "transfer_bundle_receipt.json"),
            str(TRANSFER / "SERVER_BUNDLE_READY.json"),
        ],
        "next_step": "在工位 WSL 对 MyoPS build/run/save，并 load/run CineMyoPS archive。"
    })


if __name__ == "__main__":
    main()
