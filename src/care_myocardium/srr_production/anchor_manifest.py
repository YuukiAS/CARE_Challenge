"""OOF nnU-Net anchor manifest and raw/safety context helpers for MyoPS SRR."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
from scipy.ndimage import generate_binary_structure, label


CLASS_ORDER = ["background", "myocardium", "LV_blood", "RV_blood", "edema", "scar"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def image_geom(path: Path) -> dict[str, Any]:
    img = sitk.ReadImage(str(path))
    return {
        "shape_zyx": list(reversed(img.GetSize())),
        "spacing_xyz": list(img.GetSpacing()),
        "origin_xyz": list(img.GetOrigin()),
        "direction": list(img.GetDirection()),
    }


def assert_split_match(protocol_split: Path, nnunet_split: Path) -> None:
    proto = load_json(protocol_split)["folds"]
    nnunet = load_json(nnunet_split)
    if len(proto) != len(nnunet):
        raise ValueError("protocol split and nnU-Net split fold counts differ")
    for idx, (a, b) in enumerate(zip(proto, nnunet)):
        if sorted(a["train"]) != sorted(b["train"]) or sorted(a["val"]) != sorted(b["val"]):
            raise ValueError(f"protocol split and nnU-Net split differ at fold {idx}")


def find_anchor_paths(case_id: str, anchor_root: Path) -> tuple[int, Path, Path]:
    matches: list[tuple[int, Path, Path]] = []
    for fold_dir in sorted(anchor_root.glob("fold_*")):
        try:
            fold = int(fold_dir.name.split("_", 1)[1])
        except (IndexError, ValueError):
            continue
        prob_path = fold_dir / "validation" / f"{case_id}.npz"
        pred_path = fold_dir / "validation" / f"{case_id}.nii.gz"
        if prob_path.is_file() and pred_path.is_file():
            matches.append((fold, prob_path, pred_path))
    if not matches:
        raise FileNotFoundError(f"nnU-Net OOF anchor not found for {case_id} under {anchor_root}")
    if len(matches) > 1:
        raise ValueError(f"case {case_id} has multiple OOF anchor matches: {[m[0] for m in matches]}")
    return matches[0]


def load_anchor_probabilities(prob_path: Path, reference_shape: tuple[int, int, int]) -> np.ndarray:
    with np.load(prob_path) as data:
        if "probabilities" not in data:
            raise KeyError(f"{prob_path} does not contain a 'probabilities' array")
        probs = data["probabilities"].astype(np.float32, copy=False)
    if probs.ndim != 4 or probs.shape[0] < 6:
        raise ValueError(f"{prob_path} must have shape (C,D,H,W) with at least 6 classes, got {probs.shape}")
    probs = probs[:6]
    if tuple(probs.shape[-3:]) != tuple(reference_shape):
        raise ValueError(f"{prob_path} spatial shape {probs.shape[-3:]} does not match label shape {reference_shape}")
    return np.clip(probs, 0.0, 1.0).astype(np.float32, copy=False)


def load_component_features(pred_path: Path, reference_shape: tuple[int, int, int]) -> np.ndarray:
    pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
    if tuple(pred.shape) != tuple(reference_shape):
        raise ValueError(f"{pred_path} spatial shape {pred.shape} does not match label shape {reference_shape}")
    components = []
    for cls in (5, 4):
        cc, n_cc = label((pred == cls).astype(bool), structure=generate_binary_structure(pred.ndim, 1))
        components.append((cc > 0 if n_cc > 0 else np.zeros_like(pred, dtype=bool)).astype(np.float32, copy=False))
    return np.stack(components, axis=0).astype(np.float32, copy=False)


def safety_context_from_raw_anchor(
    raw_anchor: np.ndarray,
    raw_components: np.ndarray,
    availability: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Return derived context for no-T2 safety without mutating raw OOF anchor."""

    safety_anchor = raw_anchor.copy()
    safety_components = raw_components.copy()
    t2_present = bool(np.asarray(availability)[1] > 0)
    if not t2_present:
        safety_anchor[4] = 0.0
        if safety_components.shape[0] > 1:
            safety_components[1] = 0.0
    return (
        safety_anchor,
        safety_components,
        {
            "raw_anchor_preserved": True,
            "derived_context": "no_t2_edema_channel_zeroed" if not t2_present else "raw_anchor_passthrough",
            "t2_present": t2_present,
            "raw_edema_anchor_nonzero_voxels": int(np.count_nonzero(raw_anchor[4] > 0)),
            "safety_edema_anchor_nonzero_voxels": int(np.count_nonzero(safety_anchor[4] > 0)),
        },
    )


