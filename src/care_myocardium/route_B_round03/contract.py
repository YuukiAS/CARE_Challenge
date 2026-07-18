"""Machine-readable constants for Route B Round03."""

from __future__ import annotations

from dataclasses import dataclass


MODALITY_ORDER = ("LGE", "T2", "C0")
LEGACY_ROUTE_B_ORDER = ("LGE", "C0", "T2")
SCALES = (32, 64, 128, 256)
EXPERTS_PER_SCALE = 16
PATTERN_SIP_SEED = 26071822
SAMPLER_SEED = 26071821
NO_T2_EDEMA_POLICY = "exact_zero"
CINEMA_WEIGHT_SHA256 = "c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f"
CINEMA_CODE_COMMIT = "c10daa1d93f0ea28d8b9ad9206b0f673d25805c1"
CINEMA_HF_REVISION = "b1251ee50423bceeca84c080782fc3bc7756dea6"


@dataclass(frozen=True)
class Contract:
    modality_order: tuple[str, str, str]
    scales: tuple[int, int, int, int]
    experts_per_scale: int
    pattern_sip_formula: str
    prototype_bank: str
    registration: str
    temporal_interface: str


ROUTE_B_ROUND03_CONTRACT = Contract(
    modality_order=MODALITY_ORDER,
    scales=SCALES,
    experts_per_scale=EXPERTS_PER_SCALE,
    pattern_sip_formula="mass+0.50*integrative+0.25*load+0.10*sparse",
    prototype_bank="four_shard_fold_safe_oof_fitted_inference_frozen",
    registration="seven_step_svf_scaling_and_squaring_with_inverse",
    temporal_interface="registered_logits_features_uncertainty_velocity_displacement_jacobian_motion_quality_position_mask",
)


def assert_modality_order(order: tuple[str, ...] | list[str]) -> tuple[str, str, str]:
    normalized = tuple(str(item) for item in order)
    if normalized != MODALITY_ORDER:
        raise ValueError(f"ROUTE_B_ROUND03_WRONG_MODALITY_ORDER expected {MODALITY_ORDER}, got {normalized}")
    return MODALITY_ORDER


def pattern_sip_coefficient(step: int, stage: str) -> float:
    if stage == "evidence_warmup":
        if step < 1000:
            return 0.0
        if step < 2000:
            return 0.02 * ((step - 1000) / 1000.0)
        return 0.02
    if stage in {"proposal", "refiner"}:
        return 0.05
    if stage == "joint":
        return 0.02
    raise ValueError(f"unknown Route B stage: {stage}")
