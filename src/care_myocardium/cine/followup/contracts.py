"""Fail-closed contracts for M10 follow-up Cine implementation fidelity.

These helpers are intentionally deterministic and lightweight. Wave F2 uses
them to prove that known bad Cine shortcuts cannot pass into Wave F3 runtime.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class ContractError(ValueError):
    """Raised when a Cine follow-up contract is incomplete or unsafe."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class CineMAProvenance:
    source_url: str
    repository: str
    model_identifier: str
    source_commit_or_tag: str
    license: str
    weight_filename: str
    weight_sha256: str
    architecture_identifier: str
    preprocessing: str
    label_map: Mapping[str, int]
    orientation: str
    spacing: Sequence[float]
    time_axis_convention: str
    case_frame_count: int
    output_channels: int
    feature_channels: int
    uncertainty_channels: int

    def validate(self) -> None:
        for field_name, value in asdict(self).items():
            _require(value not in ("", None, [], {}), f"missing provenance field: {field_name}")
        _require(self.source_url.startswith(("https://", "http://", "file://")), "source_url must be explicit")
        _require(len(self.weight_sha256) == 64 and all(c in "0123456789abcdef" for c in self.weight_sha256.lower()), "weight_sha256 must be a SHA256 hex digest")
        _require(self.output_channels >= 4, "CineMA evidence must be multiclass, not binary")
        _require(self.feature_channels > 0, "CineMA intermediate features are required")
        _require(self.uncertainty_channels > 0, "CineMA uncertainty is required")
        _require(len(self.spacing) == 3 and all(float(x) > 0 for x in self.spacing), "spacing must be positive 3D physical spacing")
        _require(self.case_frame_count > 0, "case/frame provenance must be non-empty")


@dataclass(frozen=True)
class AdapterControlContract:
    uses_verified_pretrained_path: bool
    trainable_adapter: str
    trainable_parameter_count: int
    random_init_parameter_count: int
    capacity_tolerance: float
    scheduled_checkpoints: int
    eval_case_count: int
    selected_checkpoint_name: str
    selected_checkpoint_reloaded: bool
    random_init_control_present: bool
    prior_channels: int
    feature_channels: int
    uncertainty_channels: int
    missing_non_reference_policy: str
    fallback_to_frame0: bool
    binarizes_prior: bool

    def validate(self) -> None:
        _require(self.uses_verified_pretrained_path, "verified pretrained CineMA path is required")
        _require(self.trainable_adapter in {"final_two_blocks", "lora", "declared_equivalent"}, "adapter must be explicitly trainable")
        _require(self.trainable_parameter_count > 0, "trainable adapter parameters are required")
        _require(self.random_init_control_present, "capacity-matched random initialization control is required")
        rel_delta = abs(self.trainable_parameter_count - self.random_init_parameter_count) / max(1, self.trainable_parameter_count)
        _require(rel_delta <= self.capacity_tolerance, "random-init control parameter count exceeds tolerance")
        _require(self.scheduled_checkpoints > 0, "scheduled checkpoint evaluation is required")
        _require(self.eval_case_count >= 12, "adapter/control evaluation requires at least 12 held-out cases")
        _require(bool(self.selected_checkpoint_name), "selected checkpoint name is required")
        _require(self.selected_checkpoint_reloaded, "selected checkpoint must be reloaded before export")
        _require(self.prior_channels >= 4, "binary foreground prior is forbidden")
        _require(self.feature_channels > 0, "nontrivial CineMA features are required")
        _require(self.uncertainty_channels > 0, "calibrated uncertainty is required")
        _require(self.missing_non_reference_policy == "record_frame_failure", "missing non-reference predictions must be recorded as frame failures")
        _require(not self.fallback_to_frame0, "frame0 fallback is forbidden")
        _require(not self.binarizes_prior, "binarized prior is forbidden")


@dataclass(frozen=True)
class RegistrationMathContract:
    input_rank: int
    input_layout: str
    reference_frame: str
    es_selection_rule: str
    selected_frame_count: int
    velocity_model: str
    unet_channels: Sequence[int]
    integration_method: str
    scaling_and_squaring_steps: int
    predicts_both_directions: bool
    unit_conversion: str
    uses_direct_velocity_as_displacement: bool
    objective_terms: Mapping[str, float]

    def validate(self) -> None:
        _require(self.input_rank == 6 and self.input_layout == "B,T,1,H,W,D", "registration input must be BxTx1xHxWxD")
        _require(self.reference_frame == "ED", "ED must be the registration reference")
        _require(self.es_selection_rule == "minimum_selected_checkpoint_lv_volume", "ES must use selected-checkpoint LV-volume rule")
        _require(self.selected_frame_count >= 8, "registration must select at least 8 frames")
        _require(self.velocity_model == "stationary_velocity_field", "registration must predict a stationary velocity field")
        _require(tuple(self.unet_channels) == (16, 32, 64, 128), "registration U-Net channels must be [16,32,64,128]")
        _require(self.integration_method == "scaling_and_squaring", "scaling-and-squaring integration is required")
        _require(self.scaling_and_squaring_steps == 7, "exactly seven scaling-and-squaring steps are required")
        _require(self.predicts_both_directions, "both phi_0<-t and phi_t<-0 are required")
        _require(self.unit_conversion == "normalized_grid_to_voxel_and_physical_mm", "explicit unit conversion is required")
        _require(not self.uses_direct_velocity_as_displacement, "direct velocity-as-displacement is forbidden")
        required = {
            "lncc_9x9x9": 1.00,
            "multiclass_dice": 1.00,
            "grad_v": 0.05,
            "negative_jacobian": 0.10,
            "inverse_consistency": 0.10,
        }
        _require(dict(self.objective_terms) == required, "registration objective terms do not match contract")


