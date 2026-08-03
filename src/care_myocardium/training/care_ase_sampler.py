"""Deterministic CARE-ASE R2 sampler and actual-train area references."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import pickle
import random
from pathlib import Path
from typing import Any

import blosc2
import numpy as np

from src.care_myocardium.data.care_ase_splits import PREPROCESSED_REL, build_care_ase_case_roles, sha256_file
from src.care_myocardium.data.case_metadata import load_myops_case_metadata


HARD_NEGATIVE_MANIFEST_TEMPLATE = "results/20260803_care_ase_r2_full_fidelity_execution/hard_negative_manifest_fold{fold}.json"
LEGACY_HARD_NEGATIVE_MANIFEST_TEMPLATE = "results/20260801_care_ase_final_model/hard_negative_manifest_fold{fold}.csv"


@dataclass(frozen=True)
class CAREASEBatchDescriptor:
    fold: int
    global_step: int
    stage_id: str
    case_id: str
    case_group: str
    center: str
    pathology_focus: str
    within_focus: str
    availability: tuple[float, float, float]
    hard_negative_category: str
    hard_negative_counts: dict[str, int]
    resolved_target_coordinates: tuple[tuple[int, int, int], ...]
    fallback_sequence: tuple[str, ...]

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


def _load_hard_negative_manifest(repo_root: Path, fold: int) -> dict[str, Any]:
    candidates = [
        repo_root / HARD_NEGATIVE_MANIFEST_TEMPLATE.format(fold=int(fold)),
        repo_root / LEGACY_HARD_NEGATIVE_MANIFEST_TEMPLATE.format(fold=int(fold)),
    ]
    path = next((item for item in candidates if item.is_file()), candidates[0])
    if not path.is_file():
        return {"manifest_path": str(path), "manifest_sha256": "MISSING", "cases": {}}
    if path.suffix == ".csv":
        cases: dict[str, dict[str, int]] = {}
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cases[str(row["case_id"])] = {
                    "scar_fp_voxels": int(float(row.get("scar_fp_voxels", 0) or 0)),
                    "scar_fn_voxels": int(float(row.get("scar_fn_voxels", 0) or 0)),
                    "edema_fp_voxels": int(float(row.get("edema_fp_voxels", 0) or 0)),
                    "edema_fn_voxels": int(float(row.get("edema_fn_voxels", 0) or 0)),
                }
        return {"manifest_path": str(path), "manifest_sha256": sha256_file(path), "cases": cases}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"hard-negative manifest is not a JSON object: {path}")
    data.setdefault("cases", {})
    data["manifest_path"] = str(path)
    data["manifest_sha256"] = sha256_file(path)
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
        if pathology_focus == "scar" and within_focus == "oof_fn" and counts["scar_fn_voxels"] > 0:
            return "scar_oof_fn", counts, _coords(value, "scar_oof_fn")
        if pathology_focus == "scar" and within_focus == "oof_fp" and counts["scar_fp_voxels"] > 0:
            return "scar_oof_fp", counts, _coords(value, "scar_oof_fp")
        if pathology_focus == "edema" and within_focus == "oof_fn_or_low_volume" and counts["edema_fn_voxels"] > 0:
            return "edema_oof_fn_or_low_volume", counts, _coords(value, "edema_oof_fn_or_low_volume")
        if pathology_focus == "edema" and within_focus == "safe_fp" and counts["edema_fp_voxels"] > 0:
            return "edema_safe_fp", counts, _coords(value, "edema_safe_fp")
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

    def __init__(self, repo_root: Path, fold: int, *, seed: int = 20260803) -> None:
        self.repo_root = repo_root.resolve()
        self.fold = int(fold)
        self.seed = int(seed)
        self.rng = random.Random(f"{seed}|fold={fold}")
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
        self.hard_negative_manifest = _load_hard_negative_manifest(self.repo_root, self.fold)
        self.case_group_cursor = 0
        self.complete_center_cursor = 0
        self.complete_pathology_cursor = 0
        self.partial_case_cursors = {"lge_only": 0, "lge_c0": 0}
        self.scar_focus_cursor = 0
        self.edema_focus_cursor = 0
        self.batch_descriptor_cursor = 0

    def _choose_case(self, group: str, cursor: int) -> str:
        values = self.by_group.get(group, [])
        if not values:
            raise RuntimeError(f"CARE-ASE R2 sampler has no actual-train cases for group={group} fold={self.fold}")
        return values[cursor % len(values)]

    def descriptor_for_step(self, global_step: int) -> CAREASEBatchDescriptor:
        stage = stage_for_step(global_step)
        if stage in {"A", "B"}:
            group = self.stage_a_b_cycle[self.case_group_cursor % len(self.stage_a_b_cycle)]
            self.case_group_cursor += 1
            if group == "complete":
                center_group = self.stage_c_cycle[self.complete_center_cursor % len(self.stage_c_cycle)]
                case_id = self._choose_case(center_group, self.complete_center_cursor)
                self.complete_center_cursor += 1
            else:
                cursor = self.partial_case_cursors[group]
                case_id = self._choose_case(group, cursor)
                self.partial_case_cursors[group] = cursor + 1
        elif stage == "C":
            group = self.stage_c_cycle[self.complete_center_cursor % len(self.stage_c_cycle)]
            case_id = self._choose_case(group, self.complete_center_cursor)
            self.complete_center_cursor += 1
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
        center, availability = self.case_meta[case_id]
        hard_category, hard_counts, hard_coords = _hard_negative_category(self.hard_negative_manifest, case_id, pathology, within_focus)
        return CAREASEBatchDescriptor(
            fold=self.fold,
            global_step=int(global_step),
            stage_id=stage,
            case_id=case_id,
            case_group=group,
            center=center,
            pathology_focus=pathology,
            within_focus=within_focus,
            availability=availability,
            hard_negative_category=hard_category,
            hard_negative_counts=hard_counts,
            resolved_target_coordinates=hard_coords,
            fallback_sequence=_fallback_sequence(pathology, within_focus, hard_category),
        )

    def peek_descriptor_for_step(self, global_step: int) -> CAREASEBatchDescriptor:
        clone = CAREASEDeterministicSampler(self.repo_root, self.fold, seed=self.seed)
        clone.load_state_dict(self.state_dict())
        return clone.descriptor_for_step(global_step)

    def state_dict(self, *, next_descriptor: CAREASEBatchDescriptor | None = None) -> dict[str, Any]:
        state = {
            "case_group_cursor": self.case_group_cursor,
            "complete_center_cursor": self.complete_center_cursor,
            "complete_pathology_cursor": self.complete_pathology_cursor,
            "partial_case_cursors": dict(self.partial_case_cursors),
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
        return state

    def load_state_dict(self, state: dict[str, Any]) -> None:
        self.case_group_cursor = int(state["case_group_cursor"])
        self.complete_center_cursor = int(state.get("complete_center_cursor", state.get("center_cursor", 0)))
        self.complete_pathology_cursor = int(state.get("complete_pathology_cursor", state.get("pathology_focus_cursor", 0)))
        self.partial_case_cursors = {str(k): int(v) for k, v in state.get("partial_case_cursors", {"lge_only": 0, "lge_c0": 0}).items()}
        self.partial_case_cursors.setdefault("lge_only", 0)
        self.partial_case_cursors.setdefault("lge_c0", 0)
        self.scar_focus_cursor = int(state["scar_focus_cursor"])
        self.edema_focus_cursor = int(state["edema_focus_cursor"])
        self.batch_descriptor_cursor = int(state["batch_descriptor_cursor"])
        rng_state = state.get("sampler_rng_state")
        if isinstance(rng_state, str) and rng_state and rng_state != "UNSET":
            self.rng.setstate(_decode_rng_state(rng_state))

    def dry_run_counts(self, steps: int, *, start_step: int = 0) -> dict[str, int]:
        clone = CAREASEDeterministicSampler(self.repo_root, self.fold, seed=self.seed)
        clone.load_state_dict(self.state_dict())
        counts: dict[str, int] = {}
        for step in range(int(start_step), int(start_step) + int(steps)):
            desc = clone.descriptor_for_step(step)
            counts[desc.case_group] = counts.get(desc.case_group, 0) + 1
        return counts

    def composition_receipt(self, steps: int, *, start_step: int = 0) -> dict[str, Any]:
        clone = CAREASEDeterministicSampler(self.repo_root, self.fold, seed=self.seed)
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
        for step in range(int(start_step), int(start_step) + int(steps)):
            desc = clone.descriptor_for_step(step)
            descriptor_hashes.append(desc.sha256())
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
        status = "PASS"
        failures = []
        if int(steps) == 400 and stage_for_step(start_step) in {"A", "B"}:
            for key, expected in expected_400.items():
                observed = int(counts.get(key, 0))
                if observed != expected:
                    failures.append({"field": key, "expected": expected, "observed": observed})
            status = "PASS" if not failures else "FAIL"
        payload = {
            "status": status,
            "fold": self.fold,
            "start_step": int(start_step),
            "steps": int(steps),
            "counts": counts,
            "expected_400_stage_a_b": expected_400,
            "failures": failures,
            "descriptor_sequence_sha256": hashlib.sha256("|".join(descriptor_hashes).encode("utf-8")).hexdigest(),
            "sampler_rng_state_restored": True,
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