def build_anchor_manifest(
    *,
    repo_root: Path,
    anchor_root: Path,
    protocol_split: Path,
    nnunet_split: Path,
    raw_root: Path,
    preprocessed_root: Path,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Build the raw OOF anchor manifest shared by validators, runners, and inference."""

    assert_split_match(protocol_split, nnunet_split)
    split_hash = sha256_file(protocol_split)
    nnunet_split_hash = sha256_file(nnunet_split)
    dataset_json = anchor_root / "dataset.json"
    plans_json = anchor_root / "plans.json"
    checkpoints: dict[int, dict[str, str]] = {}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    missing: list[str] = []
    for fold_row in load_json(protocol_split)["folds"]:
        fold = int(fold_row["fold"])
        ckpt = anchor_root / f"fold_{fold}/checkpoint_best.pth"
        ckpt_final = anchor_root / f"fold_{fold}/checkpoint_final.pth"
        if not ckpt.is_file():
            missing.append(rel(ckpt, repo_root))
            continue
        checkpoints[fold] = {
            "checkpoint_best_path": rel(ckpt, repo_root),
            "checkpoint_best_sha256": sha256_file(ckpt),
            "checkpoint_final_path": rel(ckpt_final, repo_root) if ckpt_final.is_file() else "missing",
            "checkpoint_final_sha256": sha256_file(ckpt_final) if ckpt_final.is_file() else "missing",
        }
        for case_id in sorted(fold_row["val"]):
            if case_id in seen:
                raise ValueError(f"duplicate validation case in OOF folds: {case_id}")
            seen.add(case_id)
            prob = anchor_root / f"fold_{fold}/validation/{case_id}.npz"
            pred = anchor_root / f"fold_{fold}/validation/{case_id}.nii.gz"
            label_path = raw_root / "labelsTr" / f"{case_id}.nii.gz"
            prep = preprocessed_root / f"{case_id}.pkl"
            missing_before = len(missing)
            for required in (prob, pred, label_path, prep):
                if not required.is_file():
                    missing.append(rel(required, repo_root))
            if len(missing) != missing_before:
                continue
            with np.load(prob) as data:
                if "probabilities" not in data:
                    raise ValueError(f"{prob} lacks probabilities key")
                shape = list(data["probabilities"].shape)
                dtype = str(data["probabilities"].dtype)
            pred_geom = image_geom(pred)
            label_geom = image_geom(label_path)
            if shape[0] != 6 or shape[-3:] != label_geom["shape_zyx"] or pred_geom["shape_zyx"] != label_geom["shape_zyx"]:
                raise ValueError(
                    f"shape mismatch for {case_id}: prob={shape}, pred={pred_geom['shape_zyx']}, label={label_geom['shape_zyx']}"
                )
            rows.append(
                {
                    "case_id": case_id,
                    "source_fold": fold,
                    "probability_path": rel(prob, repo_root),
                    "probability_sha256": sha256_file(prob),
                    "prediction_path": rel(pred, repo_root),
                    "prediction_sha256": sha256_file(pred),
                    "nnunet_checkpoint_path": checkpoints[fold]["checkpoint_best_path"],
                    "checkpoint_sha256": checkpoints[fold]["checkpoint_best_sha256"],
                    "trainer": "nnUNetTrainer_500epochs",
                    "plans": "nnUNetPlans",
                    "config": "3d_fullres",
                    "dataset_json_path": rel(dataset_json, repo_root),
                    "dataset_json_sha256": sha256_file(dataset_json),
                    "plans_json_path": rel(plans_json, repo_root),
                    "plans_json_sha256": sha256_file(plans_json),
                    "split_path": rel(protocol_split, repo_root),
                    "split_hash": split_hash,
                    "nnunet_split_path": rel(nnunet_split, repo_root),
                    "nnunet_split_hash": nnunet_split_hash,
                    "preprocessing_path": rel(prep, repo_root),
                    "preprocessing_hash": sha256_file(prep),
                    "class_order": CLASS_ORDER,
                    "probability_key": "probabilities",
                    "tensor_shape": shape,
                    "tensor_dtype": dtype,
                    "spacing_affine": {"prediction": pred_geom, "label": label_geom},
                    "is_oof": True,
                    "anchor_semantics": "raw_oof_anchor_unmodified",
                }
            )
    raw_cases = {p.name.replace(".nii.gz", "") for p in (raw_root / "labelsTr").glob("*.nii.gz")}
    missing_cases = sorted(raw_cases - seen)
    if missing or missing_cases or len(rows) != len(raw_cases):
        raise FileNotFoundError(
            "BATCH_2A_BLOCKED_MISSING_RAW_OOF_ANCHOR: "
            + json.dumps({"missing_files": missing[:20], "missing_cases": missing_cases[:20], "rows": len(rows), "raw_cases": len(raw_cases)})
        )
    manifest = {
        "schema_version": 2,
        "status": "COMPLETE_RAW_REAL_OOF_ANCHOR",
        "case_count": len(rows),
        "fold_counts": {str(f): sum(1 for row in rows if row["source_fold"] == f) for f in range(5)},
        "unique_cases": len({row["case_id"] for row in rows}),
        "anchor_root": rel(anchor_root, repo_root),
        "split_hash": split_hash,
        "nnunet_split_hash": nnunet_split_hash,
        "checkpoints": checkpoints,
        "entries": sorted(rows, key=lambda row: row["case_id"]),
    }
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest

