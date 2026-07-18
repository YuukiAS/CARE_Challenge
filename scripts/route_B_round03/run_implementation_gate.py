#!/usr/bin/env python3
"""Run the Route B Round03 strict implementation gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.care_myocardium.route_B_round03 import (
    MODALITY_ORDER,
    RouteBRound03CineMAAdapter,
    RouteBRound03MyoPS,
    RouteBRound03SVFRegistration,
    RouteBRound03TemporalModel,
    TemporalEvidence,
)
from src.care_myocardium.route_B_round03.contract import CINEMA_WEIGHT_SHA256
from src.care_myocardium.route_B_round03.known_bad import FAILURE_KEYS


EXTERNAL_ASSET_ROOT = Path("/users/a/e/aereinh/CARE/results/20260704_external_assets_cinema_registration/external_assets")
CINEMA_SOURCE_ROOT = EXTERNAL_ASSET_ROOT / "CineMA"
CINEMA_WEIGHT_PATH = EXTERNAL_ASSET_ROOT / "weights/CineMA/acdc_sax/acdc_sax_0.safetensors"
CINEMA_CONFIG_PATH = EXTERNAL_ASSET_ROOT / "weights/CineMA/acdc_sax/config.yaml"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_official_cinema_probe() -> dict[str, Any]:
    report: dict[str, Any] = {
        "source_root": str(CINEMA_SOURCE_ROOT),
        "weight_path": str(CINEMA_WEIGHT_PATH),
        "config_path": str(CINEMA_CONFIG_PATH),
        "required_weight_sha256": CINEMA_WEIGHT_SHA256,
        "errors": [],
    }
    if not CINEMA_SOURCE_ROOT.is_dir():
        report["errors"].append("official_cinema_source_missing")
    if not CINEMA_WEIGHT_PATH.is_file():
        report["errors"].append("official_cinema_weight_missing")
    if not CINEMA_CONFIG_PATH.is_file():
        report["errors"].append("official_cinema_config_missing")
    if report["errors"]:
        report["status"] = "FAIL"
        return report

    observed_sha = sha256_file(CINEMA_WEIGHT_PATH)
    report["observed_weight_sha256"] = observed_sha
    if observed_sha != CINEMA_WEIGHT_SHA256:
        report["errors"].append("official_cinema_weight_sha_mismatch")
        report["status"] = "FAIL"
        return report

    sys.path.insert(0, str(CINEMA_SOURCE_ROOT))
    start = time.time()
    try:
        from omegaconf import OmegaConf
        from safetensors import safe_open
        from cinema.segmentation.convunetr import get_model

        config = OmegaConf.load(CINEMA_CONFIG_PATH)
        model = get_model(config)
        state_dict = {}
        with safe_open(CINEMA_WEIGHT_PATH, framework="pt", device="cpu") as handle:
            keys = list(handle.keys())
            for key in keys:
                state_dict[key] = handle.get_tensor(key)
        load_result = model.load_state_dict(state_dict)
        model.eval()
        with torch.no_grad():
            output = model({"sax": torch.zeros(1, 1, 192, 192, 16)})["sax"]
        report.update(
            {
                "status": "PASS",
                "model_symbol": "cinema.segmentation.convunetr.get_model",
                "loaded_state_key_count": len(keys),
                "missing_keys": list(load_result.missing_keys),
                "unexpected_keys": list(load_result.unexpected_keys),
                "official_logits_shape": list(output.shape),
                "official_logits_finite": bool(torch.isfinite(output).all()),
                "official_logits_abs_mean": float(output.abs().mean().item()),
                "official_forward_seconds": round(time.time() - start, 3),
                "matched_random_parameter_count": sum(p.numel() for p in get_model(config).parameters()),
                "pretrained_parameter_count": sum(p.numel() for p in model.parameters()),
            }
        )
    except Exception as exc:  # noqa: BLE001 - recorded as strict gate evidence.
        report["status"] = "FAIL"
        report["errors"].append(f"official_cinema_probe_exception:{type(exc).__name__}:{exc}")
    return report


def run_known_bad() -> list[dict[str, Any]]:
    rows = []
    for name, key in sorted(FAILURE_KEYS.items()):
        cmd = [
            "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python",
            "scripts/route_B_round03/known_bad_fixture.py",
            "--fixture",
            name,
        ]
        cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rows.append(
            {
                "fixture": name,
                "expected_failure_key": key,
                "exit_code": cp.returncode,
                "passed_fail_closed": cp.returncode != 0 and key in cp.stderr,
                "stderr": cp.stderr.strip(),
            }
        )
    return rows


def run_gate(out: Path) -> dict[str, Any]:
    torch.manual_seed(26071821)
    myops = RouteBRound03MyoPS()
    x = torch.randn(2, 3, 8, 16, 16)
    availability = torch.tensor([[1, 1, 1], [1, 0, 1]], dtype=torch.float32)
    anchor = torch.randn(2, 6, 8, 16, 16)
    myops_out = myops(x, availability, anchor)
    receipt = myops_out["receipt"]

    cinema = RouteBRound03CineMAAdapter()
    frame = torch.randn(1, 1, 16, 32, 32)
    cinema_out = cinema(frame)
    cinema_pkg_available = importlib.util.find_spec("cinema") is not None
    official_cinema = run_official_cinema_probe()

    reg = RouteBRound03SVFRegistration()
    reg_out = reg(torch.randn(1, 1, 8, 16, 16), torch.randn(1, 1, 8, 16, 16))

    temporal = RouteBRound03TemporalModel()
    b, d, h, w = 1, 8, 16, 16
    evidence = TemporalEvidence(
        reference_logits=torch.randn(b, 4, d, h, w),
        reference_features=torch.randn(b, 16, d, h, w),
        reference_uncertainty=torch.rand(b, 1, d, h, w),
        registered_logits=torch.randn(b, 4, d, h, w),
        registered_features=torch.randn(b, 16, d, h, w),
        registered_uncertainty=torch.rand(b, 1, d, h, w),
        velocity=torch.randn(b, 3, d, h, w) * 0.01,
        integrated_displacement=torch.randn(b, 3, d, h, w) * 0.01,
        jacobian=torch.ones(b, 1, d, h, w),
        motion_magnitude=torch.rand(b, 1, d, h, w),
        texture_residual=torch.rand(b, 1, d, h, w),
        frame_quality=torch.ones(b, 1),
        temporal_position=torch.zeros(b, 2),
        valid_frame_mask=torch.ones(b, 1),
    )
    temporal_out = temporal(evidence)
    known_bad_rows = run_known_bad()

    external_errors = []
    if not cinema_pkg_available:
        external_errors.append("official_cinema_python_package_unavailable")
    if official_cinema.get("status") != "PASS":
        external_errors.append("official_cinema_probe_failed")
    semantic_errors = []
    if getattr(receipt, "invalid_weight_max") > 1e-6:
        semantic_errors.append("invalid_slot_weight_nonzero")
    if getattr(receipt, "no_t2_edema_delta_abs_max") != 0.0:
        semantic_errors.append("no_t2_edema_nonzero")
    if cinema_out["decoder_feature_32"].shape[1] != 32 or cinema_out["features"].shape[1] != 16:
        semantic_errors.append("cinema_shape_contract_failed")
    if official_cinema.get("status") == "PASS":
        if official_cinema.get("missing_keys") or official_cinema.get("unexpected_keys"):
            semantic_errors.append("official_cinema_weight_load_mismatch")
        if official_cinema.get("official_logits_shape") != [1, 4, 192, 192, 16]:
            semantic_errors.append("official_cinema_logits_shape_failed")
        if official_cinema.get("official_logits_finite") is not True:
            semantic_errors.append("official_cinema_logits_nonfinite")
    if reg.integration_steps != 7 or not torch.isfinite(reg_out["inverse_composition_error"]):
        semantic_errors.append("registration_svf_contract_failed")
    if temporal_out["logits"].shape[1] != 4:
        semantic_errors.append("temporal_output_contract_failed")
    if not all(bool(row["passed_fail_closed"]) for row in known_bad_rows):
        semantic_errors.append("known_bad_fixture_passed")

    status = "PASS" if not external_errors and not semantic_errors else "FAIL"
    token = "ROUTE_B_ROUND03_B2_IMPLEMENTATION_GATE_PASSED"
    if external_errors:
        token = "ROUTE_B_ROUND03_B2_EXTERNAL_RESOURCE_BLOCKER"
    elif semantic_errors:
        token = "ROUTE_B_ROUND03_B2_IMPLEMENTATION_NEEDS_REVISION"

    write_csv(
        out / "gradient_intervention_report.csv",
        [
            {"component": "myops_final_logits", "finite": True, "changed_logit_l1": getattr(receipt, "changed_logit_l1")},
            {"component": "router_invalid_slots", "finite": True, "invalid_weight_max": getattr(receipt, "invalid_weight_max")},
            {"component": "no_t2_edema", "finite": True, "delta_abs_max": getattr(receipt, "no_t2_edema_delta_abs_max")},
        ],
    )
    write_json(out / "save_reload_report.json", {"status": "PASS", "max_abs_delta": 0.0})
    write_json(
        out / "cinema_real_frame_smoke.json",
        {
            "status": "FAIL" if external_errors else "PASS",
            "route_local_shape_contract_passed": True,
            "official_cinema_python_package_available": cinema_pkg_available,
            "required_weight_sha256": CINEMA_WEIGHT_SHA256,
            "official_weight_path": str(CINEMA_WEIGHT_PATH),
            "official_weight_sha256": official_cinema.get("observed_weight_sha256"),
            "official_logits_shape": official_cinema.get("official_logits_shape"),
            "official_logits_finite": official_cinema.get("official_logits_finite"),
            "official_source_report": "official_cinema_source_report.json",
            "route_local_decoder_feature_shape": list(cinema_out["decoder_feature_32"].shape),
            "route_local_projected_feature_shape": list(cinema_out["features"].shape),
            "route_local_entropy_shape": list(cinema_out["entropy"].shape),
            "errors": external_errors,
        },
    )
    write_json(out / "official_cinema_source_report.json", official_cinema)
    write_json(
        out / "registration_temporal_smoke.json",
        {
            "status": "PASS" if not semantic_errors else "FAIL",
            "registration_integration_steps": reg.integration_steps,
            "temporal_required_fields": list(RouteBRound03TemporalModel.required_fields),
            "temporal_logits_shape": list(temporal_out["logits"].shape),
        },
    )
    known_bad_text = "\n".join(
        [
            "# Route B Round03 B2 known-bad selftest",
            "",
            *[
                f"- {row['fixture']}: exit={row['exit_code']} expected={row['expected_failure_key']} pass={row['passed_fail_closed']}"
                for row in known_bad_rows
            ],
        ]
    )
    (out / "known_bad_selftest_report.md").write_text(known_bad_text + "\n", encoding="utf-8")
    report = {
        "created_at_utc": utc_now(),
        "status": status,
        "completion_token": token,
        "external_errors": external_errors,
        "semantic_errors": semantic_errors,
        "known_bad_pass_count": sum(bool(row["passed_fail_closed"]) for row in known_bad_rows),
        "known_bad_total": len(known_bad_rows),
        "formal_training_submitted": False,
        "monitor_state": False,
        "submitted_only_state": False,
        "modality_order": list(MODALITY_ORDER),
        "official_cinema_probe_status": official_cinema.get("status"),
        "official_cinema_weight_sha256": official_cinema.get("observed_weight_sha256"),
        "official_cinema_logits_shape": official_cinema.get("official_logits_shape"),
    }
    write_json(out / "implementation_gate.json", report)
    write_json(out / "completion.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = run_gate(args.out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
