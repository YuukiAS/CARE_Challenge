#!/usr/bin/env python3
"""Fail-closed CARE-ARC implementation and packet validator."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch

from src.care_myocardium.models.care_arc import CAREARC, build_care_arc, trainable_parameter_count

TASK_KEY = "20260729_care_arc_clean_fold1"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
MODEL_PATH = REPO_ROOT / "src/care_myocardium/models/care_arc.py"
FORBIDDEN_SOURCE_PATTERNS = [
    r"anchor_logits",
    r"anchor_probability",
    r"nnunet_.*prob",
    r"distance_to_myocardium",
    r"component_utility",
    r"prototype",
    r"dictionary",
    r"router",
    r"MoSAIC",
    r"MMRD",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def check_source_contract() -> list[str]:
    text = MODEL_PATH.read_text(encoding="utf-8")
    failures: list[str] = []
    for pattern in FORBIDDEN_SOURCE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            failures.append(f"forbidden_source_pattern:{pattern}")
    required_symbols = [
        "class CAREARCEncoder",
        "class FeatureAlignmentE2",
        "class EvidenceGate",
        "class PathologyDecoder",
        "class CAREARC",
        "log_burden_pred",
        "sdf_logvar",
        "scar_gates",
        "edema_gates",
    ]
    for symbol in required_symbols:
        if symbol not in text:
            failures.append(f"missing_symbol:{symbol}")
    return failures


def check_model_contract(device: str) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    torch.manual_seed(29)
    model = build_care_arc().to(device)
    model.eval()
    params = trainable_parameter_count(model)
    if not 20_000_000 <= params <= 45_000_000:
        failures.append(f"parameter_count_out_of_range:{params}")
    if model.shared_encoder_count != 1:
        failures.append("shared_encoder_count_not_one")
    images = torch.randn(1, 3, 2, 64, 64, device=device)
    avail = torch.tensor([[1.0, 1.0, 1.0]], device=device)
    ctx_a = {"probabilities": torch.randn(1, 6, 2, 64, 64, device=device)}
    ctx_b = {"probabilities": torch.randn(1, 6, 2, 64, 64, device=device) * 100.0}
    with torch.no_grad():
        out_a = model(images, avail, external_nnunet_context=ctx_a)
        out_b = model(images, avail, external_nnunet_context=ctx_b)
    for key in ("scar_direct_logit", "edema_zone_direct_logit"):
        if not torch.equal(out_a[key], out_b[key]):
            failures.append(f"external_context_changes_{key}")
    no_t2 = torch.tensor([[1.0, 0.0, 1.0]], device=device)
    out_no_t2 = model(images, no_t2)
    for key in ("direct_full_logit", "coarse_extent_logit", "sdf_mean", "sdf_logvar"):
        if float(out_no_t2["edema"][key].abs().max().detach().cpu()) != 0.0:
            failures.append(f"no_t2_edema_not_exact_zero:{key}")
    if float(out_no_t2["edema"]["presence_logit"].abs().max().detach().cpu()) != 0.0:
        failures.append("no_t2_edema_presence_not_exact_zero")
    pre_direct = model.scar_decoder.direct_head(out_a["scar"]["pre_film_features"])
    film_delta = (pre_direct - out_a["scar"]["direct_full_logit"]).abs().max()
    if float(film_delta.detach().cpu()) <= 0.0:
        failures.append("burden_film_does_not_change_direct_logits")
    report = {
        "trainable_parameter_count": params,
        "shared_encoder_count": model.shared_encoder_count,
        "external_context_invariance_exact": "external_context_changes_scar_direct_logit" not in failures
        and "external_context_changes_edema_zone_direct_logit" not in failures,
        "burden_film_max_abs_delta": float(film_delta.detach().cpu()),
        "no_t2_edema_max_abs": float(out_no_t2["edema_zone_direct_logit"].abs().max().detach().cpu()),
    }
    return failures, report


def check_preflight_artifacts(runtime_root: Path) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    required = {
        "receipt": runtime_root / "preflight_receipt.json",
        "gradient": runtime_root / "gradient_report.json",
        "parity": runtime_root / "full_volume_parity.json",
        "context": runtime_root / "context_invariance.json",
        "no_t2": runtime_root / "no_t2_exact_zero.json",
        "resume": runtime_root / "resume_exact.json",
    }
    loaded: dict[str, Any] = {}
    for name, path in required.items():
        if not path.exists():
            failures.append(f"missing_preflight_artifact:{name}:{path}")
            continue
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    if failures:
        return failures, {"runtime_root": str(runtime_root), "artifacts_present": sorted(loaded)}
    receipt = loaded["receipt"]
    loss_drop = receipt.get("loss_drop", {})
    if int(receipt.get("formal_training_credit", -1)) != 0:
        failures.append("preflight_not_zero_credit")
    if int(receipt.get("optimizer_steps", -1)) != 300:
        failures.append(f"preflight_optimizer_steps_not_300:{receipt.get('optimizer_steps')}")
    if int(receipt.get("gradient_accumulation", -1)) != 2:
        failures.append("preflight_gradient_accumulation_not_2")
    if float(loss_drop.get("scar_drop_fraction") or 0.0) < 0.30:
        failures.append(f"scar_loss_drop_below_30pct:{loss_drop.get('scar_drop_fraction')}")
    if float(loss_drop.get("edema_drop_fraction") or 0.0) < 0.30:
        failures.append(f"edema_loss_drop_below_30pct:{loss_drop.get('edema_drop_fraction')}")
    expected_roles = ["complete_trimodal", "lge_c0", "lge_only", "no_t2", "scar_positive", "edema_positive", "hard_negative"]
    selected = receipt.get("case_report", {}).get("selected_roles", {})
    for role in expected_roles:
        if not selected.get(role):
            failures.append(f"missing_preflight_role:{role}")
    if len(receipt.get("case_report", {}).get("present_wanted_depths", [])) < 2:
        failures.append("insufficient_multi_z_depth_coverage")
    grad = loaded["gradient"]
    if grad.get("status") != "PASS":
        failures.append("gradient_report_status_not_pass")
    for name, row in grad.get("modules", {}).items():
        if not row.get("has_gradient"):
            failures.append(f"missing_required_gradient:{name}")
    parity = loaded["parity"]
    if parity.get("status") != "PASS" or not all(row.get("shape_match") for row in parity.get("rows", [])):
        failures.append("full_volume_parity_failed")
    context = loaded["context"]
    if context.get("status") != "PASS" or not context.get("scar_exact") or not context.get("edema_exact"):
        failures.append("external_context_invariance_failed")
    no_t2 = loaded["no_t2"]
    if no_t2.get("status") != "PASS" or float(no_t2.get("edema_branch_gradient_max_abs", -1.0)) != 0.0:
        failures.append("no_t2_output_loss_or_gradient_not_exact_zero")
    resume = loaded["resume"]
    if resume.get("status") != "PASS":
        failures.append("checkpoint_resume_exact_failed")
    if float(receipt.get("burden_film_max_abs_delta") or 0.0) <= 0.0:
        failures.append("burden_film_no_direct_logit_delta")
    return failures, {
        "runtime_root": str(runtime_root),
        "receipt_status": receipt.get("status"),
        "loss_drop": loss_drop,
        "selected_roles": selected,
        "present_wanted_depths": receipt.get("case_report", {}).get("present_wanted_depths", []),
        "gradient_status": grad.get("status"),
        "no_t2_status": no_t2.get("status"),
        "resume_status": resume.get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="implementation")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", default=str(RESULT_ROOT / "implementation_validator_report.json"))
    parser.add_argument("--runtime-root", default=str(RESULT_ROOT / "runtime/preflight"))
    args = parser.parse_args()
    failures = []
    failures.extend(check_source_contract())
    model_failures, model_report = check_model_contract(args.device)
    failures.extend(model_failures)
    preflight_report = None
    if args.stage == "preflight":
        preflight_failures, preflight_report = check_preflight_artifacts(Path(args.runtime_root))
        failures.extend(preflight_failures)
    payload = {
        "task_key": TASK_KEY,
        "stage": args.stage,
        "created_at_utc": now_utc(),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "model_report": model_report,
        "preflight_report": preflight_report,
        "known_bad_coverage": [
            "source_forbidden_external_context_patterns",
            "parameter_count_range",
            "single_shared_encoder",
            "external_context_invariance",
            "no_t2_edema_exact_zero",
            "burden_film_changes_logits",
        ],
    }
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
