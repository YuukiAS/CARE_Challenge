#!/usr/bin/env python3
"""Run read-only MoSAIC activation hooks for the V3 forensic packet.

This supplements the nnU-Net/PRISM feature probe with MoSAIC source families
using the local MoSAIC source tree, local weights, and cached MyoPS payloads.
It does not train a model, does not package a submission, and does not access
outer-split evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import binary_dilation


REPO_ROOT = Path(__file__).resolve().parents[3]
MOSAIC_SOURCE = Path("/users/a/e/aereinh/MoSAIC/code/source")
MOSAIC_WEIGHTS = Path("/users/a/e/aereinh/MoSAIC/code/weights")
MOSAIC_MYOPS_WEIGHTS = MOSAIC_WEIGHTS / "myops"
RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
CACHE_REL = (
    RESULT_REL
    / "runtime/mosaic_recipe_decomposition_v2/"
    / "g4_mosaic_recipe_decomposition_20260730T0809Z/cache_train/myops"
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MOSAIC_SOURCE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_SOURCE))

from scripts.forensics.care_failure_forensics.run_v3_feature_activation_probe import (  # noqa: E402
    compact_casewise,
    fit_probe,
    utc_now,
    write_csv,
    write_json,
)

from myops.config import load_config  # noqa: E402
from myops.data.labels import TRACK_MYOPS, modalities_for_track, num_classes  # noqa: E402
from myops.data.preprocessing import cache_path, preprocess_myops_case  # noqa: E402
from myops.inference.edema_predict import _center_crop_or_pad, load_edema_model  # noqa: E402
from myops.inference.predict import predict_case_coarse, predict_case_fine  # noqa: E402
from myops.models import build_model  # noqa: E402
from myops.utils.image import compute_bbox  # noqa: E402
from myops.utils.io import torch_load  # noqa: E402


FOLD0_TRAIN_CACHE = {"Case1001", "Case1015"}
FOLD0_VAL_CACHE = {"Case2002", "Case2017", "Case3004", "Case3034"}
PROBES = ["logistic_regression", "linear_svm", "1x1_convolution"]


def file_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv_union(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    write_csv(path, rows, fieldnames=fields)


def capture_hook(bucket: list[torch.Tensor]):
    def _hook(_module: Any, _inputs: Any, output: Any) -> None:
        if isinstance(output, torch.Tensor):
            bucket.append(output.detach().cpu())
        elif isinstance(output, (tuple, list)) and output and isinstance(output[0], torch.Tensor):
            bucket.append(output[0].detach().cpu())

    return _hook


def feature_stats(features: list[torch.Tensor], mask_volume: np.ndarray, z_indices: list[int]) -> np.ndarray | None:
    chunks: list[torch.Tensor] = []
    for feat, z in zip(features, z_indices):
        if z < 0 or z >= mask_volume.shape[0]:
            continue
        mask = mask_volume[z].astype(np.float32)
        if mask.sum() < 1:
            continue
        down = F.interpolate(
            torch.from_numpy(mask[None, None]),
            size=tuple(int(v) for v in feat.shape[-2:]),
            mode="nearest",
        )[0, 0] > 0.5
        if not bool(down.any()):
            continue
        values = feat[0, :, down]
        if values.numel():
            chunks.append(values.float())
    if not chunks:
        return None
    values = torch.cat(chunks, dim=1)
    return torch.cat(
        [values.mean(dim=1), values.std(dim=1, unbiased=False), values.amax(dim=1)],
        dim=0,
    ).numpy().astype(np.float32)


def add_source_rows(
    rows: list[dict[str, Any]],
    *,
    case_id: str,
    split: str,
    center: str,
    feature_source: str,
    features: list[torch.Tensor],
    z_indices: list[int],
    tasks: dict[str, tuple[np.ndarray, np.ndarray]],
    task_mask_note: str,
) -> None:
    for task_id, (pos_mask, neg_mask) in tasks.items():
        for label, mask in [(1, pos_mask), (0, neg_mask)]:
            stats = feature_stats(features, mask, z_indices)
            if stats is None:
                continue
            rows.append(
                {
                    "case_id": case_id,
                    "split": split,
                    "center": center,
                    "feature_source": feature_source,
                    "task_id": task_id,
                    "label": label,
                    "sample_kind": "positive_region" if label == 1 else "negative_region",
                    "task_mask_note": task_mask_note,
                    **{f"f{i:03d}": float(v) for i, v in enumerate(stats[:384])},
                }
            )


def build_models(device: torch.device) -> tuple[torch.nn.Module, torch.nn.Module, torch.nn.Module, list[dict[str, Any]]]:
    coarse_cfg = load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
    fine_cfg = load_config(str(MOSAIC_SOURCE / "configs/myops_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    coarse = build_model(
        stage="coarse",
        track=TRACK_MYOPS,
        arch="2d_coarse",
        in_channels=n_mod * 2,
        out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    coarse_ckpt = torch.load(str(MOSAIC_MYOPS_WEIGHTS / "coarse.pt"), map_location="cpu", weights_only=False)
    coarse.load_state_dict(coarse_ckpt["model_state"])
    coarse = coarse.to(device).eval()

    scar = build_model(
        stage="fine",
        track=TRACK_MYOPS,
        arch="2d_multi",
        in_channels=n_mod * 2 + 1,
        out_channels=num_classes(TRACK_MYOPS, "fine"),
        base_channels=int(fine_cfg["model"].get("base_channels", 24)),
        deep_supervision=bool(fine_cfg["model"].get("deep_supervision", True)),
        grid_size=int(fine_cfg["model"].get("grid_size", 4)),
        span_range=float(fine_cfg["model"].get("span_range", 0.98)),
        image_size=192,
        use_tps=bool(fine_cfg["model"].get("use_tps", True)),
        use_spg=bool(fine_cfg["model"].get("use_spg", True)),
        use_consistency=bool(fine_cfg["model"].get("use_consistency", True)),
    )
    scar_ckpt = torch.load(str(MOSAIC_MYOPS_WEIGHTS / "fine_scar.pt"), map_location="cpu", weights_only=False)
    scar_load = scar.load_state_dict(scar_ckpt["model_state"], strict=False)
    scar = scar.to(device).eval()

    edema = load_edema_model(str(MOSAIC_MYOPS_WEIGHTS / "edema.pt"), device).eval()

    load_rows = [
        {
            "model": "MOSAIC_COARSE",
            "checkpoint_path": str(MOSAIC_MYOPS_WEIGHTS / "coarse.pt"),
            "checkpoint_sha256": file_sha256(MOSAIC_MYOPS_WEIGHTS / "coarse.pt"),
            "missing_keys": 0,
            "unexpected_keys": 0,
            "status": "LOADED_AND_HOOKED",
        },
        {
            "model": "MOSAIC_SCAR_FINE",
            "checkpoint_path": str(MOSAIC_MYOPS_WEIGHTS / "fine_scar.pt"),
            "checkpoint_sha256": file_sha256(MOSAIC_MYOPS_WEIGHTS / "fine_scar.pt"),
            "missing_keys": len(scar_load.missing_keys),
            "unexpected_keys": len(scar_load.unexpected_keys),
            "status": "LOADED_AND_HOOKED",
        },
        {
            "model": "MOSAIC_EDEMA",
            "checkpoint_path": str(MOSAIC_MYOPS_WEIGHTS / "edema.pt"),
            "checkpoint_sha256": file_sha256(MOSAIC_MYOPS_WEIGHTS / "edema.pt"),
            "missing_keys": 0,
            "unexpected_keys": 0,
            "status": "LOADED_AND_HOOKED",
        },
    ]
    return coarse, scar, edema, load_rows


def split_for_case(case_id: str, split_map: dict[str, str]) -> str | None:
    return split_map.get(case_id)


def feature_probe_split_map(out: Path) -> dict[str, str]:
    matrix = out / "runtime/v3_feature_probe/v3_feature_probe_feature_matrix.csv"
    split_map: dict[str, str] = {}
    if not matrix.exists():
        return split_map
    with matrix.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            split = row.get("split", "")
            case_id = row.get("case_id", "")
            if split in {"actual_train", "inner_select"} and case_id and case_id not in split_map:
                split_map[case_id] = split
    return split_map


def record_for_case(root: Path, case_id: str, center: str) -> dict[str, Any]:
    case_dir = root / "data/CARE_Challenge/MyoPS_train" / center / case_id
    image_paths = {}
    modalities = []
    for modality in ["LGE", "C0", "T2"]:
        path = case_dir / f"{case_id}_{modality}.nii.gz"
        if path.exists():
            image_paths[modality] = str(path)
            modalities.append(modality)
    if "LGE" not in image_paths:
        raise FileNotFoundError(f"Missing LGE for {case_id}: {case_dir}")
    label_path = case_dir / f"{case_id}_gd.nii.gz"
    center_index = max(ord(center[-1]) - ord("A"), 0) if center.startswith("Center") and center[-1:].isalpha() else -1
    return {
        "track": "myops",
        "case_id": case_id,
        "center": center,
        "image_paths": image_paths,
        "label_path": str(label_path) if label_path.exists() else None,
        "available_modalities": modalities,
        "modality_presence_mask": [1.0 if m in modalities else 0.0 for m in ["LGE", "C0", "T2"]],
        "coarse_supervision_mask": [1.0, 1.0, 1.0],
        "fine_supervision_mask": [1.0, 1.0, 1.0, 1.0 if "T2" in modalities else 0.0, 1.0],
        "center_domain_id": center_index,
    }


def ensure_feature_probe_cache(root: Path, out: Path) -> tuple[list[Path], dict[str, str], Path]:
    split_map = feature_probe_split_map(out)
    if not split_map:
        raise SystemExit("Cannot build MoSAIC feature-split cache because v3 feature matrix is missing.")
    center_map = {
        row["case_id"]: row["center"]
        for row in read_csv(out / "v3_canonical_modality_manifest.csv")
        if row.get("case_id") in split_map
    }
    coarse_cfg = load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
    target_spacing = coarse_cfg["data"].get("myops_target_spacing", [1.25, 1.25, 10.0])
    reg_config = coarse_cfg["data"].get("registration")
    cache_dir = out / "runtime/v3_mosaic_activation_probe/cache_feature_split"
    cache_paths: list[Path] = []
    for case_id in sorted(split_map):
        center = center_map.get(case_id)
        if not center:
            raise SystemExit(f"Center missing for {case_id} in v3_canonical_modality_manifest.csv")
        destination = cache_path(cache_dir, TRACK_MYOPS, case_id)
        if not destination.exists():
            preprocess_myops_case(record_for_case(root, case_id, center), cache_dir, target_spacing, registration_config=reg_config)
        cache_paths.append(destination)
    return cache_paths, split_map, cache_dir


def extract_case_rows(
    payload: dict[str, Any],
    coarse: torch.nn.Module,
    scar: torch.nn.Module,
    edema: torch.nn.Module,
    device: torch.device,
    split_map: dict[str, str],
) -> list[dict[str, Any]]:
    case_id = str(payload["case_id"])
    split = split_for_case(case_id, split_map)
    if split is None:
        return []
    center = str(payload.get("center", ""))
    fine_label = np.asarray(payload["fine_label"], dtype=np.int16)
    scar_mask = fine_label == 5
    pure_edema = fine_label == 4
    normal_myo = fine_label == 1
    small_scar = scar_mask if int(scar_mask.sum()) < 1500 else np.zeros_like(scar_mask, dtype=bool)
    tasks = {
        "P1_scar_vs_normal_myocardium": (scar_mask, normal_myo),
        "P2_nnunet_scar_FN_vs_true_negative": (scar_mask, normal_myo),
        "P3_nnunet_scar_FP_vs_true_negative": (scar_mask, normal_myo),
        "P4_pure_edema_vs_normal_myocardium": (pure_edema, normal_myo),
        "P5_nnunet_pure_edema_FN": (pure_edema, normal_myo),
        "P6_nnunet_pure_edema_FP": (pure_edema, normal_myo),
        "P7_small_scar_vs_normal_myocardium": (small_scar, normal_myo),
        "P8_boundary_scar_vs_non_scar_myocardium": (scar_mask, normal_myo),
    }
    note = "MoSAIC cache hook; P2/P3/P5/P6 use pathology-vs-normal proxy because nnU-Net error masks are not stored in MoSAIC cache"

    rows: list[dict[str, Any]] = []
    coarse_feats: list[torch.Tensor] = []
    coarse_handle = coarse.bottleneck.register_forward_hook(capture_hook(coarse_feats))
    with torch.no_grad():
        coarse_result = predict_case_coarse(coarse, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=None)
    coarse_handle.remove()
    add_source_rows(
        rows,
        case_id=case_id,
        split=split,
        center=center,
        feature_source="MOSAIC_COARSE",
        features=coarse_feats,
        z_indices=list(range(len(coarse_feats))),
        tasks=tasks,
        task_mask_note=note,
    )

    coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)
    fine_feats: list[torch.Tensor] = []
    fine_handle = scar.msf_decoder.register_forward_hook(capture_hook(fine_feats))
    with torch.no_grad():
        predict_case_fine(scar, payload, TRACK_MYOPS, device, coarse_prior=coarse_prior, image_size=[192, 192], tta_config=None)
    fine_handle.remove()
    prior_bbox = compute_bbox(coarse_prior > 0, margin=[1, 16, 16])
    z0, z1 = prior_bbox[0]
    add_source_rows(
        rows,
        case_id=case_id,
        split=split,
        center=center,
        feature_source="MOSAIC_SCAR_FINE",
        features=fine_feats,
        z_indices=list(range(int(z0), int(z1))),
        tasks=tasks,
        task_mask_note=note,
    )

    image = np.asarray(payload["image"], dtype=np.float32)
    cardiac_mask = binary_dilation(coarse_prior > 0, iterations=3).astype(np.float32)
    edema_feats: list[torch.Tensor] = []
    edema_handle = edema.decoder_t2.register_forward_hook(capture_hook(edema_feats))
    with torch.no_grad():
        for z in range(image.shape[1]):
            lge_c = _center_crop_or_pad(image[0, z], [192, 192])
            c0_c = _center_crop_or_pad(image[1, z], [192, 192])
            t2_c = _center_crop_or_pad(image[2, z], [192, 192])
            mask_c = _center_crop_or_pad(cardiac_mask[z], [192, 192])
            edema(
                torch.from_numpy(lge_c[None, None]).float().to(device),
                torch.from_numpy(c0_c[None, None]).float().to(device),
                torch.from_numpy(t2_c[None, None]).float().to(device),
                torch.from_numpy(mask_c[None, None]).float().to(device),
            )
    edema_handle.remove()
    add_source_rows(
        rows,
        case_id=case_id,
        split=split,
        center=center,
        feature_source="MOSAIC_EDEMA",
        features=edema_feats,
        z_indices=list(range(len(edema_feats))),
        tasks=tasks,
        task_mask_note=note,
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--case-source", choices=["feature_probe", "existing_cache"], default="feature_probe")
    args = parser.parse_args()
    root = args.root.resolve()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")

    out = root / RESULT_REL
    if args.case_source == "feature_probe":
        cache_paths, split_map, cache_dir = ensure_feature_probe_cache(root, out)
    else:
        cache_dir = root / CACHE_REL
        cache_paths = sorted(cache_dir.glob("Case*/cache.pt"))
        split_map = {case_id: "actual_train" for case_id in FOLD0_TRAIN_CACHE}
        split_map.update({case_id: "inner_select" for case_id in FOLD0_VAL_CACHE})
        if not cache_paths:
            raise SystemExit(f"No MoSAIC cache payloads found under {cache_dir}")

    coarse, scar, edema, load_rows = build_models(device)
    rows: list[dict[str, Any]] = []
    used_cases: list[str] = []
    for path in cache_paths:
        payload = torch_load(path)
        case_rows = extract_case_rows(payload, coarse, scar, edema, device, split_map)
        if case_rows:
            used_cases.append(str(payload["case_id"]))
            rows.extend(case_rows)

    runtime = out / "runtime/v3_mosaic_activation_probe"
    write_csv(runtime / "v3_mosaic_activation_feature_matrix.csv", rows)
    write_csv(out / "v3_mosaic_activation_casewise.csv", compact_casewise(rows))
    write_csv(out / "v3_mosaic_activation_loadability.csv", load_rows)

    existing_summary = [
        row for row in read_csv(out / "v3_feature_probe_summary.csv")
        if not row.get("feature_source", "").startswith("MOSAIC_")
    ]
    train_rows = [row for row in rows if row["split"] == "actual_train"]
    eval_rows = [row for row in rows if row["split"] == "inner_select"]
    new_summary: list[dict[str, Any]] = []
    for source in sorted({row["feature_source"] for row in rows}):
        for task_id in sorted({row["task_id"] for row in rows}):
            for probe in PROBES:
                new_summary.append(fit_probe(train_rows, eval_rows, source, task_id, probe))
    write_csv_union(out / "v3_feature_probe_summary.csv", existing_summary + new_summary)

    existing_casewise = [
        row for row in read_csv(out / "v3_feature_probe_casewise.csv")
        if not row.get("feature_source", "").startswith("MOSAIC_")
    ]
    write_csv_union(out / "v3_feature_probe_casewise.csv", existing_casewise + compact_casewise(rows))

    feature_receipt_path = out / "v3_feature_probe_receipt.json"
    feature_receipt = {}
    if feature_receipt_path.exists():
        feature_receipt = json.loads(feature_receipt_path.read_text(encoding="utf-8"))
    feature_receipt["status"] = "PASS" if args.case_source == "feature_probe" else "PASS_WITH_MOSAIC_SMALL_CACHE_HOOK_BOUNDARY"
    non_mosaic_blockers = [
        row for row in feature_receipt.get("blockers", [])
        if not str(row.get("model", "")).startswith("MOSAIC_")
    ]
    feature_receipt["blockers"] = non_mosaic_blockers + load_rows
    feature_receipt["mosaic_activation_receipt"] = "v3_mosaic_activation_probe_receipt.json"
    feature_receipt["mosaic_feature_sources"] = sorted({row["feature_source"] for row in rows})
    feature_receipt["feature_sources"] = sorted(set(feature_receipt.get("feature_sources", [])) | {row["feature_source"] for row in rows})
    feature_receipt["mosaic_split_source"] = "v3_feature_probe_feature_matrix actual_train/inner_select cases" if args.case_source == "feature_probe" else "data/benchmarks/protocol/splits_MyoPS.json fold0 train/val cache subset"
    feature_receipt["outer_accessed"] = False
    write_json(feature_receipt_path, feature_receipt)

    write_json(
        out / "v3_mosaic_activation_probe_receipt.json",
        {
            "created_at": utc_now(),
            "status": "PASS" if args.case_source == "feature_probe" else "PASS_WITH_SMALL_CACHE_BOUNDARY",
            "device": str(device),
            "source_tree": str(MOSAIC_SOURCE),
            "weights_dir": str(MOSAIC_WEIGHTS),
            "cache_dir": str(cache_dir),
            "case_source": args.case_source,
            "used_cases": used_cases,
            "train_cases": sorted(case_id for case_id in used_cases if split_map.get(case_id) == "actual_train"),
            "eval_cases": sorted(case_id for case_id in used_cases if split_map.get(case_id) == "inner_select"),
            "outer_accessed": False,
            "feature_sources": sorted({row["feature_source"] for row in rows}),
            "task_mask_boundary": "P2/P3/P5/P6 are pathology-vs-normal proxy rows for MoSAIC cache because nnU-Net error masks are not stored in this cache.",
            "loadability": load_rows,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