@dataclass(frozen=True)
class SynControlContract:
    command: str
    ants_version: str
    parameter_json: str
    transform_files: Sequence[str]
    same_case_frame_metrics: bool
    runtime_seconds_recorded: bool
    failure_rows_recorded: bool
    uses_proxy_after_metric: bool

    def validate(self) -> None:
        _require("antsRegistration" in self.command or "antsRegistrationSyN" in self.command, "real ANTs registration command is required")
        _require(bool(self.ants_version), "ANTs version is required")
        _require(bool(self.parameter_json), "ANTs parameter JSON is required")
        _require(len(self.transform_files) > 0, "ANTs transform files must be recorded")
        _require(self.same_case_frame_metrics, "SyN control must use same case/frame metrics")
        _require(self.runtime_seconds_recorded, "SyN runtime must be recorded")
        _require(self.failure_rows_recorded, "SyN failures must remain in denominator")
        _require(not self.uses_proxy_after_metric, "synthetic SyN proxy metrics are forbidden")


@dataclass(frozen=True)
class RegistrationGateEvidence:
    checkpoint_name: str
    selected_checkpoint_reloaded: bool
    eval_case_count: int
    pair_count: int
    case_level_denominator: int
    failed_rows_in_denominator: bool
    true_jacobian: bool
    physical_displacement_mm: bool
    inverse_consistency_composition: bool
    learned_noninferior_to_syn: bool

    def validate(self) -> None:
        _require(bool(self.checkpoint_name), "registration selected checkpoint is required")
        _require(self.selected_checkpoint_reloaded, "registration selected checkpoint must be reloaded")
        _require(self.eval_case_count >= 12, "registration eval requires at least 12 cases")
        _require(self.pair_count >= 60, "registration eval requires at least 60 non-reference pairs")
        _require(self.case_level_denominator >= self.eval_case_count, "case-level denominator must include all eligible cases")
        _require(self.failed_rows_in_denominator, "failure rows must remain in denominator")
        _require(self.true_jacobian, "true Jacobian determinant is required")
        _require(self.physical_displacement_mm, "physical displacement in mm is required")
        _require(self.inverse_consistency_composition, "inverse-consistency composition is required")
        _require(self.learned_noninferior_to_syn, "learned-vs-SyN comparison is required")


@dataclass(frozen=True)
class TemporalLaunchContract:
    registration_gate_passed: bool
    registration_checkpoint_reloaded: bool
    valid_non_reference_frames: int
    slot_names: Sequence[str]
    includes_velocity: bool
    includes_jacobian: bool
    includes_residual: bool
    includes_uncertainty: bool
    writes_temporal_output_without_registration: bool

    def validate(self) -> None:
        _require(self.registration_gate_passed, "temporal launch requires passed registration gate")
        _require(self.registration_checkpoint_reloaded, "temporal launch requires reloaded registration checkpoint")
        _require(self.valid_non_reference_frames >= 4, "fewer than four valid non-reference frames is registration failure")
        expected = (
            "ed_anatomy_anchor",
            "early_systolic_contraction",
            "late_systolic_contraction",
            "early_diastolic_relaxation",
            "late_diastolic_relaxation",
            "motion_magnitude",
            "registered_texture_residual",
            "registration_uncertainty_safety",
        )
        _require(tuple(self.slot_names) == expected, "temporal dictionary must use exactly eight required slots")
        _require(self.includes_velocity and self.includes_jacobian and self.includes_residual and self.includes_uncertainty, "temporal evidence is incomplete")
        _require(not self.writes_temporal_output_without_registration, "temporal output without passed registration is forbidden")


def build_freeze_receipt(paths: Iterable[Path], *, task_key: str, status: str = "FROZEN_FOR_WAVE_F3") -> dict[str, object]:
    files = []
    for path in sorted(paths, key=lambda p: str(p)):
        _require(path.is_file(), f"freeze path missing: {path}")
        files.append({"path": str(path), "sha256": sha256_file(path)})
    payload = {"task_key": task_key, "status": status, "files": files}
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    payload["freeze_hash"] = hashlib.sha256(encoded).hexdigest()
    return payload
