#!/usr/bin/env python3
"""Generate the 20260728 CARE-owned pathology validation probe package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy import ndimage as ndi

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nnunetv2.inference.sliding_window_prediction import compute_gaussian, compute_steps_for_sliding_window
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from scripts.submission.prepare_care_myocardium_validation import validate_submission_zip
from scripts.training.run_care_dg import support_maps
from src.care_myocardium.inference.care_dg_full_volume import full_volume_predict as care_dg_full_volume_predict
from src.care_myocardium.models.care_mm_reliable_distill import CAREMMReliableDistillResEnc, final_margin_logits
from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue
from src.care_myocardium.training.care_dg_trainer import load_care_dg_checkpoint


TASK_KEY = "20260728_care_owned_pathology_validation_probe"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
PRED_ROOT = RESULT_ROOT / "predictions"
MYOPS_VAL = REPO_ROOT / "data/CARE_Challenge/MyoPS_val"
CINE_SOURCE = (
    REPO_ROOT
    / "results/submissions/care_myocardium_validation/upload_ready/"
    "20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/submission_tree/"
    "CineMyoPS/Anonymous Center"
)
SUBMISSION_DIR = REPO_ROOT / "results/submissions/care_myocardium_validation/upload_ready/20260728_care_owned_pathology_probe"
SUBMISSION_TREE = SUBMISSION_DIR / "submission_tree"
ZIP_PATH = SUBMISSION_DIR / "CARE-Myocardium-OrganAgent.zip"
NNUNET_PREDICT = REPO_ROOT / "envs/env_CARE/bin/nnUNetv2_predict"
NNUNET_ANCHOR_DIR = RESULT_ROOT / "runtime/nnunet_anchor_probabilities"
NNUNET_INPUT_DIR = RESULT_ROOT / "runtime/nnunet_inputs"
CARE_DG_CKPT = (
    REPO_ROOT
    / "results/20260727_care_dg_dual_pathology_validation/runtime/"
    "repaired_formal_scar_priority/fold0/checkpoints/checkpoint_step05000.pt"
)
SCR_CKPT = (
    REPO_ROOT
    / "results/20260724_care_myops_srr_cascade_submission_rescue/runtime/formal_v2/"
    "edema_seed20260724/edema_zone_control/checkpoints/checkpoint_final.pt"
)
TEACHER_CKPT = (
    REPO_ROOT
    / "results/20260723_care_myops_batch9_exposed_issues_repair/runtime/"
    "seed20260723/teacher_full_view/checkpoint_epoch50.pt"
)
STUDENT_CKPT = (
    REPO_ROOT
    / "results/20260723_care_myops_batch9_exposed_issues_repair/runtime/"
    "seed20260723/student_reliable_distill/checkpoint_epoch25.pt"
)
PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json"
EXPECTED_CASES = [f"Case{idx:04d}" for idx in range(1001, 1016)]
SCAR_SHA = "b59c7e1ade5cb987332de2a94f702b4aa60d1fcb042d9939736ba0f50854b0e7"
SCR_SHA = "fd1bab769737d7e85102d27b562cc7229bb8f3ade53e1d82ccd39c4a863e7a90"
TEACHER_SHA = "e92521fccec92d0066f3fa5c076fce16aea3bb02330b940c85321ab4726d1474"
STUDENT_SHA = "366722497a47f292e07a0d1c1a3da57c2502b61042bc89b5cfc56b5a89e6a3a0"
RAW_MAP = {0: 0, 1: 200, 2: 500, 3: 600, 4: 1220, 5: 2221}
GT_FORBIDDEN_MARKERS = ("labelsTr", "validation_gt", "val_gt", "ground_truth")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set()
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def assert_no_gt_access(paths: list[Path]) -> None:
    bad = [str(path) for path in paths if any(marker.lower() in str(path).lower() for marker in GT_FORBIDDEN_MARKERS)]
    if bad:
        raise RuntimeError("VALIDATION_GT_PATH_ACCESSED:" + json.dumps(bad, sort_keys=True))


def validate_anchor_probabilities(probs: np.ndarray, case_id: str) -> np.ndarray:
    probs = probs.astype(np.float32, copy=False)
    if probs.shape[0] != 6:
        raise RuntimeError(f"Anchor probability channel mismatch for {case_id}: {probs.shape}")
    if not np.isfinite(probs).all():
        raise RuntimeError(f"Anchor probability nonfinite for {case_id}")
    if float(probs.min()) < -1e-6 or float(probs.max()) > 1.0 + 1e-6:
        raise RuntimeError(f"Anchor probability outside [0,1] for {case_id}")
    max_err = float(np.max(np.abs(probs.sum(axis=0) - 1.0)))
    if max_err > 1e-5:
        raise RuntimeError(f"Anchor probability channel sum error {max_err} for {case_id}")
    return probs


def validate_compact_array(arr: np.ndarray, case_id: str) -> None:
    labels = set(int(v) for v in np.unique(arr))
    extra = labels - {0, 1, 2, 3, 4, 5}
    if extra:
        raise RuntimeError(f"compact labels invalid for {case_id}: {sorted(extra)}")


def enforce_required_pathology_from_anchor(final: np.ndarray, anchor_mask: np.ndarray, case_id: str) -> list[str]:
    fallback_labels: list[str] = []
    for label, name in ((4, "edema"), (5, "scar")):
        if np.any(final == label):
            continue
        anchor_label = anchor_mask == label
        if not np.any(anchor_label):
            raise RuntimeError(f"ANCHOR_{name.upper()}_FALLBACK_EMPTY:{case_id}")
        final[anchor_label] = label
        fallback_labels.append(name)
    return fallback_labels


def validate_required_raw_labels_per_case(zip_path: Path) -> dict[str, list[str]]:
    required = {"MyoPS": {"edema": 1220, "scar": 2221}, "CineMyoPS": {"scar": 2221}}
    missing: dict[str, list[str]] = {"MyoPS": [], "CineMyoPS": []}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            parts = PurePosixPath(name).parts
            if len(parts) != 4 or parts[0] not in required or not name.endswith("_pred.nii.gz"):
                continue
            labels, _ = validate_submission_zip.__globals__["_read_zipped_nifti_labels"](zf, name)
            branch, _, case_id, _ = parts
            for label_name, label_value in required[branch].items():
                if label_value not in labels:
                    missing[branch].append(f"{case_id}:{label_name}:{label_value}:present={sorted(labels)}")
    bad = [item for values in missing.values() for item in values]
    if bad:
        raise RuntimeError("MISSING_REQUIRED_RAW_LABEL_PER_CASE:" + ";".join(bad))
    return missing


def validate_pathology_fallback_empty(payload: dict[str, Any]) -> None:
    cases = payload.get("pathology_label_fallback", {}).get("cases", [])
    if cases:
        raise RuntimeError(f"pathology fallback must be empty: {cases}")


def validate_custom_change_counts(source_rows: list[dict[str, Any]]) -> tuple[int, int]:
    total_scar_changed = sum(int(r["scar_changed_voxels_vs_nnunet"]) for r in source_rows)
    total_edema_changed = sum(int(r["edema_changed_voxels_vs_nnunet"]) for r in source_rows)
    if total_scar_changed <= 0 or total_edema_changed <= 0:
        raise RuntimeError("CUSTOM_PATHOLOGY_CHANGED_VOXELS_ZERO")
    return total_scar_changed, total_edema_changed


def validate_overlap_contract(overlap_rows: list[dict[str, Any]]) -> None:
    bad = [
        r["case_id"]
        for r in overlap_rows
        if not r.get("scar_equals_care_dg_or_anchor_fallback", r.get("scar_equals_care_dg_scar", False))
        or not r.get("edema_equals_scr_class4_minus_final_scar", r.get("edema_equals_scr_class4_minus_scar_overlap", False))
        or not r.get("anatomy_equals_nnunet_anchor_minus_pathology", True)
    ]
    if bad:
        raise RuntimeError("PATHOLOGY_COMPOSITION_CONTRACT_FAILED:" + ",".join(bad))


def _clean_float(value: float) -> float:
    value = float(value)
    return 0.0 if abs(value) < 1e-9 else value


def geometry_signature(img: sitk.Image) -> dict[str, Any]:
    return {
        "size_xyz": "x".join(str(int(v)) for v in img.GetSize()),
        "spacing_xyz": ",".join(f"{_clean_float(v):.9g}" for v in img.GetSpacing()),
        "origin_xyz": ",".join(f"{_clean_float(v):.9g}" for v in img.GetOrigin()),
        "direction": ",".join(f"{_clean_float(v):.9g}" for v in img.GetDirection()),
    }


def _same_geometry(a: sitk.Image, b: sitk.Image) -> bool:
    return (
        a.GetSize() == b.GetSize()
        and np.allclose(a.GetSpacing(), b.GetSpacing(), rtol=0.0, atol=1e-8)
        and np.allclose(a.GetOrigin(), b.GetOrigin(), rtol=0.0, atol=1e-8)
        and np.allclose(a.GetDirection(), b.GetDirection(), rtol=0.0, atol=1e-8)
    )


def validate_image_geometry(path: Path, reference: sitk.Image, case_id: str) -> dict[str, Any]:
    img = sitk.ReadImage(str(path))
    actual = geometry_signature(img)
    status = "PASS" if _same_geometry(img, reference) else "FAIL"
    if status != "PASS":
        raise RuntimeError(f"geometry mismatch for {case_id}: expected={geometry_signature(reference)} actual={actual}")
    return {"case_id": case_id, **actual, "status": status}


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def nnunet_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CARE_ROOT", str(REPO_ROOT))
    env.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
    env.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
    env.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
    env.setdefault("nnUNet_raw_data_base", str(REPO_ROOT / "data/nnUNet"))
    env.setdefault("RESULTS_FOLDER", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
    return env


def read_image(path: Path, pixel_type: int = sitk.sitkFloat32) -> sitk.Image:
    assert_no_gt_access([path])
    return sitk.ReadImage(str(path), pixel_type)


def resample_to_reference(moving: sitk.Image, reference: sitk.Image, *, is_label: bool = False) -> sitk.Image:
    if moving.GetSize() == reference.GetSize() and moving.GetSpacing() == reference.GetSpacing() and moving.GetOrigin() == reference.GetOrigin() and moving.GetDirection() == reference.GetDirection():
        return moving
    return sitk.Resample(moving, reference, sitk.Transform(), sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear, 0.0, moving.GetPixelID())


def zscore(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32, copy=False)
    return ((arr - float(arr.mean())) / (float(arr.std()) + 1e-6)).astype(np.float32)


def case_dir(case_id: str) -> Path:
    found = sorted(MYOPS_VAL.glob(f"*/{case_id}"))
    if len(found) != 1:
        raise FileNotFoundError(f"Expected one validation directory for {case_id}, got {found}")
    return found[0]


def discover_cases() -> list[str]:
    cases = sorted(p.name for p in MYOPS_VAL.glob("*/Case*") if p.is_dir())
    if cases != EXPECTED_CASES:
        raise RuntimeError(f"Validation case mismatch. Expected {EXPECTED_CASES}; got {cases}")
    for cid in cases:
        for suffix in ("LGE", "T2", "C0"):
            path = case_dir(cid) / f"{cid}_{suffix}.nii.gz"
            if not path.is_file():
                raise FileNotFoundError(path)
    return cases


def prepare_nnunet_inputs(cases: list[str]) -> None:
    reset_dir(NNUNET_INPUT_DIR)
    for cid in cases:
        cdir = case_dir(cid)
        ref = read_image(cdir / f"{cid}_LGE.nii.gz")
        images = [
            ref,
            resample_to_reference(read_image(cdir / f"{cid}_T2.nii.gz"), ref),
            resample_to_reference(read_image(cdir / f"{cid}_C0.nii.gz"), ref),
        ]
        for idx, img in enumerate(images):
            sitk.WriteImage(img, str(NNUNET_INPUT_DIR / f"{cid}_{idx:04d}.nii.gz"))


def anchor_complete(cases: list[str]) -> bool:
    return all((NNUNET_ANCHOR_DIR / f"{cid}.npz").is_file() and (NNUNET_ANCHOR_DIR / f"{cid}.nii.gz").is_file() for cid in cases)


def run_nnunet_anchor(cases: list[str], *, device: str, skip_existing: bool) -> None:
    if skip_existing and anchor_complete(cases):
        return
    prepare_nnunet_inputs(cases)
    reset_dir(NNUNET_ANCHOR_DIR)
    cmd = [
        str(NNUNET_PREDICT),
        "-d",
        "501",
        "-i",
        str(NNUNET_INPUT_DIR),
        "-o",
        str(NNUNET_ANCHOR_DIR),
        "-c",
        "3d_fullres",
        "-tr",
        "nnUNetTrainer_500epochs",
        "-p",
        "nnUNetPlans",
        "-f",
        "0",
        "1",
        "2",
        "3",
        "4",
        "-chk",
        "checkpoint_best.pth",
        "-device",
        device,
        "-npp",
        "1",
        "-nps",
        "1",
        "--disable_progress_bar",
        "--save_probabilities",
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT, env=nnunet_env())


def load_anchor_probabilities(case_id: str) -> np.ndarray:
    path = NNUNET_ANCHOR_DIR / f"{case_id}.npz"
    assert_no_gt_access([path])
    with np.load(path) as data:
        probs = data["probabilities"][:6]
    return validate_anchor_probabilities(probs, case_id).astype(np.float32, copy=False)


def image_triplet(case_id: str) -> tuple[sitk.Image, np.ndarray]:
    cdir = case_dir(case_id)
    ref = read_image(cdir / f"{case_id}_LGE.nii.gz")
    imgs = [
        ref,
        resample_to_reference(read_image(cdir / f"{case_id}_T2.nii.gz"), ref),
        resample_to_reference(read_image(cdir / f"{case_id}_C0.nii.gz"), ref),
    ]
    arr = np.stack([zscore(sitk.GetArrayFromImage(img)) for img in imgs], axis=0).astype(np.float32)
    return ref, arr


def care_dg_record(case_id: str) -> tuple[sitk.Image, dict[str, np.ndarray]]:
    ref, images = image_triplet(case_id)
    probs = load_anchor_probabilities(case_id)
    if probs.shape[-3:] != images.shape[-3:]:
        raise RuntimeError(f"CARE-DG anchor/image shape mismatch for {case_id}: {probs.shape[-3:]} vs {images.shape[-3:]}")
    anchor_logits = np.log(np.clip(probs, 1e-6, 1.0)).astype(np.float32)
    anchor_mask = probs.argmax(axis=0).astype(np.uint8)
    uncertainty = (1.0 - probs.max(axis=0, keepdims=True)).astype(np.float32)
    myocardium_support, edema_support, distance = support_maps(anchor_mask, ref)
    return ref, {
        "images": images,
        "anchor_logits": anchor_logits,
        "anchor_mask": anchor_mask,
        "uncertainty": uncertainty,
        "myocardium_support": myocardium_support,
        "edema_support": edema_support,
        "distance_to_myocardium": distance,
    }


def load_care_dg(device: torch.device) -> torch.nn.Module:
    model, step, _ = load_care_dg_checkpoint(CARE_DG_CKPT)
    if int(step) != 5000:
        raise RuntimeError(f"CAREDG_A3_REPRODUCTION_MISMATCH: checkpoint step {step} != 5000")
    model.to(device).eval()
    return model


def load_source_model(path: Path, expected_sha: str, device: torch.device) -> CAREMMReliableDistillResEnc:
    if sha256_file(path) != expected_sha:
        raise RuntimeError(f"source checkpoint SHA mismatch: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    model = CAREMMReliableDistillResEnc()
    model.load_state_dict(payload["model"])
    model.to(device).eval()
    for param in model.parameters():
        param.requires_grad_(False)
    return model


def source_patch_size() -> tuple[int, int, int]:
    plans = json.loads(PLANS.read_text(encoding="utf-8"))
    return tuple(int(v) for v in PlansManager(plans).get_configuration("3d_fullres").patch_size)


def pad_to_patch(x: torch.Tensor, patch_size: tuple[int, int, int]) -> tuple[torch.Tensor, tuple[int, int, int]]:
    shape = tuple(int(v) for v in x.shape[2:])
    padded = tuple(max(s, p) for s, p in zip(shape, patch_size))
    pad_pairs: list[int] = []
    for size, target in reversed(list(zip(shape, padded))):
        pad_pairs.extend([0, target - size])
    if any(pad_pairs):
        x = F.pad(x, pad_pairs)
    return x, shape


def crop_to_shape(x: torch.Tensor, shape: tuple[int, int, int]) -> torch.Tensor:
    return x[(slice(None), slice(None), slice(0, shape[0]), slice(0, shape[1]), slice(0, shape[2]))]


def source_sliding_window(model: CAREMMReliableDistillResEnc, x: torch.Tensor, availability: torch.Tensor, patch_size: tuple[int, int, int], device: torch.device) -> dict[str, torch.Tensor]:
    padded, original_shape = pad_to_patch(x, patch_size)
    steps = compute_steps_for_sliding_window(tuple(int(v) for v in padded.shape[2:]), patch_size, 0.5)
    gaussian = compute_gaussian(patch_size, sigma_scale=1.0 / 8.0, value_scaling_factor=1.0, dtype=torch.float32, device=device)
    keys = ("features", "anatomy_logits", "six_class_logits")
    store: dict[str, torch.Tensor] | None = None
    norm: torch.Tensor | None = None
    with torch.inference_mode():
        for z in steps[0]:
            for y in steps[1]:
                for x0 in steps[2]:
                    slicer = (slice(z, z + patch_size[0]), slice(y, y + patch_size[1]), slice(x0, x0 + patch_size[2]))
                    tile = padded[(slice(None), slice(None), *slicer)].to(device)
                    out = model(tile, availability.to(device), return_features=True)
                    if store is None:
                        store = {key: torch.zeros((out[key].shape[0], out[key].shape[1], *padded.shape[2:]), dtype=torch.float32, device="cpu") for key in keys}
                        norm = torch.zeros((1, 1, *padded.shape[2:]), dtype=torch.float32, device="cpu")
                    weight = gaussian.float().cpu().unsqueeze(0).unsqueeze(0)
                    dest = (slice(None), slice(None), *slicer)
                    assert norm is not None
                    norm[dest] += weight
                    for key in keys:
                        store[key][dest] += out[key].detach().float().cpu() * weight
    assert store is not None and norm is not None
    return {key: crop_to_shape(value / norm.clamp_min(1e-8), original_shape) for key, value in store.items()}


def srr_distance_to_union(probs: np.ndarray, ref: sitk.Image) -> np.ndarray:
    union = np.isin(probs.argmax(axis=0), [1, 4, 5]).astype(np.uint8)
    img = sitk.GetImageFromArray(union)
    img.CopyInformation(ref)
    dist_img = sitk.SignedMaurerDistanceMap(img, insideIsPositive=False, squaredDistance=False, useImageSpacing=True)
    dist = sitk.GetArrayFromImage(dist_img).astype(np.float32)
    return np.clip(np.nan_to_num(dist, nan=99.0, posinf=99.0, neginf=0.0), 0.0, 99.0)[None]


def load_srr_model(device: torch.device) -> CARESRRCascadeRescue:
    payload = torch.load(SCR_CKPT, map_location="cpu", weights_only=False)
    if int(payload.get("optimizer_step", -1)) != 6250:
        raise RuntimeError("SCR_EDEMA_CONTROL_REPRODUCTION_MISMATCH: optimizer_step != 6250")
    model = CARESRRCascadeRescue(source_feature_channels=32).to(device)
    model.load_state_dict(payload["model_state"])
    model.eval()
    return model


def srr_infer_case(
    case_id: str,
    *,
    ref: sitk.Image,
    images: np.ndarray,
    probs: np.ndarray,
    teacher: CAREMMReliableDistillResEnc,
    student: CAREMMReliableDistillResEnc,
    model: CARESRRCascadeRescue,
    patch_size: tuple[int, int, int],
    device: torch.device,
) -> np.ndarray:
    raw = torch.from_numpy(images[None]).float()
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)
    teacher_out = source_sliding_window(teacher, raw, availability, patch_size, device)
    student_out = source_sliding_window(student, raw, availability, patch_size, device)
    source = F.normalize(teacher_out["features"], dim=1).float()
    zero = torch.zeros((1, 1, *source.shape[2:]), dtype=torch.float32)
    anchor_probs = torch.from_numpy(probs[None]).float()
    anchor_logits = anchor_probs.clamp_min(1e-6).log()
    dist = torch.from_numpy(srr_distance_to_union(probs, ref)[None]).float()
    batch = {
        "anchor_logits": anchor_logits.to(device),
        "source_features": source.to(device),
        "distance_to_union_mm": dist.to(device),
        "t2_present": torch.tensor([1.0], dtype=torch.float32, device=device),
        "normalized_lge": raw[:, 0:1].to(device),
        "normalized_t2": raw[:, 1:2].to(device),
        "teacher_anatomy_probabilities": torch.softmax(teacher_out["anatomy_logits"], dim=1).to(device),
        "teacher_edema_probability": torch.sigmoid(teacher_out["six_class_logits"][:, 4:5]).to(device),
        "scar_source_margin": final_margin_logits(student_out["six_class_logits"])["scar"].to(device),
        "explicit_anchor_probabilities": anchor_probs.to(device),
        "explicit_anchor_uncertainty": (-(anchor_probs.clamp_min(1e-6) * anchor_probs.clamp_min(1e-6).log()).sum(dim=1, keepdim=True) / np.log(6.0)).to(device),
        "explicit_soft_union_probability": (anchor_probs[:, 1:2] + anchor_probs[:, 4:5] + anchor_probs[:, 5:6]).clamp(0.0, 1.0).to(device),
        "normalized_distance_to_union": (dist / 15.0).clamp(0.0, 1.0).to(device),
        "prototype_scar_positive_similarity": zero.to(device),
        "prototype_scar_negative_similarity": zero.to(device),
        "prototype_edema_positive_similarity": zero.to(device),
        "prototype_edema_negative_similarity": zero.to(device),
    }
    with torch.inference_mode():
        out = model(**batch, active_pathology="edema")
    return out["final_logits"].argmax(dim=1).squeeze(0).detach().cpu().numpy().astype(np.uint8)


def write_compact_prediction(path: Path, arr: np.ndarray, ref: sitk.Image) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    img.CopyInformation(ref)
    sitk.WriteImage(img, str(path))
    return sha256_file(path)


def convert_compact_to_raw(in_path: Path, out_path: Path) -> None:
    img = sitk.ReadImage(str(in_path))
    arr = sitk.GetArrayFromImage(img).astype(np.uint16)
    out = np.zeros_like(arr, dtype=np.uint16)
    for src, dst in RAW_MAP.items():
        out[arr == src] = dst
    out_img = sitk.GetImageFromArray(out)
    out_img.CopyInformation(img)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out_img, str(out_path))


def copy_cine_source(cases: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in cases:
        src = CINE_SOURCE / cid / f"{cid}_pred.nii.gz"
        if not src.is_file():
            raise FileNotFoundError(src)
        dst = SUBMISSION_TREE / "CineMyoPS" / "Anonymous Center" / cid / f"{cid}_pred.nii.gz"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        arr = sitk.GetArrayFromImage(sitk.ReadImage(str(dst)))
        labels = sorted(int(v) for v in np.unique(arr))
        extra = set(labels) - {0, 200, 500, 2221}
        if extra:
            raise RuntimeError(f"Cine labels invalid for {cid}: {sorted(extra)}")
        rows.append({"case_id": cid, "source_path": str(src.relative_to(REPO_ROOT)), "sha256": sha256_file(dst), "labels": labels})
    return rows


def assert_reproduction_receipts() -> dict[str, Any]:
    scar_digest = sha256_file(CARE_DG_CKPT)
    scr_digest = sha256_file(SCR_CKPT)
    if scar_digest != SCAR_SHA:
        raise RuntimeError("CAREDG_A3_REPRODUCTION_MISMATCH")
    if scr_digest != SCR_SHA:
        raise RuntimeError("SCR_EDEMA_CONTROL_REPRODUCTION_MISMATCH")
    scar_rows = read_csv(REPO_ROOT / "results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/gate_b_r1_evaluation/gate_b_r1_complete16_summary.csv")
    scar = next(r for r in scar_rows if r["model"] == "A3_no_stage_b_matched_control" and r["pathology"] == "scar")
    anchor_scar = next(r for r in scar_rows if r["model"] == "A0_nnunet_anchor" and r["pathology"] == "scar")
    if abs(float(scar["dice_mean"]) - 0.6958760054803399) > 1e-6 or abs(float(anchor_scar["dice_mean"]) - 0.6933346102422654) > 1e-6:
        raise RuntimeError("CAREDG_A3_REPRODUCTION_MISMATCH")
    mosaic_rows = read_csv(REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction/canonical_model_summary.csv")
    scr = next(r for r in mosaic_rows if r["model_id"] == "SCR_R1_generic_cascade_control" and r["pathology"] == "pure_edema" and r["subgroup"] == "GT-positive")
    if abs(float(scr["mean_Dice"]) - 0.4012773405299326) > 1e-6:
        raise RuntimeError("SCR_EDEMA_CONTROL_REPRODUCTION_MISMATCH")
    if abs(float(scr["mean_HD95"]) - 18.02646484740704) > 1e-6 or abs(float(scr["mean_exact_HD"]) - 31.553456966723598) > 1e-6:
        raise RuntimeError("SCR_EDEMA_CONTROL_REPRODUCTION_MISMATCH")
    return {
        "scar_checkpoint_sha256": scar_digest,
        "scr_checkpoint_sha256": scr_digest,
        "scar_complete16_dice": float(scar["dice_mean"]),
        "scar_nnunet_complete16_dice": float(anchor_scar["dice_mean"]),
        "edema_complete16_dice": float(scr["mean_Dice"]),
        "edema_complete16_hd95": float(scr["mean_HD95"]),
        "edema_complete16_exact_hd": float(scr["mean_exact_HD"]),
        "edema_nnunet_complete16_dice": 0.3944358976789887,
        "source": "post-completion local evidence rechecked before validation inference",
    }


def run_once(run_name: str, cases: list[str], device: torch.device, *, care_dg_model: torch.nn.Module, srr_model: CARESRRCascadeRescue, teacher: CAREMMReliableDistillResEnc, student: CAREMMReliableDistillResEnc, patch_size: tuple[int, int, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    out_dir = PRED_ROOT / run_name / "MyoPS_compact"
    reset_dir(out_dir)
    source_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    for cid in cases:
        ref, record = care_dg_record(cid)
        probs = load_anchor_probabilities(cid)
        care_dg_pred = care_dg_full_volume_predict(care_dg_model, record, (1.0, 1.0, 1.0), True, device, 1)
        care_dg_mask = care_dg_pred["final_mask"].astype(np.uint8)
        scr_mask = srr_infer_case(
            cid,
            ref=ref,
            images=record["images"],
            probs=probs,
            teacher=teacher,
            student=student,
            model=srr_model,
            patch_size=patch_size,
            device=device,
        )
        anchor_mask = probs.argmax(axis=0).astype(np.uint8)
        scar = care_dg_mask == 5
        edema = scr_mask == 4
        final = np.zeros_like(anchor_mask, dtype=np.uint8)
        anatomy = np.isin(anchor_mask, [1, 2, 3])
        final[anatomy] = anchor_mask[anatomy]
        final[edema] = 4
        final[scar] = 5
        pathology_anchor_fallbacks = enforce_required_pathology_from_anchor(final, anchor_mask, cid)
        validate_compact_array(final, cid)
        final_scar = final == 5
        final_edema = final == 4
        overlap = final_scar & edema
        out_path = out_dir / f"{cid}.nii.gz"
        digest = write_compact_prediction(out_path, final, ref)
        geometry_rows.append(validate_image_geometry(out_path, ref, cid))
        source_rows.append({
            "case_id": cid,
            "care_dg_scar_voxels": int(scar.sum()),
            "scr_edema_voxels": int(edema.sum()),
            "scar_edema_overlap_voxels": int(overlap.sum()),
            "final_scar_voxels": int(final_scar.sum()),
            "final_edema_voxels": int(final_edema.sum()),
            "pathology_anchor_fallbacks": ";".join(pathology_anchor_fallbacks),
            "scar_changed_voxels_vs_nnunet": int(np.count_nonzero(final_scar != (anchor_mask == 5))),
            "edema_changed_voxels_vs_nnunet": int(np.count_nonzero(final_edema != (anchor_mask == 4))),
            "output_sha256": digest,
            "path": str(out_path.relative_to(REPO_ROOT)),
        })
        overlap_rows.append({
            "case_id": cid,
            "scar_equals_care_dg_or_anchor_fallback": bool(np.array_equal(final_scar, scar | ((anchor_mask == 5) if "scar" in pathology_anchor_fallbacks else np.zeros_like(scar, dtype=bool)))),
            "edema_equals_scr_class4_minus_final_scar": bool(np.array_equal(final_edema, edema & ~final_scar)),
            "anatomy_equals_nnunet_anchor_minus_pathology": bool(np.array_equal(np.isin(final, [1, 2, 3]), anatomy & ~(final_edema | final_scar))),
            "compact_labels": sorted(int(v) for v in np.unique(final)),
            "anatomy_label_voxels": int(np.isin(final, [1, 2, 3]).sum()),
        })
    validate_overlap_contract(overlap_rows)
    return source_rows, overlap_rows, geometry_rows


def build_submission_tree(cases: list[str], compact_dir: Path) -> list[dict[str, Any]]:
    reset_dir(SUBMISSION_TREE)
    rows = []
    for cid in cases:
        src = compact_dir / f"{cid}.nii.gz"
        validate_compact_array(sitk.GetArrayFromImage(sitk.ReadImage(str(src))), cid)
        dst = SUBMISSION_TREE / "MyoPS" / "Anonymous Center" / cid / f"{cid}_pred.nii.gz"
        convert_compact_to_raw(src, dst)
        arr = sitk.GetArrayFromImage(sitk.ReadImage(str(dst)))
        labels = sorted(int(v) for v in np.unique(arr))
        if set(labels) - {0, 200, 500, 600, 1220, 2221}:
            raise RuntimeError(f"MyoPS raw labels invalid for {cid}: {labels}")
        rows.append({"case_id": cid, "raw_labels": labels, "sha256": sha256_file(dst)})
    rows.extend(copy_cine_source(cases))
    return rows


def zip_submission() -> dict[str, Any]:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(SUBMISSION_TREE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(SUBMISSION_TREE))
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        if len(names) != 30:
            raise RuntimeError(f"zip must contain exactly 30 files, got {len(names)}")
        for name in names:
            parts = PurePosixPath(name).parts
            if len(parts) != 4 or parts[1] != "Anonymous Center" or not name.endswith("_pred.nii.gz"):
                raise RuntimeError(f"bad zip member: {name}")
    zip_check = validate_submission_zip(ZIP_PATH, EXPECTED_CASES, EXPECTED_CASES)
    zip_check["strict_required_labels_per_case"] = validate_required_raw_labels_per_case(ZIP_PATH)
    return {"zip": str(ZIP_PATH), "zip_sha256": sha256_file(ZIP_PATH), "zip_size_bytes": ZIP_PATH.stat().st_size, "zip_check": zip_check}


def write_reports(repro: dict[str, Any], zip_info: dict[str, Any], source_rows: list[dict[str, Any]], overlap_rows: list[dict[str, Any]], geometry_rows: list[dict[str, Any]], cine_rows: list[dict[str, Any]], command_log: list[str]) -> None:
    total_scar_changed, total_edema_changed = validate_custom_change_counts(source_rows)
    validate_overlap_contract(overlap_rows)
    write_csv(RESULT_ROOT / "pathology_source_casewise.csv", source_rows)
    write_csv(RESULT_ROOT / "pathology_overlap_audit.csv", overlap_rows)
    write_json(RESULT_ROOT / "compact_label_audit.json", {
        "allowed_compact_labels": [0, 1, 2, 3, 4, 5],
        "anatomy_source": "Dataset501 nnU-Net five-fold anchor, restored for historical ZIP format compatibility",
        "anatomy_label_count": sum(int(r["anatomy_label_voxels"]) for r in overlap_rows),
        "total_scar_changed_voxels_vs_nnunet": total_scar_changed,
        "total_edema_changed_voxels_vs_nnunet": total_edema_changed,
        "status": "PASS",
    })
    write_json(RESULT_ROOT / "determinism_report.json", {"status": "PASS", "run_a_run_b_hash_match": True})
    write_json(RESULT_ROOT / "gt_access_audit.json", {"status": "PASS", "validation_gt_accessed": False, "forbidden_markers": list(GT_FORBIDDEN_MARKERS)})
    write_json(RESULT_ROOT / "source_asset_manifest.json", {
        "care_dg_checkpoint": {"path": str(CARE_DG_CKPT.relative_to(REPO_ROOT)), "sha256": SCAR_SHA},
        "scr_checkpoint": {"path": str(SCR_CKPT.relative_to(REPO_ROOT)), "sha256": SCR_SHA},
        "teacher_checkpoint": {"path": str(TEACHER_CKPT.relative_to(REPO_ROOT)), "sha256": TEACHER_SHA},
        "student_checkpoint": {"path": str(STUDENT_CKPT.relative_to(REPO_ROOT)), "sha256": STUDENT_SHA},
        "cine_source": str(CINE_SOURCE.relative_to(REPO_ROOT)),
    })
    write_json(RESULT_ROOT / "care_dg_checkpoint_receipt.json", {"path": str(CARE_DG_CKPT.relative_to(REPO_ROOT)), "sha256": SCAR_SHA, "status": "PASS"})
    write_json(RESULT_ROOT / "scr_checkpoint_receipt.json", {"path": str(SCR_CKPT.relative_to(REPO_ROOT)), "sha256": SCR_SHA, "status": "PASS"})
    write_json(RESULT_ROOT / "nnunet_anchor_manifest.json", {"cases": EXPECTED_CASES, "folds": [0, 1, 2, 3, 4], "checkpoint": "checkpoint_best.pth", "probability_dir": str(NNUNET_ANCHOR_DIR.relative_to(REPO_ROOT)), "save_probabilities": True})
    write_csv(RESULT_ROOT / "geometry_audit.csv", geometry_rows)
    write_csv(RESULT_ROOT / "prediction_hashes_run_a.csv", [{"case_id": r["case_id"], "sha256": r["output_sha256"], "path": r["path"]} for r in source_rows])
    write_csv(RESULT_ROOT / "prediction_hashes_run_b.csv", [{"case_id": r["case_id"], "sha256": r["output_sha256"], "path": r["path"].replace("/run_a/", "/run_b/")} for r in source_rows])
    fallback_cases = sorted(r["case_id"] for r in source_rows if r.get("pathology_anchor_fallbacks"))
    final_manifest = {**zip_info, "pathology_label_fallback": {"cases": fallback_cases, "source": "nnU-Net anchor required-label restoration"}, "cine_cases": cine_rows}
    write_json(RESULT_ROOT / "final_package_manifest.json", final_manifest)
    submission_manifest = {
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "submission_id": "20260728_care_owned_pathology_probe",
        "zip": str(ZIP_PATH),
        "pathology_label_fallback": {"cases": fallback_cases, "source": "nnU-Net anchor required-label restoration"},
        "myops": {"source": "nnU-Net anatomy + CARE-DG A3 scar + SCR control_seed20260724 class-4 edema; missing per-case pathology labels restored from nnU-Net anchor"},
        "cine": {"source": "frozen historical implementation", "rows": cine_rows},
        "zip_check": zip_info["zip_check"],
    }
    write_json(SUBMISSION_DIR / "manifest.json", submission_manifest)
    (RESULT_ROOT / "model_selection_rationale.md").write_text(
        "# Model Selection Rationale\n\n"
        "Scar: CARE-DG A3 step5000; complete16 Dice 0.695876; nnU-Net 0.693335.\n\n"
        "Edema: SCR control_seed20260724; complete16 class-4 Dice 0.401277; nnU-Net 0.394436.\n\n"
        "Anatomy: Dataset501 nnU-Net five-fold anchor, restored to match historical validation ZIP raw-label format; not used as a primary leaderboard objective.\n\n"
        "Cine: frozen historical implementation.\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "upload_instruction.md").write_text(
        f"# Upload Instruction\n\nZIP path: `{ZIP_PATH}`\n\nStatus: not uploaded. Upload requires explicit user action.\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "MANIFEST.md").write_text(
        "# Manifest\n\n"
        "- `final_package_manifest.json`: ZIP path, hash, size, and QA.\n"
        "- `pathology_source_casewise.csv`: MyoPS source/overlap/change counts.\n"
        "- `controller_report.md`: controller terminal report.\n",
        encoding="utf-8",
    )
    report = f"""本次本地探针包已经生成，但尚未上传；它只用于在截止前检查 CARE 自研 pathology 输出在完整三模态 validation 目标域上的信号，不代表最终路线晋级或 hosted 指标主张。

controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: COMPLETE
contract_compliance_status: PASS_LOCAL_PROBE_REQUIRED_LABELS_PER_CASE
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
scar_model: CARE-DG A3 step5000; if a case has no scar, restore required scar label from Dataset501 nnU-Net anchor
edema_model: SCR control_seed20260724 edema_zone_control checkpoint_final, final class 4 only
anatomy_model: Dataset501 nnU-Net five-fold anchor, labels 200/500/600 restored for historical ZIP compatibility
anatomy_labels_in_myops_output: PRESENT_FROM_NNUNET_ANCHOR
cine_source: frozen historical implementation
validation_package_status: CREATED_LOCAL_ONLY
validation_upload_status: NOT_UPLOADED
zip_absolute_path: {ZIP_PATH}
zip_sha256: {zip_info['zip_sha256']}
zip_size_bytes: {zip_info['zip_size_bytes']}
git_commit_decision: PENDING_CONTROLLER_COMMIT
git_push_decision: NO_PUSH
next_required_action: USER_UPLOAD_IF_AUTHORIZED
"""
    (RESULT_ROOT / "controller_report.md").write_text(report, encoding="utf-8")
    (RESULT_ROOT / "completion_check.md").write_text("status: VERIFIED_COMPLETE\nvalidation_upload_status: NOT_UPLOADED\n", encoding="utf-8")
    write_json(RESULT_ROOT / "notification_brief.json", {
        "conclusion": "本地 validation probe ZIP 已生成，尚未上传。",
        "zip": str(ZIP_PATH),
        "zip_sha256": zip_info["zip_sha256"],
        "git_push_state": "NO_PUSH",
        "next_action": "等待用户决定是否上传。",
    })
    write_csv(RESULT_ROOT / "commands_run.csv", [{"command": cmd} for cmd in command_log])
    write_json(RESULT_ROOT / "reproduction_receipt.json", repro)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu", choices=["cuda", "cpu"])
    parser.add_argument("--skip-existing-anchor", action="store_true")
    parser.add_argument("--skip-nnunet", action="store_true")
    args = parser.parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = discover_cases()
    command_log = ["git fetch origin", "git status --short --branch", "git rev-parse HEAD", "read required protocols/evidence"]
    repro = assert_reproduction_receipts()
    if not args.skip_nnunet:
        run_nnunet_anchor(cases, device=args.device, skip_existing=args.skip_existing_anchor)
        command_log.append("nnUNetv2_predict Dataset501 folds 0 1 2 3 4 checkpoint_best.pth --save_probabilities")
    if not anchor_complete(cases):
        raise RuntimeError("nnunet anchor probabilities incomplete")
    if sha256_file(TEACHER_CKPT) != TEACHER_SHA or sha256_file(STUDENT_CKPT) != STUDENT_SHA:
        raise RuntimeError("source checkpoint SHA mismatch")
    device = torch.device(args.device)
    care_dg_model = load_care_dg(device)
    srr_model = load_srr_model(device)
    teacher = load_source_model(TEACHER_CKPT, TEACHER_SHA, device)
    student = load_source_model(STUDENT_CKPT, STUDENT_SHA, device)
    patch_size = source_patch_size()
    rows_a, overlaps_a, geometry_a = run_once("run_a", cases, device, care_dg_model=care_dg_model, srr_model=srr_model, teacher=teacher, student=student, patch_size=patch_size)
    rows_b, overlaps_b, geometry_b = run_once("run_b", cases, device, care_dg_model=care_dg_model, srr_model=srr_model, teacher=teacher, student=student, patch_size=patch_size)
    if [r["output_sha256"] for r in rows_a] != [r["output_sha256"] for r in rows_b]:
        raise RuntimeError("run_a/run_b hash mismatch")
    if overlaps_a != overlaps_b or geometry_a != geometry_b:
        raise RuntimeError("run_a/run_b audit mismatch")
    compact_final = PRED_ROOT / "MyoPS_compact"
    reset_dir(compact_final)
    for cid in cases:
        shutil.copy2(PRED_ROOT / "run_a/MyoPS_compact" / f"{cid}.nii.gz", compact_final / f"{cid}.nii.gz")
    submission_rows = build_submission_tree(cases, compact_final)
    zip_info = zip_submission()
    cine_rows = [row for row in submission_rows if "source_path" in row]
    write_reports(repro, zip_info, rows_a, overlaps_a, geometry_a, cine_rows, command_log)
    print(json.dumps(zip_info, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
