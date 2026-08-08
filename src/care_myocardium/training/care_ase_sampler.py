"""Deterministic CARE-ASE R2 sampler and actual-train area references."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
import pickle
import random
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
from scipy import ndimage

from src.care_myocardium.data.care_ase_splits import PREPROCESSED_REL, build_care_ase_case_roles, sha256_file
from src.care_myocardium.data.case_metadata import load_myops_case_metadata


CURRENT_TASK_ID = "care-ase-faithful"
HARD_NEGATIVE_MANIFEST_ENV = "CARE_ASE_HARD_NEGATIVE_MANIFEST"


@dataclass(frozen=True)
class CAREASEBatchDescriptor:
    fold: int
    global_step: int
    stage_id: str
    case_id: str
    case_group: str
    center_group: str
    center: str
    pathology_focus: str
    within_focus: str
    availability: tuple[float, float, float]
    hard_negative_category: str
    hard_negative_counts: dict[str, int]
    resolved_target_coordinates: tuple[tuple[int, int, int], ...]
    fallback_sequence: tuple[str, ...]
    selected_target_coordinate: tuple[int, int, int] | None = None
    coordinate_selection_source: str = "micro_patch_rng"
    requested_category: str = ""
    resolved_category: str = ""
    fallback_reason: str | None = None
    eligible_case_count: int = 0
    candidate_coordinate_count: int = 0
    manifest_sha256: str = ""
    augmentation_seed: int = 0

    def sha256(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CAREASEMicrobatchBundle:
    fold: int
    global_step: int
    stage_id: str
    optimizer_step_stratum: dict[str, str]
    micro_descriptors: tuple[CAREASEBatchDescriptor, ...]

    def sha256(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def stage_for_step(global_step: int) -> str:
    step = int(global_step)
    if step < 2000:
        return "A"
    if step < 10000:
        return "B"
    if step < 14000:
        return "C"
    return "complete"


def _case_group_from_availability(availability: tuple[float, float, float]) -> str:
    lge, t2, c0 = tuple(float(v) > 0.5 for v in availability)
    if lge and t2 and c0:
        return "complete"
    if lge and c0 and not t2:
        return "lge_c0"
    if lge and not c0 and not t2:
        return "lge_only"
    return "other"


def _load_hard_negative_manifest(repo_root: Path, fold: int, manifest_path: Path | None = None) -> dict[str, Any]:
    if manifest_path is None:
        env_path = os.environ.get(HARD_NEGATIVE_MANIFEST_ENV)
        if not env_path:
            raise FileNotFoundError(
                "CARE-ASE hard-negative manifest must be supplied explicitly by the current runtime input bundle "
                f"or {HARD_NEGATIVE_MANIFEST_ENV}"
            )
        path = Path(env_path)
        if not path.is_absolute():
            path = repo_root / path
    else:
        path = Path(manifest_path)
        if not path.is_absolute():
            path = repo_root / path
    if not path.is_file():
        raise FileNotFoundError(f"canonical CARE-ASE R2 hard-negative JSON manifest is required: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"hard-negative manifest is not a JSON object: {path}")
    if data.get("source") != "canonical_patient_held_out_stock_nnunet_oof_only":
        raise ValueError(f"hard-negative manifest source is not canonical stock OOF only: {data.get('source')}")
    if data.get("v9_manifest") is not True:
        raise ValueError("hard-negative manifest must declare v9_manifest=true")
    if data.get("task_id") not in (None, CURRENT_TASK_ID):
        raise ValueError(f"hard-negative manifest task_id is not current CARE-ASE task: {data.get('task_id')}")
    if data.get("forbidden_old_manifest_paths_rejected") is not True:
        raise ValueError("hard-negative manifest must prove old manifest paths are rejected")
    cases = data.setdefault("cases", {})
    required_case_fields = {
        "case_id",
        "source_stock_fold",
        "source_checkpoint_type",
        "source_checkpoint_path",
        "source_checkpoint_sha256",
        "source_prediction_path",
        "source_prediction_sha256",
        "preprocessed_prediction_array_sha256",
        "proof_case_not_in_source_fold_train",
        "preprocessed_shape",
        "preprocessed_spacing",
        "preprocessed_geometry_sha256",
        "binding_method",
        "targets",
        "target_coordinate_counts",
        "target_masks_counts",
        "sampled_coordinates",
        "coordinate_semantic_validation",
    }
    for case_id, row in (cases.items() if isinstance(cases, dict) else ()):
        missing = sorted(required_case_fields - set(row)) if isinstance(row, dict) else sorted(required_case_fields)
        if missing:
            raise ValueError(f"hard-negative manifest case {case_id} missing v6 fields: {missing}")
        if row.get("proof_case_not_in_source_fold_train") is not True:
            raise ValueError(f"hard-negative manifest case {case_id} lacks patient-held-out source proof")
        if row.get("binding_method") != "exact_preprocessed_grid_with_manifest_geometry_proof":
            raise ValueError(f"hard-negative manifest case {case_id} has illegal binding_method={row.get('binding_method')}")
        validation = row.get("coordinate_semantic_validation", {})
        if not isinstance(validation, dict) or validation.get("coordinate_bounds_valid") is not True:
            raise ValueError(f"hard-negative manifest case {case_id} failed coordinate bounds validation")
        nonempty = validation.get("nonempty_required_when_voxel_count_positive", {})
        if isinstance(nonempty, dict) and not all(bool(v) for v in nonempty.values()):
            raise ValueError(f"hard-negative manifest case {case_id} has empty OOF coordinate claims")
    data["manifest_path"] = str(path)
    data["manifest_sha256"] = sha256_file(path)
    if int(data.get("fold", fold)) != int(fold):
        raise ValueError(f"hard-negative manifest fold mismatch: expected {fold}, got {data.get('fold')}")
    return data


def _encode_rng_state(rng: random.Random) -> str:
    return pickle.dumps(rng.getstate(), protocol=4).hex()


def _decode_rng_state(encoded: str) -> object:
    return pickle.loads(bytes.fromhex(str(encoded)))


def _coords(value: dict[str, Any], key: str) -> tuple[tuple[int, int, int], ...]:
    raw = value.get("targets", {}).get(key, []) if isinstance(value.get("targets", {}), dict) else []
    out = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            out.append((int(item[0]), int(item[1]), int(item[2])))
    return tuple(out)


def _case_spacing_from_manifest(manifest_case: dict[str, Any]) -> tuple[float, float, float]:
    raw = manifest_case.get("preprocessed_spacing", (1.0, 1.0, 1.0)) if isinstance(manifest_case, dict) else (1.0, 1.0, 1.0)
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        return tuple(float(v) for v in raw)
    return (1.0, 1.0, 1.0)


def _hard_negative_category(manifest: dict[str, Any], case_id: str, pathology_focus: str, within_focus: str) -> tuple[str, dict[str, int], tuple[tuple[int, int, int], ...]]:
    cases = manifest.get("cases", {})
    value = cases.get(case_id, {}) if isinstance(cases, dict) else {}
    if isinstance(value, dict):
        counts = {
            "scar_fp_voxels": int(value.get("scar_fp_voxels", 0) or 0),
            "scar_fn_voxels": int(value.get("scar_fn_voxels", 0) or 0),
            "edema_fp_voxels": int(value.get("edema_fp_voxels", 0) or 0),
            "edema_fn_voxels": int(value.get("edema_fn_voxels", 0) or 0),
        }
        if pathology_focus == "scar" and within_focus == "small_component":
            coords = _coords(value, "scar_small_component")
            if coords:
                return "scar_small_component", counts, coords
        if pathology_focus == "scar" and within_focus == "oof_fn" and counts["scar_fn_voxels"] > 0:
            coords = _coords(value, "scar_oof_fn")
            if not coords:
                raise RuntimeError(f"manifest claims scar FN for {case_id} but provides no scar_oof_fn coordinates")
            return "scar_oof_fn", counts, coords
        if pathology_focus == "scar" and within_focus == "oof_fp" and counts["scar_fp_voxels"] > 0:
            coords = _coords(value, "scar_oof_fp")
            if not coords:
                raise RuntimeError(f"manifest claims scar FP for {case_id} but provides no scar_oof_fp coordinates")
            return "scar_oof_fp", counts, coords
        if pathology_focus == "edema" and within_focus == "oof_fn_or_low_volume" and counts["edema_fn_voxels"] > 0:
            coords = _coords(value, "edema_oof_fn_or_low_volume")
            if not coords:
                raise RuntimeError(f"manifest claims edema FN/low-volume for {case_id} but provides no edema_oof_fn_or_low_volume coordinates")
            return "edema_oof_fn_or_low_volume", counts, coords
        if pathology_focus == "edema" and within_focus == "safe_fp" and counts["edema_fp_voxels"] > 0:
            coords = _coords(value, "edema_safe_fp")
            if not coords:
                raise RuntimeError(f"manifest claims edema safe FP for {case_id} but provides no edema_safe_fp coordinates")
            return "edema_safe_fp", counts, coords
        return "manifest_consumed_no_matching_oof", counts, ()
    return "manifest_missing_case", {"scar_fp_voxels": 0, "scar_fn_voxels": 0, "edema_fp_voxels": 0, "edema_fn_voxels": 0}, ()


def _fallback_sequence(pathology_focus: str, within_focus: str, hard_category: str) -> tuple[str, ...]:
    if pathology_focus == "scar":
        mapping = {
            "small_component": ("small_component", "gt_component", "random_wall"),
            "oof_fn": ("oof_fn", "gt_component", "random_wall"),
            "oof_fp": ("oof_fp", "remote_background", "blood_pool_adjacent", "random_background"),
            "gt_component": ("gt_component", "random_wall", "background"),
            "random": ("random_wall", "background"),
        }
    else:
        mapping = {
            "oof_fn_or_low_volume": ("oof_fn_or_low_volume", "positive", "boundary"),
            "safe_fp": ("safe_fp", "boundary", "positive"),
            "positive": ("positive", "boundary", "random_wall"),
            "boundary": ("boundary", "positive", "random_wall"),
            "random": ("random_wall", "positive"),
        }
    first = mapping.get(within_focus, (within_focus,))
    if hard_category.startswith(("scar_oof", "edema_oof", "edema_safe")):
        return (hard_category, *tuple(item for item in first if item != hard_category))
    return first


class CAREASEDeterministicSampler:
    """R2 exact batch descriptor generator.

    The sampler returns descriptors. The training entrypoint materializes image
    crops from these descriptors. This keeps cursor/hash behavior testable
    without touching outer labels.
    """

    stage_a_b_cycle = (
        "complete",
        "lge_only",
        "complete",
        "lge_c0",
        "complete",
        "lge_only",
        "complete",
        "lge_c0",
        "complete",
        "lge_only",
        "complete",
        "lge_c0",
        "complete",
        "lge_only",
        "complete",
        "lge_c0",
        "complete",
        "lge_only",
        "complete",
        "lge_c0",
    )
    stage_c_cycle = ("complete_centerB", "complete_centerC")
    pathology_cycle = ("scar", "edema")
    scar_within_focus_cycle = (
        "gt_component",
        "gt_component",
        "gt_component",
        "gt_component",
        "gt_component",
        "gt_component",
        "gt_component",
        "small_component",
        "small_component",
        "small_component",
        "small_component",
        "oof_fn",
        "oof_fn",
        "oof_fn",
        "oof_fn",
        "oof_fp",
        "oof_fp",
        "oof_fp",
        "random",
        "random",
    )
    edema_within_focus_cycle = (
        "positive",
        "positive",
        "positive",
        "positive",
        "positive",
        "positive",
        "positive",
        "oof_fn_or_low_volume",
        "oof_fn_or_low_volume",
        "oof_fn_or_low_volume",
        "oof_fn_or_low_volume",
        "boundary",
        "boundary",
        "boundary",
        "boundary",
        "safe_fp",
        "safe_fp",
        "safe_fp",
        "random",
        "random",
    )

    def __init__(self, repo_root: Path, fold: int, *, seed: int = 20260803, hard_negative_manifest_path: Path | None = None) -> None:
        self.repo_root = repo_root.resolve()
        self.fold = int(fold)
        self.seed = int(seed)
        self._hard_negative_manifest_path_arg = hard_negative_manifest_path
        self.rng = random.Random(f"{seed}|fold={fold}")
        self.micro_case_rng_by_group = {
            group: random.Random(f"{seed}|fold={fold}|micro_case|{group}")
            for group in ("complete_centerB", "complete_centerC", "lge_only", "lge_c0")
        }
        self.micro_patch_rng = random.Random(f"{seed}|fold={fold}|micro_patch")
        metadata = load_myops_case_metadata(self.repo_root)
        rows = [row for row in build_care_ase_case_roles(self.repo_root, self.fold) if row.role == "actual-train"]
        self.by_group: dict[str, list[str]] = {"complete": [], "lge_only": [], "lge_c0": [], "complete_centerB": [], "complete_centerC": []}
        self.case_meta: dict[str, tuple[str, tuple[float, float, float]]] = {}
        for row in rows:
            meta = metadata[row.case_id]
            availability = tuple(float(v) for v in meta.availability)
            group = _case_group_from_availability(availability)
            if group in self.by_group:
                self.by_group[group].append(row.case_id)
            if group == "complete" and row.center in {"CenterB", "CenterC"}:
                center_group = {"CenterB": "complete_centerB", "CenterC": "complete_centerC"}[row.center]
                self.by_group[center_group].append(row.case_id)
            self.case_meta[row.case_id] = (row.center, availability)
        for key, values in self.by_group.items():
            if values:
                self.by_group[key] = sorted(values)
        if hard_negative_manifest_path is None:
            self.hard_negative_manifest = _load_hard_negative_manifest(self.repo_root, self.fold)
        else:
            self.hard_negative_manifest = _load_hard_negative_manifest(self.repo_root, self.fold, hard_negative_manifest_path)
        self.hard_negative_manifest_path = self.hard_negative_manifest.get("manifest_path")
        self._coordinate_cache: dict[tuple[str, str, str], tuple[tuple[int, int, int], ...]] = {}
        self.case_group_cursor = 0
        self.complete_center_selector_cursor = 0
        self.complete_centerB_case_cursor = 0
        self.complete_centerC_case_cursor = 0
        self.complete_center_cursor = 0
        self.complete_pathology_cursor = 0
        self.partial_case_cursors = {"lge_only": 0, "lge_c0": 0}
        self.micro_case_cursors_by_group = {"complete_centerB": 0, "complete_centerC": 0, "lge_only": 0, "lge_c0": 0}
        self.micro_patch_cursor = 0
        self.scar_focus_cursor = 0
        self.edema_focus_cursor = 0
        self.batch_descriptor_cursor = 0

    def _choose_case(self, group: str, cursor: int) -> str:
        values = self.by_group.get(group, [])
        if not values:
            raise RuntimeError(f"CARE-ASE R2 sampler has no actual-train cases for group={group} fold={self.fold}")
        return values[cursor % len(values)]

    def _case_for_micro(self, group: str) -> str:
        values = self.by_group.get(group, [])
        if not values:
            raise RuntimeError(f"CARE-ASE R2 sampler has no actual-train cases for group={group} fold={self.fold}")
        rng = self.micro_case_rng_by_group.setdefault(group, random.Random(f"{self.seed}|fold={self.fold}|micro_case|{group}"))
        case_id = values[rng.randrange(len(values))]
        self.micro_case_cursors_by_group[group] = self.micro_case_cursors_by_group.get(group, 0) + 1
        return case_id

    def _case_seg(self, case_id: str) -> np.ndarray:
        path = self.repo_root / PREPROCESSED_REL / f"{case_id}_seg.b2nd"
        return np.asarray(blosc2.open(str(path), mode="r")[:])[0].astype(np.int16, copy=False)

    def _candidate_coordinates(self, case_id: str, pathology: str, category: str) -> tuple[tuple[int, int, int], ...]:
        cache_key = (str(case_id), str(pathology), str(category))
        if cache_key in self._coordinate_cache:
            return self._coordinate_cache[cache_key]
        manifest_case = self.hard_negative_manifest.get("cases", {}).get(case_id, {})
        manifest_key = {
            "oof_fn": "scar_oof_fn" if pathology == "scar" else "edema_oof_fn_or_low_volume",
            "oof_fp": "scar_oof_fp",
            "oof_fn_or_low_volume": "edema_oof_fn_or_low_volume",
            "safe_fp": "edema_safe_fp",
            "small_component": "scar_small_component",
        }.get(category)
        if manifest_key:
            coords = _coords(manifest_case, manifest_key) if isinstance(manifest_case, dict) else ()
            self._coordinate_cache[cache_key] = coords
            return coords
        seg = self._case_seg(case_id)
        spacing = _case_spacing_from_manifest(manifest_case if isinstance(manifest_case, dict) else {})
        wall = (seg == 1) | (seg == 4) | (seg == 5)
        scar = seg == 5
        edema = seg == 4
        pathology_mask = scar | edema
        blood = (seg == 2) | (seg == 3)
        lesion = scar if pathology == "scar" else edema
        mask = np.zeros(seg.shape, dtype=bool)
        if category in {"gt_component", "positive"}:
            mask = lesion
        elif category == "small_component" and pathology == "scar":
            labels, count = ndimage.label(scar, structure=np.ones((3, 3, 3), dtype=np.uint8))
            small = np.zeros(seg.shape, dtype=bool)
            for comp_id in range(1, int(count) + 1):
                comp = labels == comp_id
                if float(comp.sum() * np.prod(spacing)) < 1000.0:
                    small |= comp
            mask = small
        elif category in {"boundary"} and pathology == "edema":
            if edema.any() and not edema.all():
                dist_inside = ndimage.distance_transform_edt(edema, sampling=spacing)
                dist_outside = ndimage.distance_transform_edt(~edema, sampling=spacing)
                raw = dist_inside - dist_outside
                mask = (np.abs(raw) <= 10.0) | edema
            else:
                mask = np.zeros(seg.shape, dtype=bool)
        elif category in {"random_wall", "random"}:
            mask = wall
        elif category in {"random_background", "background"}:
            mask = seg == 0
        elif category == "remote_background":
            dist_to_wall = ndimage.distance_transform_edt(~wall, sampling=spacing)
            mask = (~pathology_mask) & (seg == 0) & (dist_to_wall > 10.0)
        elif category == "blood_pool_adjacent":
            dist_to_blood = ndimage.distance_transform_edt(~blood, sampling=spacing)
            mask = (~pathology_mask) & (~blood) & (dist_to_blood <= 3.0)
        coords_np = np.argwhere(mask)
        if coords_np.shape[0] > 4096:
            stride = max(1, coords_np.shape[0] // 4096)
            coords_np = coords_np[::stride][:4096]
        coords = tuple((int(z), int(y), int(x)) for z, y, x in coords_np)
        self._coordinate_cache[cache_key] = coords
        return coords

    def _eligible_cases_for_category(self, group: str, pathology: str, category: str) -> list[str]:
        values = list(self.by_group.get(group, []))
        return sorted(case_id for case_id in values if self._candidate_coordinates(case_id, pathology, category))

    def _resolve_category_and_pool(self, group: str, pathology: str, within_focus: str, hard_category: str) -> tuple[str, list[str], str | None]:
        values = list(self.by_group.get(group, []))
        if not values:
            return within_focus, [], "empty_group"
        for category in _fallback_sequence(pathology, within_focus, hard_category):
            eligible = self._eligible_cases_for_category(group, pathology, category)
            if eligible:
                reason = None if category == within_focus or category == hard_category else f"eligible_pool_empty_for_{pathology}_{within_focus}_resolved_to_{category}"
                return category, eligible, reason
        return within_focus, [], f"eligible_pool_empty_for_{pathology}_{within_focus}"

    def _case_for_micro_from_pool(self, group: str, pool: list[str]) -> str:
        if not pool:
            raise RuntimeError(f"CARE-ASE R2 sampler has no eligible cases for group={group} fold={self.fold}")
        rng = self.micro_case_rng_by_group.setdefault(group, random.Random(f"{self.seed}|fold={self.fold}|micro_case|{group}"))
        case_id = pool[rng.randrange(len(pool))]
        self.micro_case_cursors_by_group[group] = self.micro_case_cursors_by_group.get(group, 0) + 1
        return case_id

    def descriptor_bundle_for_step(self, global_step: int, *, microbatch_count: int = 4) -> CAREASEMicrobatchBundle:
        stage = stage_for_step(global_step)
        if stage in {"A", "B"}:
            group = self.stage_a_b_cycle[self.case_group_cursor % len(self.stage_a_b_cycle)]
            self.case_group_cursor += 1
            if group == "complete":
                center_group = self.stage_c_cycle[self.complete_center_selector_cursor % len(self.stage_c_cycle)]
                self.complete_center_selector_cursor += 1
                if center_group == "complete_centerB":
                    self.complete_centerB_case_cursor += 1
                else:
                    self.complete_centerC_case_cursor += 1
                self.complete_center_cursor = self.complete_center_selector_cursor
            else:
                center_group = group
                self.partial_case_cursors[group] = self.partial_case_cursors[group] + 1
        elif stage == "C":
            center_group = self.stage_c_cycle[self.complete_center_selector_cursor % len(self.stage_c_cycle)]
            group = "complete"
            self.complete_center_selector_cursor += 1
            if center_group == "complete_centerB":
                self.complete_centerB_case_cursor += 1
            else:
                self.complete_centerC_case_cursor += 1
            self.complete_center_cursor = self.complete_center_selector_cursor
        else:
            raise ValueError(f"global_step outside formal training range: {global_step}")
        if group in {"lge_only", "lge_c0"}:
            pathology = "scar"
        else:
            pathology = self.pathology_cycle[self.complete_pathology_cursor % len(self.pathology_cycle)]
            self.complete_pathology_cursor += 1
        if pathology == "scar":
            within_focus = self.scar_within_focus_cycle[self.scar_focus_cursor % len(self.scar_within_focus_cycle)]
            self.scar_focus_cursor += 1
        else:
            within_focus = self.edema_within_focus_cycle[self.edema_focus_cursor % len(self.edema_within_focus_cycle)]
            self.edema_focus_cursor += 1
        self.batch_descriptor_cursor += 1
        requested_hard_category = _fallback_sequence(pathology, within_focus, within_focus)[0]
        resolved_category, eligible_cases, fallback_reason = self._resolve_category_and_pool(center_group, pathology, within_focus, requested_hard_category)
        descriptors = []
        for _micro in range(int(microbatch_count)):
            case_id = self._case_for_micro_from_pool(center_group, eligible_cases)
            center, availability = self.case_meta[case_id]
            hard_category, hard_counts, hard_coords = _hard_negative_category(self.hard_negative_manifest, case_id, pathology, resolved_category)
            if hard_coords:
                candidate_coords = tuple(tuple(int(v) for v in coord) for coord in hard_coords)
                descriptor_resolved_category = hard_category
                coordinate_source = "micro_patch_rng_manifest_coordinate"
                descriptor_fallback_reason = "manifest_coordinate_consumed"
            else:
                candidate_coords = self._candidate_coordinates(case_id, pathology, resolved_category)
                descriptor_resolved_category = resolved_category
                coordinate_source = "micro_patch_rng_resolved_category_coordinate"
                descriptor_fallback_reason = fallback_reason
            if not candidate_coords:
                raise RuntimeError(f"resolved sampler category has no coordinates: case={case_id} category={resolved_category}")
            if hard_category in {"manifest_consumed_no_matching_oof", "manifest_missing_case"}:
                hard_category = descriptor_resolved_category
            selected_coord = candidate_coords[self.micro_patch_rng.randrange(len(candidate_coords))]
            augmentation_seed = self.micro_patch_rng.randrange(2**32)
            descriptors.append(
                CAREASEBatchDescriptor(
                    fold=self.fold,
                    global_step=int(global_step),
                    stage_id=stage,
                    case_id=case_id,
                    case_group=group,
                    center_group=center_group,
                    center=center,
                    pathology_focus=pathology,
                    within_focus=within_focus,
                    availability=availability,
                    hard_negative_category=hard_category,
                    hard_negative_counts=hard_counts,
                    resolved_target_coordinates=candidate_coords,
                    fallback_sequence=_fallback_sequence(pathology, within_focus, descriptor_resolved_category),
                    selected_target_coordinate=selected_coord,
                    coordinate_selection_source=coordinate_source,
                    requested_category=within_focus,
                    resolved_category=descriptor_resolved_category,
                    fallback_reason=descriptor_fallback_reason,
                    eligible_case_count=len(eligible_cases),
                    candidate_coordinate_count=len(candidate_coords),
                    manifest_sha256=str(self.hard_negative_manifest.get("manifest_sha256", "")),
                    augmentation_seed=int(augmentation_seed),
                )
            )
            self.micro_patch_cursor += 1
        return CAREASEMicrobatchBundle(
            fold=self.fold,
            global_step=int(global_step),
            stage_id=stage,
            optimizer_step_stratum={
                "case_group": group,
                "center_group": center_group,
                "pathology_focus": pathology,
                "within_focus": within_focus,
            },
            micro_descriptors=tuple(descriptors),
        )

    def descriptor_for_step(self, global_step: int) -> CAREASEBatchDescriptor:
        raise RuntimeError("descriptor_for_step is not a formal CARE-ASE R2 API; use descriptor_bundle_for_step so four microbatches are explicit")

    def peek_descriptor_for_step(self, global_step: int) -> CAREASEBatchDescriptor:
        return self.peek_descriptor_bundle_for_step(global_step).micro_descriptors[0]

    def peek_descriptor_bundle_for_step(self, global_step: int) -> CAREASEMicrobatchBundle:
        clone = CAREASEDeterministicSampler(self.repo_root, self.fold, seed=self.seed, hard_negative_manifest_path=self._hard_negative_manifest_path_arg)
        clone.load_state_dict(self.state_dict())
        return clone.descriptor_bundle_for_step(global_step)

    def state_dict(self, *, next_descriptor: CAREASEBatchDescriptor | None = None) -> dict[str, Any]:
        state = {
            "case_group_cursor": self.case_group_cursor,
            "complete_center_selector_cursor": self.complete_center_selector_cursor,
            "complete_centerB_case_cursor": self.complete_centerB_case_cursor,
            "complete_centerC_case_cursor": self.complete_centerC_case_cursor,
            "complete_center_cursor": self.complete_center_cursor,
            "complete_pathology_cursor": self.complete_pathology_cursor,
            "partial_case_cursors": dict(self.partial_case_cursors),
            "micro_case_cursors_by_group": dict(self.micro_case_cursors_by_group),
            "micro_case_rng_state_by_group": {group: _encode_rng_state(rng) for group, rng in sorted(self.micro_case_rng_by_group.items())},
            "micro_patch_cursor": int(self.micro_patch_cursor),
            "micro_patch_rng_state": _encode_rng_state(self.micro_patch_rng),
            "center_cursor": self.complete_center_cursor,
            "pathology_focus_cursor": self.complete_pathology_cursor,
            "scar_focus_cursor": self.scar_focus_cursor,
            "edema_focus_cursor": self.edema_focus_cursor,
            "sampler_rng_state": _encode_rng_state(self.rng),
            "batch_descriptor_cursor": self.batch_descriptor_cursor,
            "hard_negative_manifest_path": self.hard_negative_manifest.get("manifest_path"),
            "hard_negative_manifest_sha256": self.hard_negative_manifest.get("manifest_sha256"),
            "hard_negative_manifest_case_count": len(self.hard_negative_manifest.get("cases", {})),
        }
        if next_descriptor is not None:
            state["next_batch_descriptor_sha256"] = next_descriptor.sha256()
            if isinstance(next_descriptor, CAREASEMicrobatchBundle):
                state["next_optimizer_step_micro_descriptor_bundle"] = [asdict(item) for item in next_descriptor.micro_descriptors]
                state["next_optimizer_step_micro_descriptor_sha256"] = next_descriptor.sha256()
        return state

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.case_group_cursor = int(state["case_group_cursor"])
        legacy_center = int(state.get("complete_center_cursor", state.get("center_cursor", 0)))
        self.complete_center_selector_cursor = int(state.get("complete_center_selector_cursor", legacy_center))
        self.complete_centerB_case_cursor = int(state.get("complete_centerB_case_cursor", (self.complete_center_selector_cursor + 1) // 2))
        self.complete_centerC_case_cursor = int(state.get("complete_centerC_case_cursor", self.complete_center_selector_cursor // 2))
        self.complete_center_cursor = self.complete_center_selector_cursor
        self.complete_pathology_cursor = int(state.get("complete_pathology_cursor", state.get("pathology_focus_cursor", 0)))
        self.partial_case_cursors = {str(k): int(v) for k, v in state.get("partial_case_cursors", {"lge_only": 0, "lge_c0": 0}).items()}
        self.partial_case_cursors.setdefault("lge_only", 0)
        self.partial_case_cursors.setdefault("lge_c0", 0)
        self.micro_case_cursors_by_group = {str(k): int(v) for k, v in state.get("micro_case_cursors_by_group", {}).items()}
        for key in ("complete_centerB", "complete_centerC", "lge_only", "lge_c0"):
            self.micro_case_cursors_by_group.setdefault(key, 0)
        rng_states = state.get("micro_case_rng_state_by_group", {})
        if isinstance(rng_states, dict):
            for key, encoded in rng_states.items():
                rng = self.micro_case_rng_by_group.setdefault(str(key), random.Random(f"{self.seed}|fold={self.fold}|micro_case|{key}"))
                if isinstance(encoded, str) and encoded:
                    rng.setstate(_decode_rng_state(encoded))
        self.micro_patch_cursor = int(state.get("micro_patch_cursor", 0))
        micro_patch_rng_state = state.get("micro_patch_rng_state")
        if isinstance(micro_patch_rng_state, str) and micro_patch_rng_state:
            self.micro_patch_rng.setstate(_decode_rng_state(micro_patch_rng_state))
        self.scar_focus_cursor = int(state["scar_focus_cursor"])
        self.edema_focus_cursor = int(state["edema_focus_cursor"])
        self.batch_descriptor_cursor = int(state["batch_descriptor_cursor"])
        rng_state = state.get("sampler_rng_state")
        if isinstance(rng_state, str) and rng_state and rng_state != "UNSET":
            self.rng.setstate(_decode_rng_state(rng_state))

    def dry_run_counts(self, steps: int, *, start_step: int = 0) -> dict[str, int]:
        clone = CAREASEDeterministicSampler(self.repo_root, self.fold, seed=self.seed, hard_negative_manifest_path=self._hard_negative_manifest_path_arg)
        clone.load_state_dict(self.state_dict())
        counts: dict[str, int] = {}
        for step in range(int(start_step), int(start_step) + int(steps)):
            desc = clone.descriptor_bundle_for_step(step).micro_descriptors[0]
            counts[desc.case_group] = counts.get(desc.case_group, 0) + 1
        return counts

    def composition_receipt(self, steps: int, *, start_step: int = 0) -> dict[str, Any]:
        clone = CAREASEDeterministicSampler(self.repo_root, self.fold, seed=self.seed, hard_negative_manifest_path=self._hard_negative_manifest_path_arg)
        clone.load_state_dict(self.state_dict())
        counts = {
            "complete": 0,
            "lge_only": 0,
            "lge_c0": 0,
            "complete_centerB": 0,
            "complete_centerC": 0,
            "complete_scar": 0,
            "complete_edema": 0,
            "partial_scar": 0,
            "partial_edema": 0,
            "scar_focus": {},
            "edema_focus": {},
        }
        descriptor_hashes: list[str] = []
        all_four_same = 0
        distinct_distribution: dict[str, int] = {}
        micro_counts = {
            "complete": 0,
            "lge_only": 0,
            "lge_c0": 0,
            "complete_centerB": 0,
            "complete_centerC": 0,
            "complete_scar": 0,
            "complete_edema": 0,
            "partial_scar": 0,
            "partial_edema": 0,
        }
        for step in range(int(start_step), int(start_step) + int(steps)):
            bundle = clone.descriptor_bundle_for_step(step)
            desc = bundle.micro_descriptors[0]
            descriptor_hashes.append(bundle.sha256())
            micro_case_ids = [item.case_id for item in bundle.micro_descriptors]
            if len(set(micro_case_ids)) == 1:
                all_four_same += 1
            distinct_count = len(set(micro_case_ids))
            distinct_distribution[str(distinct_count)] = distinct_distribution.get(str(distinct_count), 0) + 1
            counts[desc.case_group] = int(counts.get(desc.case_group, 0)) + 1
            if desc.case_group == "complete":
                center_key = {"CenterB": "complete_centerB", "CenterC": "complete_centerC"}.get(desc.center, f"complete_{desc.center}")
                counts[center_key] = int(counts.get(center_key, 0)) + 1
                counts[f"complete_{desc.pathology_focus}"] = int(counts.get(f"complete_{desc.pathology_focus}", 0)) + 1
            else:
                counts[f"partial_{desc.pathology_focus}"] = int(counts.get(f"partial_{desc.pathology_focus}", 0)) + 1
            focus_key = "scar_focus" if desc.pathology_focus == "scar" else "edema_focus"
            focus_counts = counts[focus_key]
            assert isinstance(focus_counts, dict)
            focus_counts[desc.within_focus] = int(focus_counts.get(desc.within_focus, 0)) + 1
            for micro_desc in bundle.micro_descriptors:
                micro_counts[micro_desc.case_group] = int(micro_counts.get(micro_desc.case_group, 0)) + 1
                if micro_desc.case_group == "complete":
                    center_key = {"CenterB": "complete_centerB", "CenterC": "complete_centerC"}.get(micro_desc.center, f"complete_{micro_desc.center}")
                    micro_counts[center_key] = int(micro_counts.get(center_key, 0)) + 1
                    micro_counts[f"complete_{micro_desc.pathology_focus}"] = int(micro_counts.get(f"complete_{micro_desc.pathology_focus}", 0)) + 1
                else:
                    micro_counts[f"partial_{micro_desc.pathology_focus}"] = int(micro_counts.get(f"partial_{micro_desc.pathology_focus}", 0)) + 1
        expected_400 = {
            "complete": 200,
            "lge_only": 100,
            "lge_c0": 100,
            "complete_centerB": 100,
            "complete_centerC": 100,
            "complete_scar": 100,
            "complete_edema": 100,
            "partial_edema": 0,
        }
        expected_400_micro = {
            "complete": 800,
            "lge_only": 400,
            "lge_c0": 400,
            "complete_centerB": 400,
            "complete_centerC": 400,
            "complete_scar": 400,
            "complete_edema": 400,
            "partial_edema": 0,
        }
        status = "PASS"
        failures = []
        if int(steps) == 400 and stage_for_step(start_step) in {"A", "B"}:
            for key, expected in expected_400.items():
                observed = int(counts.get(key, 0))
                if observed != expected:
                    failures.append({"field": key, "expected": expected, "observed": observed})
            for key, expected in expected_400_micro.items():
                observed = int(micro_counts.get(key, 0))
                if observed != expected:
                    failures.append({"field": f"micro_{key}", "expected": expected, "observed": observed})
            status = "PASS" if not failures else "FAIL"
        payload = {
            "status": status,
            "fold": self.fold,
            "start_step": int(start_step),
            "steps": int(steps),
            "counts": counts,
            "microbatch_count": int(steps) * 4,
            "micro_counts": micro_counts,
            "all_four_same_case_fraction": float(all_four_same / max(int(steps), 1)),
            "distinct_case_count_distribution": distinct_distribution,
            "expected_400_stage_a_b": expected_400,
            "expected_400_stage_a_b_micro": expected_400_micro,
            "failures": failures,
            "descriptor_sequence_sha256": hashlib.sha256("|".join(descriptor_hashes).encode("utf-8")).hexdigest(),
            "sampler_rng_state_restored": True,
            "microbatch_case_draw": "independent_with_replacement_rng_per_group",
            "microbatch_rng_state_saved_fields": ["micro_case_rng_state_by_group", "micro_patch_rng_state"],
            "partial_events_do_not_advance_complete_pathology_cursor": True,
        }
        payload["payload_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return payload


def compute_actual_train_area_references(repo_root: Path, fold: int) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    rows = [row for row in build_care_ase_case_roles(repo_root, int(fold)) if row.role == "actual-train"]
    preprocessed = repo_root / PREPROCESSED_REL
    scar_fracs: list[float] = []
    edema_fracs: list[float] = []
    for row in rows:
        seg_path = preprocessed / f"{row.case_id}_seg.b2nd"
        seg = np.asarray(blosc2.open(str(seg_path), mode="r")[:])[0]
        wall = (seg == 1) | (seg == 4) | (seg == 5)
        scar = seg == 5
        edema = seg == 4
        wall_by_slice = wall.sum(axis=(1, 2)).astype(np.float64)
        scar_by_slice = scar.sum(axis=(1, 2)).astype(np.float64)
        edema_by_slice = edema.sum(axis=(1, 2)).astype(np.float64)
        scar_valid = (scar_by_slice > 0) & (wall_by_slice > 0)
        edema_valid = (edema_by_slice > 0) & (wall_by_slice > 0)
        scar_fracs.extend((scar_by_slice[scar_valid] / wall_by_slice[scar_valid]).astype(float).tolist())
        if row.t2_present:
            edema_fracs.extend((edema_by_slice[edema_valid] / wall_by_slice[edema_valid]).astype(float).tolist())
    if not scar_fracs:
        raise RuntimeError(f"no actual-train scar-positive slices/cases for fold {fold}")
    if not edema_fracs:
        raise RuntimeError(f"no actual-train T2-present pure-edema-positive slices/cases for fold {fold}")
    payload = {
        "fold": int(fold),
        "source": "actual_train_only",
        "inner_or_outer_access": "forbidden_not_used",
        "scar_reference": float(np.median(np.asarray(scar_fracs, dtype=np.float64))),
        "edema_reference": float(np.median(np.asarray(edema_fracs, dtype=np.float64))),
        "scar_positive_slice_count": len(scar_fracs),
        "edema_positive_t2_present_slice_count": len(edema_fracs),
        "denominator_wall_union_labels": [1, 4, 5],
    }
    payload["payload_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload
