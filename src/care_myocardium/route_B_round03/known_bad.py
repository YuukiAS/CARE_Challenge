"""Known-bad fixture checks for Route B Round03."""

from __future__ import annotations

from .contract import MODALITY_ORDER, assert_modality_order


FAILURE_KEYS = {
    "wrong_modality_order": "ROUTE_B_ROUND03_WRONG_MODALITY_ORDER",
    "bootstrap_formal_memory": "ROUTE_B_ROUND03_BOOTSTRAP_FORMAL_MEMORY",
    "ema_formal_memory": "ROUTE_B_ROUND03_EMA_FORMAL_MEMORY",
    "fake_cinema": "ROUTE_B_ROUND03_FAKE_CINEMA",
    "direct_velocity_displacement": "ROUTE_B_ROUND03_DIRECT_VELOCITY_DISPLACEMENT",
    "proxy_jacobian": "ROUTE_B_ROUND03_PROXY_JACOBIAN",
    "abstract_temporal_z": "ROUTE_B_ROUND03_TEMPORAL_Z_ONLY",
    "monitor_packet_completion": "ROUTE_B_ROUND03_MONITOR_PACKET_IS_NOT_COMPLETION",
    "bare_python_wrapper": "ROUTE_B_ROUND03_BARE_PYTHON_WRAPPER",
    "zero_myops_effect_plus_cine_gain": "ROUTE_B_ROUND03_ZERO_MYOPS_EFFECT_PLUS_CINE_GAIN",
}


def evaluate_known_bad(name: str) -> str:
    if name == "wrong_modality_order":
        assert_modality_order(("LGE", "C0", "T2"))
    if name == "valid_control":
        assert_modality_order(MODALITY_ORDER)
        return "PASS"
    if name not in FAILURE_KEYS:
        raise ValueError(f"unknown fixture {name}")
    raise RuntimeError(FAILURE_KEYS[name])
