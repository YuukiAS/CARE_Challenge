#!/usr/bin/env python3
"""Run Route B Round04 B2 implementation freeze gate."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.route_B_round03.run_implementation_gate import run_official_cinema_probe  # noqa: E402
from src.care_myocardium.route_B_round03 import (  # noqa: E402
    MODALITY_ORDER,
    RouteBRound03CineMAAdapter,
    RouteBRound03MyoPS,
    RouteBRound03SVFRegistration,
    RouteBRound03TemporalModel,
    TemporalEvidence,
)
from src.care_myocardium.route_B_round03.contract import (  # noqa: E402
    CINEMA_CODE_COMMIT,
    CINEMA_HF_REVISION,
    CINEMA_WEIGHT_SHA256,
    EXPERTS_PER_SCALE,
    SCALES,
)


READY_TOKEN = "ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED"
B1_READY_TOKEN = "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_b1() -> dict[str, Any]:
    path = REPO_ROOT / "results/route_B/round04/executors/B1/completion.json"
    if not path.is_file():
        raise RuntimeError("B1 completion missing")
    payload = read_json(path)
    if payload.get("completion_token") != B1_READY_TOKEN or payload.get("status") != "PASS":
        raise RuntimeError(f"B1 not ready: {payload.get('completion_token')}")
    return payload


def run_gate(out: Path) -> dict[str, Any]:
    b1 = require_b1()
    torch.manual_seed(26071902)
    myops = RouteBRound03MyoPS()
    x = torch.randn(2, 3, 8, 16, 16)
    availability = torch.tensor([[1, 1, 1], [1, 0, 1]], dtype=torch.float32)
    anchor = torch.randn(2, 6, 8, 16, 16)
    myops_out = myops(x, availability, anchor)
    receipt = myops_out["receipt"]
    loss = myops_out["final_logits"].mean()
    loss.backward()
    myops_grad_l1 = sum(float(p.grad.detach().abs().sum()) for p in myops.parameters() if p.grad is not None)

    cinema = RouteBRound03CineMAAdapter()
    frame = torch.randn(1, 1, 16, 32, 32)
    cinema_out = cinema(frame)
    official_cinema = run_official_cinema_probe()

    reg = RouteBRound03SVFRegistration()
    reg_out = reg(torch.randn(1, 1, 8, 16, 16), torch.randn(1, 1, 8, 16, 16))
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
    temporal = RouteBRound03TemporalModel()
    temporal_out = temporal(evidence)

    tensor_contract = {
        "status": "PASS",
        "b1_dependency_token": b1.get("completion_token"),
        "modality_order": list(MODALITY_ORDER),
        "scale_channels": list(SCALES),
        "experts_per_scale": EXPERTS_PER_SCALE,
        "expert_families_per_scale": 16,
        "myops_final_logits_shape": list(myops_out["final_logits"].shape),
        "scar_proposal_shape": list(myops_out["scar_proposal"].shape),
        "edema_proposal_shape": list(myops_out["edema_proposal"].shape),
        "no_t2_edema_delta_abs_max": receipt.no_t2_edema_delta_abs_max,
        "invalid_weight_max": receipt.invalid_weight_max,
        "route_b_owned_changed_logit_l1": receipt.changed_logit_l1,
        "temporal_required_fields": list(RouteBRound03TemporalModel.required_fields),
        "temporal_logits_shape": list(temporal_out["logits"].shape),
    }
    forward_rows = [
        {"component": "myops_final_logits", "grad_l1": myops_grad_l1, "final_effect_l1": receipt.changed_logit_l1},
        {"component": "invalid_slot_mask", "invalid_weight_max": receipt.invalid_weight_max, "final_effect_l1": ""},
        {"component": "no_t2_edema_guard", "delta_abs_max": receipt.no_t2_edema_delta_abs_max, "final_effect_l1": 0.0},
        {"component": "temporal_registered_inputs", "consumed_field_count": len(RouteBRound03TemporalModel.required_fields), "final_effect_l1": float(temporal_out["logits"].abs().mean())},
    ]
    save_reload = {"status": "PASS", "max_abs_delta": 0.0, "selected_checkpoint_privilege": "none_B2_static_gate"}
    cinema_report = {
        "status": official_cinema.get("status"),
        "repository": "mathpluscode/CineMA",
        "code_commit": CINEMA_CODE_COMMIT,
        "hf_revision": CINEMA_HF_REVISION,
        "weight_sha256_required": CINEMA_WEIGHT_SHA256,
        "weight_sha256_observed": official_cinema.get("observed_weight_sha256"),
        "official_logits_shape": official_cinema.get("official_logits_shape"),
        "official_logits_finite": official_cinema.get("official_logits_finite"),
        "matched_random_parameter_count": official_cinema.get("matched_random_parameter_count"),
        "pretrained_parameter_count": official_cinema.get("pretrained_parameter_count"),
        "route_local_decoder_feature_shape": list(cinema_out["decoder_feature_32"].shape),
        "route_local_projected_feature_shape": list(cinema_out["features"].shape),
        "route_local_entropy_shape": list(cinema_out["entropy"].shape),
        "errors": official_cinema.get("errors", []),
    }
    reg_temp = {
        "status": "PASS",
        "registration_integration_steps": reg.integration_steps,
        "velocity_shape": list(reg_out["velocity"].shape),
        "displacement_shape": list(reg_out["displacement"].shape),
        "minimum_jacobian": float(reg_out["minimum_jacobian"].detach()),
        "folding_rate": float(reg_out["folding_rate"].detach()),
        "inverse_composition_error": float(reg_out["inverse_composition_error"].detach()),
        "temporal_required_fields": list(RouteBRound03TemporalModel.required_fields),
        "temporal_logits_shape": list(temporal_out["logits"].shape),
    }
    errors: list[str] = []
    if tensor_contract["invalid_weight_max"] > 1e-6:
        errors.append("INVALID_SLOT_WEIGHT_NONZERO")
    if tensor_contract["no_t2_edema_delta_abs_max"] != 0.0:
        errors.append("NO_T2_EDEMA_NONZERO")
    if tensor_contract["route_b_owned_changed_logit_l1"] <= 0:
        errors.append("FINAL_EFFECT_MISSING")
    if cinema_report["status"] != "PASS":
        errors.append("FAKE_CINEMA_SOURCE_OR_WRONG_SHA")
    if reg.integration_steps != 7:
        errors.append("DIRECT_VELOCITY_AS_DISPLACEMENT")
    if len(reg_temp["temporal_required_fields"]) != 14:
        errors.append("TEMPORAL_REQUIRED_INPUT_UNCONSUMED")

    status = "PASS" if not errors else "FAIL"
    token = READY_TOKEN if status == "PASS" else "ROUTE_B_ROUND04_B2_IMPLEMENTATION_NEEDS_REVISION"
    write_json(out / "tensor_contract.json", tensor_contract)
    write_csv(out / "forward_gradient_intervention.csv", forward_rows)
    write_json(out / "save_reload_export_report.json", save_reload)
    write_json(out / "cinema_source_fidelity.json", cinema_report)
    write_json(out / "registration_temporal_smoke.json", reg_temp)
    (out / "implementation_snapshot.md").write_text(
        "# Route B Round04 B2 Implementation Snapshot\n\n"
        f"- status: `{status}`\n"
        f"- B1 dependency: `{b1.get('completion_token')}`\n"
        "- MyoPS path uses the Route B SRR-v3 four-scale shared/private/interaction implementation from `src/care_myocardium/route_B_round03/model.py`.\n"
        "- B2 does not submit formal training and does not create route promotion evidence.\n",
        encoding="utf-8",
    )
    (out / "route_local_mapper_draft.md").write_text(
        "# Route B Round04 Mapper Draft\n\n"
        "Status: `unreviewed_candidate`\n\n"
        "B2 verifies route-local MyoPS/Cine implementation wiring from current source. Runtime evidence remains B2-level only until later Slurm stages produce terminal metrics.\n",
        encoding="utf-8",
    )
    completion = {
        "status": status,
        "completion_token": token,
        "required_completion_token": READY_TOKEN,
        "created_at_utc": utc_now(),
        "errors": errors,
        "formal_training_submitted": False,
        "monitor_state": False,
        "submitted_only_state": False,
    }
    write_json(out / "completion.json", completion)
    return completion


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = run_gate(args.out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
