#!/usr/bin/env python
"""Fail-closed validator for CARE-PRISM result packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_W1 = [
    "adoption_receipt.json",
    "backbone_asset_resolution.json",
    "controller_context.json",
    "init_transplant_report_fold0.json",
    "init_transplant_report_fold1.json",
    "multiscale_usage_report.json",
    "data_pipeline_report.json",
    "loss_and_negative_space_report.json",
    "implementation_intervention_report.json",
    "known_bad_report.json",
    "checkpoint_resume_report.json",
    "implementation_validator_report.json",
    "label_semantics_report.json",
    "direct_loss_gradient_report.json",
    "anatomy_exchange_report.json",
    "sampler_balance_report.json",
]

REQUIRED_W2 = [
    "w2_training_summary.json",
    "preflight_training_receipt.json",
    "preflight_mechanism_report.json",
    "correspondence_freeze_receipt.json",
    "preflight_resume_report.json",
    "critic_repair_receipt.json",
    "label_semantics_report.json",
    "direct_loss_gradient_report.json",
    "anatomy_exchange_report.json",
    "sampler_balance_report.json",
    "exact_resume_report.json",
    "w2_adequacy_report.json",
]

REQUIRED_W3 = [
    "w3_training_summary.json",
    "w3_checkpoint_audit_report.json",
    "fold0_outer_once_lock.json",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mean_metric_delta(metrics_csv: Path, metric_name: str, key: str = "dice_delta_vs_nnunet") -> float:
    import csv

    rows = [row for row in csv.DictReader(metrics_csv.open(newline="", encoding="utf-8")) if row.get("metric_name") == metric_name]
    values = [float(row[key]) for row in rows if row.get(key) not in {None, "", "None"}]
    if not values:
        return 0.0
    return sum(values) / len(values)


def harm_count(metrics_csv: Path, metric_name: str) -> int:
    import csv

    return sum(
        1
        for row in csv.DictReader(metrics_csv.open(newline="", encoding="utf-8"))
        if row.get("metric_name") == metric_name and row.get("harm_vs_nnunet") == "True"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--stage", choices=["W1", "W2", "W1W2", "W3"], default="W1")
    args = parser.parse_args()
    errors: list[str] = []
    reports: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_W1:
        path = args.result_root / name
        if not path.exists():
            errors.append(f"missing required W1 file: {name}")
            continue
        try:
            reports[name] = read_json(path)
        except Exception as exc:
            errors.append(f"invalid JSON {name}: {exc}")
    for name, payload in reports.items():
        if name.endswith("_report.json") or name in {"backbone_asset_resolution.json", "implementation_validator_report.json"}:
            status = payload.get("status")
            if status not in {"PASS", "PASS_PLAN_DRIVEN_STOCK_NNUNET", None}:
                errors.append(f"{name} status is {status!r}")
    for name in ("init_transplant_report_fold0.json", "init_transplant_report_fold1.json"):
        payload = reports.get(name, {})
        if float(payload.get("transplant", {}).get("byte_coverage", 0.0)) < 0.99:
            errors.append(f"{name} byte coverage below 0.99")
        if float(payload.get("fp32_encoder_parity", {}).get("max_abs_error", 1.0)) > 1.0e-6:
            errors.append(f"{name} FP32 parity above 1e-6")
    loss = reports.get("loss_and_negative_space_report.json", {})
    data = reports.get("data_pipeline_report.json", {})
    if float(loss.get("no_t2_edema_probability_max", 1.0)) != 0.0:
        errors.append("no-T2 edema probability is not exact zero")
    if float(loss.get("no_t2_edema_refiner_grad_abs", 1.0)) != 0.0:
        errors.append("no-T2 edema gradient is not exact zero")
    if float(loss.get("scar_negative_target_sum", 0.0)) <= 0.0 or float(loss.get("edema_negative_target_sum", 0.0)) <= 0.0:
        errors.append("negative-space targets are empty")
    if float(data.get("edema_negative_target_sum_t2_case", 0.0)) <= 0.0:
        errors.append("real Dataset501 T2-present edema negative target is empty")
    for semantic_name in ["label_semantics_report.json", "direct_loss_gradient_report.json", "anatomy_exchange_report.json", "sampler_balance_report.json"]:
        payload = reports.get(semantic_name)
        if payload is not None and payload.get("status") != "PASS":
            errors.append(f"{semantic_name} did not PASS")
    label = reports.get("label_semantics_report.json", {})
    if label and label.get("label_semantics", {}).get("edema_zone") != "label==4 or label==5":
        errors.append("label semantics report does not bind edema_zone to label 4 or 5")
    direct = reports.get("direct_loss_gradient_report.json", {})
    if direct and any(float(v) <= 0.0 for v in direct.get("gradient_abs_sums", {}).values()):
        errors.append("direct proposal/negative gradients are not all nonzero")
    exchange = reports.get("anatomy_exchange_report.json", {})
    if exchange:
        if float(exchange.get("exchange_gate_grad_before_step", 0.0)) <= 0.0:
            errors.append("anatomy exchange gate has no initial gradient")
        if float(exchange.get("pathology_only_anatomy_decoder_grad_abs", 1.0)) != 0.0:
            errors.append("pathology gradient enters anatomy decoder")
    sampler = reports.get("sampler_balance_report.json", {})
    if sampler and any(float(v) > 1.0 for v in sampler.get("max_center_count_deviation", {}).values()):
        errors.append("sampler center balance deviation exceeds tolerance")
    if args.stage in {"W2", "W1W2"}:
        for name in REQUIRED_W2:
            path = args.result_root / name
            if not path.exists():
                errors.append(f"missing required W2 file: {name}")
                continue
            try:
                reports[name] = read_json(path)
            except Exception as exc:
                errors.append(f"invalid JSON {name}: {exc}")
        train = reports.get("preflight_training_receipt.json", {})
        if train.get("status") != "PASS":
            errors.append("W2 preflight training receipt did not PASS")
        if int(train.get("optimizer_steps", 0)) != 400:
            errors.append("W2 optimizer steps is not exactly 400")
        if bool(train.get("synthetic_credit_used", True)):
            errors.append("W2 used synthetic training credit")
        if float(train.get("logged_loss_drop_fraction", 0.0)) < 0.30:
            errors.append("W2 logged loss drop is below 30 percent")
        mech = reports.get("preflight_mechanism_report.json", {})
        if mech.get("status") != "PASS":
            errors.append("W2 mechanism report did not PASS")
        if any(float(v) <= 1.0e-7 for v in mech.get("matched_on_off_final_logit_deltas", {}).values()):
            errors.append("W2 matched on/off did not change final logits")
        if any(float(v) <= 0.0 for v in mech.get("gradient_abs_sums", {}).values()):
            errors.append("W2 mechanism gradients did not reach all target modules")
        corr = reports.get("correspondence_freeze_receipt.json", {})
        if corr.get("slice_correspondence_mode") != "identity_disabled" or not bool(corr.get("train_deploy_mode_match", False)):
            errors.append("W2 correspondence mode is not frozen identity")
        resume = reports.get("preflight_resume_report.json", {})
        if resume.get("status") != "PASS":
            errors.append("W2 resume report did not PASS")
        if float(resume.get("next_case_image_max_abs_delta_after_rng_restore", 1.0)) != 0.0:
            errors.append("W2 augmentation RNG restore is not exact")
        adequacy = reports.get("w2_adequacy_report.json", {})
        if adequacy.get("status") != "PASS":
            errors.append("W2 adequacy report did not PASS")
        known_bad = reports.get("known_bad_report.json", {})
        cases = {row.get("case"): row.get("status") for row in known_bad.get("known_bad_cases", [])}
        for required_case in [
            "wrong_edema_zone_label4_only",
            "wrong_myocardium_union_includes_blood",
            "detached_direct_loss",
            "dead_anatomy_exchange",
            "unsafe_no_t2_edema_negative",
            "fake_w2_pass_summary",
            "missing_inner_outer_lock",
        ]:
            if cases.get(required_case) != "PASS":
                errors.append(f"known-bad missing or not passing: {required_case}")
    if args.stage == "W3":
        for name in REQUIRED_W3:
            path = args.result_root / name
            if not path.exists():
                errors.append(f"missing required W3 file: {name}")
                continue
            try:
                reports[name] = read_json(path)
            except Exception as exc:
                errors.append(f"invalid JSON {name}: {exc}")
        train = reports.get("w3_training_summary.json", {})
        if train.get("status") != "PASS":
            errors.append("W3 training summary did not PASS")
        if int(train.get("optimizer_steps", 0)) != 6500:
            errors.append("W3 optimizer steps is not exactly 6500")
        if bool(train.get("synthetic_credit_used", True)):
            errors.append("W3 used synthetic training credit")
        audit = reports.get("w3_checkpoint_audit_report.json", {})
        audit_steps = [int(row.get("checkpoint_step", -1)) for row in audit.get("audits", [])]
        expected_steps = list(range(500, 6501, 500))
        if audit.get("status") != "PASS":
            errors.append("W3 checkpoint audit report did not PASS")
        if audit_steps != expected_steps:
            errors.append(f"W3 checkpoint audit steps are {audit_steps}, expected {expected_steps}")
        inner_dir = args.result_root / "evaluation/fold0_w3_inner_select_formal_v2"
        outer_dir = args.result_root / "evaluation/fold0_w3_outer_once_formal_v2"
        for name, directory in {"inner": inner_dir, "outer": outer_dir}.items():
            if not (directory / "summary.json").exists() or not (directory / "case_metrics.csv").exists():
                errors.append(f"missing W3 {name} evaluation outputs under {directory}")
        inner = read_json(inner_dir / "summary.json") if (inner_dir / "summary.json").exists() else {}
        freeze = read_json(inner_dir / "freeze_receipt.json") if (inner_dir / "freeze_receipt.json").exists() else {}
        outer = read_json(outer_dir / "summary.json") if (outer_dir / "summary.json").exists() else {}
        lock = reports.get("fold0_outer_once_lock.json", {})
        selected = (inner.get("selected_checkpoint") or {}).get("checkpoint")
        selected_sha = (inner.get("selected_checkpoint") or {}).get("checkpoint_sha256")
        if inner.get("status") != "PASS" or inner.get("split") != "inner_select" or bool(inner.get("outer_accessed", True)):
            errors.append("W3 inner selection did not stay on inner_select without outer access")
        if int(inner.get("checkpoint_count", 0)) != 13:
            errors.append("W3 inner selection did not evaluate all 13 checkpoints")
        if freeze.get("selected_checkpoint") != selected or freeze.get("selected_checkpoint_sha256") != selected_sha:
            errors.append("W3 freeze receipt does not match inner selected checkpoint")
        if lock.get("selected_checkpoint") != selected or lock.get("selected_checkpoint_sha256") != selected_sha:
            errors.append("W3 outer lock does not match frozen selected checkpoint")
        if outer.get("status") != "PASS" or outer.get("split") != "outer" or not bool(outer.get("outer_accessed", False)):
            errors.append("W3 outer evaluation did not run as outer")
        if int(outer.get("checkpoint_count", 0)) != 1:
            errors.append("W3 outer evaluation did not use exactly one frozen checkpoint")
        if (outer.get("selected_checkpoint") or {}).get("checkpoint") != selected:
            errors.append("W3 outer evaluation checkpoint does not match frozen selection")
        outer_metrics = outer_dir / "case_metrics.csv"
        if outer_metrics.exists():
            scar_delta = mean_metric_delta(outer_metrics, "scar")
            edema_delta = mean_metric_delta(outer_metrics, "edema_zone")
            scar_harm = harm_count(outer_metrics, "scar")
            edema_harm = harm_count(outer_metrics, "edema_zone")
            if scar_delta < 0.0 or edema_delta < 0.0:
                errors.append(f"W3 selected model is worse than same-fold nnU-Net on outer: scar_delta={scar_delta:.6f}, edema_delta={edema_delta:.6f}")
            if scar_harm > 0 or edema_harm > 0:
                errors.append(f"W3 outer help/harm gate failed: scar_harm={scar_harm}, edema_harm={edema_harm}")
    decision = "PASS" if not errors else "FAIL"
    out = {
        "status": decision,
        "errors": errors,
        "stage": args.stage,
        "failure_classification": "CALIBRATION" if args.stage == "W3" and errors else None,
        "validated_files": REQUIRED_W1
        + (REQUIRED_W2 if args.stage in {"W2", "W1W2"} else [])
        + (REQUIRED_W3 if args.stage == "W3" else []),
    }
    out_name = (
        "w1_w2_strict_validator_report.json"
        if args.stage == "W1W2"
        else "preflight_strict_validator_report.json"
        if args.stage == "W2"
        else "w3_strict_validator_report.json"
        if args.stage == "W3"
        else "strict_validator_report.json"
    )
    (args.result_root / out_name).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if decision == "PASS" else 1)


if __name__ == "__main__":
    main()
