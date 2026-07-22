#!/usr/bin/env python3
"""Fail-closed validator for Batch7 minimal pathology decomposition."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260722_srr_batch7_minimal_pathology_decomposition"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY

MONITOR_TOKENS = (
    "NEEDS_MONITOR",
    "PENDING_MONITOR",
    "JOB_SUBMITTED",
    "PENDING_PRIORITY",
    "RUNNING",
    "AWAITING_SACCT",
    "NOT_SUBMITTED",
    "PENDING",
)

STATIC_REQUIRED_FILES = (
    "center_modality_inventory.csv",
    "pathology_source_eligibility.csv",
    "source_balanced_sampler_manifest.csv",
    "resolved_stage_loss_weights.csv",
    "loss_specific_gradient_matrix.csv",
    "sip_formula_unit_tests.json",
    "sip_weight_calibration.csv",
    "representer_parameter_manifest.csv",
    "representer_scale_checks.csv",
    "beta_hierarchy_checks.csv",
    "availability_mask_checks.csv",
    "source_learner_coefficients.csv",
    "integrativeness_diagnostics.csv",
    "anchor_free_discovery_coverage.csv",
    "matched_run_manifest.csv",
    "br2_staged_gradient_checks.json",
    "slurm_attempts.csv",
)

FINAL_REQUIRED_FILES = (
    "scar_casewise_metrics.csv",
    "scar_checkpoint_selection.csv",
    "scar_help_harm.csv",
    "scar_source_learner_coefficients.csv",
    "scar_proposal_mechanism_metrics.csv",
    "scar_deployment_subgroup_metrics.csv",
    "edema_casewise_metrics.csv",
    "edema_checkpoint_selection.csv",
    "edema_help_harm.csv",
    "edema_source_learner_coefficients.csv",
    "edema_proposal_mechanism_metrics.csv",
    "edema_deployment_subgroup_metrics.csv",
    "pathology_decision_matrix.csv",
    "br2_increment_matrix.csv",
    "sip_increment_matrix.csv",
    "deployment_subgroup_metrics.csv",
    "proposal_mechanism_metrics.csv",
    "casewise_metrics.csv",
    "subgroup_metrics.csv",
    "help_harm.csv",
    "claim_boundary.md",
    "controller_report.md",
    "completion_check.md",
    "mapper_report_final.md",
    "MANIFEST.md",
)

FORBIDDEN_ACTIVE_LOSS_SUBSTRINGS = (
    "refiner",
    "final_",
    "production_gate",
    "arbiter",
    "arbitration",
    "bounded_correction",
    "correction_opportunity",
    "prototype",
    "memory",
    "generic_dictionary",
)

TARGET_ACTIVE_LOSSES = {
    "scar": {
        "loss_scar_anchor_false_positive_suppression",
        "loss_scar_anchor_missed_lesion_recovery",
        "loss_scar_confirmation_proposal",
        "loss_scar_discovery_proposal",
        "loss_scar_proposal",
    },
    "edema": {
        "loss_edema_anchor_false_positive_suppression_t2_present",
        "loss_edema_anchor_missed_lesion_recovery_t2_present",
        "loss_edema_confirmation_proposal_t2_present",
        "loss_edema_discovery_proposal_t2_present",
        "loss_edema_proposal_t2_present_only",
    },
}

BR2_ACTIVE_LOSSES = {
    "loss_br2_source_l1_sparsity",
    "loss_br2_center_deviation_shrinkage",
    "loss_br2_selective_integration_penalty",
}


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in {"", None}:  # type: ignore[comparison-overlap]
        return default
    return float(value)


def require_files(result_root: Path, names: tuple[str, ...], errors: list[str]) -> None:
    for name in names:
        path = result_root / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing_or_empty:{name}")


def validate_center_inventory(result_root: Path, cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = read_csv(result_root / "center_modality_inventory.csv")
    expected = cfg["training_data"]["expected_center_observation_patterns"]
    if set(row.get("center", "") for row in rows) != set(expected):
        errors.append("center_inventory_centers_mismatch")
    train_total = 0
    val_total = 0
    for row in rows:
        center = row.get("center", "")
        if row.get("status") != "PASS":
            errors.append(f"center_inventory_status:{center}:{row.get('status')}")
        if row.get("source_semantics") != "metadata.center":
            errors.append(f"center_source_not_metadata_center:{center}")
        if row.get("availability_semantics") != "observation_set_not_training_source":
            errors.append(f"availability_used_as_source:{center}")
        if row.get("observation_set") != expected.get(center):
            errors.append(f"center_observation_set_mismatch:{center}")
        train_total += int(float(row.get("train_case_count", "0") or 0))
        val_total += int(float(row.get("val_case_count", "0") or 0))
    if train_total != int(cfg["training_data"]["train_case_count"]):
        errors.append(f"train_case_count:{train_total}")
    if val_total != int(cfg["training_data"]["validation_case_count"]):
        errors.append(f"validation_case_count:{val_total}")
    return errors


def validate_source_eligibility(result_root: Path) -> list[str]:
    errors: list[str] = []
    rows = read_csv(result_root / "pathology_source_eligibility.csv")
    if not rows:
        return ["empty_pathology_source_eligibility"]
    for row in rows:
        pathology = row.get("pathology", "")
        center = row.get("center", "")
        eligible = int(float(row.get("eligible_for_beta_sip_loss", "0") or 0))
        t2_present = int(float(row.get("t2_present", "0") or 0))
        if pathology == "edema" and not t2_present and eligible:
            errors.append(f"no_t2_edema_source_eligible:{center}:{row.get('representer')}")
    edema_eligible_centers = {
        row["center"]
        for row in rows
        if row.get("pathology") == "edema" and int(float(row.get("eligible_for_beta_sip_loss", "0") or 0))
    }
    if not edema_eligible_centers or not edema_eligible_centers <= {"CenterB", "CenterC"}:
        errors.append(f"edema_eligible_centers:{sorted(edema_eligible_centers)}")
    return errors


def validate_resolved_losses(result_root: Path, cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = read_csv(result_root / "resolved_stage_loss_weights.csv")
    expected_experiments = set(cfg["experiments"])
    if not rows:
        return ["empty_resolved_stage_loss_weights"]
    if {row.get("experiment", "") for row in rows} != expected_experiments:
        errors.append("resolved_loss_experiment_set_mismatch")
    for row in rows:
        name = row.get("loss_name", "")
        experiment = row.get("experiment", "")
        pathology = row.get("pathology", "")
        weight = as_float(row, "resolved_weight")
        if name in {"loss_pattern_sip_integrativeness", "loss_dictionary_entropy_coverage_load_balance"} and weight != 0.0:
            errors.append(f"legacy_sip_or_dictionary_nonzero:{experiment}:{name}")
        if name == "loss_no_t2_edema_safety" and weight != 0.0:
            errors.append(f"no_t2_edema_loss_nonzero:{experiment}")
        if weight == 0.0:
            continue
        if any(token in name for token in FORBIDDEN_ACTIVE_LOSS_SUBSTRINGS):
            errors.append(f"forbidden_active_loss:{experiment}:{name}")
        if name in BR2_ACTIVE_LOSSES:
            if not cfg["experiments"].get(experiment, {}).get("br2_enabled", False):
                errors.append(f"br2_loss_in_non_br2_experiment:{experiment}:{name}")
            if name == "loss_br2_selective_integration_penalty" and not cfg["experiments"].get(experiment, {}).get("sip_enabled", False):
                errors.append(f"sip_loss_in_no_sip_experiment:{experiment}")
            continue
        if name not in TARGET_ACTIVE_LOSSES.get(pathology, set()):
            errors.append(f"unauthorized_active_loss:{experiment}:{name}")
    return errors


def validate_static_mechanism_files(result_root: Path) -> list[str]:
    errors: list[str] = []
    for row in read_csv(result_root / "representer_parameter_manifest.csv"):
        if row.get("distinct_storage_status") != "PASS":
            errors.append(f"duplicate_representer_storage:{row.get('representer')}")
        if int(float(row.get("final_adapter_zero_initialized", "0") or 0)) != 1:
            errors.append(f"representer_final_not_zero:{row.get('representer')}")
    for row in read_csv(result_root / "representer_scale_checks.csv"):
        available = int(float(row.get("available", "0") or 0))
        pre_beta_rms = as_float(row, "pre_beta_rms")
        contribution = as_float(row, "contribution_rms_after_availability_mask")
        if available and abs(pre_beta_rms - 1.0) > 1.0e-4:
            errors.append(f"representer_rms_not_one:{row.get('case_pattern')}:{row.get('representer')}")
        if not available and contribution != 0.0:
            errors.append(f"missing_representer_nonzero:{row.get('case_pattern')}:{row.get('representer')}")
        if as_float(row, "initial_br2_delta_rms") > 1.0e-6:
            errors.append(f"br2_initial_delta_nonzero:{row.get('case_pattern')}:{row.get('representer')}")
        if int(float(row.get("initial_output_matches_minimal", "0") or 0)) != 1:
            errors.append(f"initial_output_not_minimal:{row.get('case_pattern')}:{row.get('representer')}")
    for row in read_csv(result_root / "beta_hierarchy_checks.csv"):
        if row.get("status") != "PASS":
            errors.append(f"beta_hierarchy_fail:{row.get('check')}:{row.get('pattern')}")
    for row in read_csv(result_root / "availability_mask_checks.csv"):
        required = [item for item in row.get("required_modalities", "").split(",") if item]
        pattern = row.get("observation_set", "")
        expected = int(
            ("LGE" not in required or "lge" in pattern)
            and ("T2" not in required or "t2" in pattern)
            and ("C0" not in required or "c0" in pattern)
        )
        if int(float(row.get("availability_mask", "0") or 0)) != expected:
            errors.append(f"availability_mask_mismatch:{pattern}:{row.get('representer')}")
    sip_tests = json.loads((result_root / "sip_formula_unit_tests.json").read_text(encoding="utf-8"))
    if sip_tests.get("status") != "PASS":
        errors.append("sip_formula_unit_tests_not_pass")
    if sip_tests.get("batch_average_gate_proxy") != "REJECTED":
        errors.append("sip_batch_proxy_not_rejected")
    staged = json.loads((result_root / "br2_staged_gradient_checks.json").read_text(encoding="utf-8"))
    if staged.get("status") != "PASS":
        errors.append("br2_staged_gradient_checks_not_pass")
    return errors


def validate_preflight_runtime(result_root: Path) -> list[str]:
    errors: list[str] = []
    sampler_rows = read_csv(result_root / "source_balanced_sampler_manifest.csv")
    if not sampler_rows:
        errors.append("empty_source_balanced_sampler_manifest")
    for row in sampler_rows:
        if row.get("training_source") != "metadata.center":
            errors.append(f"sampler_training_source:{row.get('pathology')}:{row.get('step')}")
        if str(row.get("availability_is_observation_set_not_source")) != "True":
            errors.append(f"sampler_availability_source_proxy:{row.get('pathology')}:{row.get('step')}")
    gradients = read_csv(result_root / "loss_specific_gradient_matrix.csv")
    if not gradients:
        errors.append("empty_loss_specific_gradient_matrix")
    for row in gradients:
        family = str(row.get("loss_family", "")).lower()
        if "logits_mean" in family:
            errors.append(f"logits_mean_gradient_proxy:{row.get('experiment')}:{row.get('loss_family')}")
        if str(row.get("forbidden_logits_mean_proxy")) != "True":
            errors.append(f"gradient_proxy_guard_missing:{row.get('experiment')}:{row.get('loss_family')}")
    return errors


def validate_sip_calibration(result_root: Path, *, final: bool) -> list[str]:
    errors: list[str] = []
    rows = read_csv(result_root / "sip_weight_calibration.csv")
    for pathology in ("scar", "edema"):
        selected = [
            row
            for row in rows
            if row.get("pathology") == pathology
            and row.get("status") == "PASS"
            and str(row.get("selected")) == "1"
            and str(row.get("formal_sip_run_allowed")) == "1"
        ]
        if final and len(selected) != 1:
            errors.append(f"sip_calibration_not_selected:{pathology}:{len(selected)}")
        if not final and selected:
            continue
    return errors


def validate_matched_runs(result_root: Path, cfg: dict[str, Any], *, final: bool) -> list[str]:
    errors: list[str] = []
    rows = read_csv(result_root / "matched_run_manifest.csv")
    expected = set(cfg["experiments"])
    by_experiment = {row.get("experiment", ""): row for row in rows}
    if set(by_experiment) != expected:
        errors.append("matched_run_experiment_set_mismatch")
    for experiment, spec in cfg["experiments"].items():
        row = by_experiment.get(experiment)
        if row is None:
            continue
        if int(float(row.get("optimizer_steps", "0") or 0)) != 400:
            errors.append(f"matched_run_optimizer_steps:{experiment}")
        if row.get("eval_steps") != "200,400":
            errors.append(f"matched_run_eval_steps:{experiment}:{row.get('eval_steps')}")
        if row.get("source_checkpoint_sha256") != cfg["source_checkpoint"]["sha256"]:
            errors.append(f"matched_run_checkpoint_sha:{experiment}")
        if final and row.get("runtime_status") != "TERMINAL_AGGREGATED_PASS":
            errors.append(f"matched_run_not_terminal:{experiment}:{row.get('runtime_status')}")
        if bool(spec.get("sip_enabled", False)) and row.get("only_difference_from_no_sip_pair") != "loss_br2_selective_integration_penalty_weight":
            errors.append(f"sip_pair_difference_not_isolated:{experiment}")
    for pathology in ("scar", "edema"):
        seeds = {row.get("seed_group") for row in rows if row.get("pathology") == pathology}
        samplers = {row.get("sampler_sequence_group") for row in rows if row.get("pathology") == pathology}
        if len(seeds) != 1:
            errors.append(f"seed_group_mismatch:{pathology}")
        if len(samplers) != 1:
            errors.append(f"sampler_group_mismatch:{pathology}")
        br2_rows = [row for row in rows if row.get("pathology") == pathology and row.get("br2_init_group") != "not_applicable"]
        if {row.get("warmup_step50_group") for row in br2_rows} != {f"{pathology}_shared_step50_warmup"}:
            errors.append(f"br2_warmup_group_mismatch:{pathology}")
    return errors


def validate_final_metrics(result_root: Path) -> list[str]:
    errors: list[str] = []
    for pathology in ("scar", "edema"):
        casewise = read_csv(result_root / f"{pathology}_casewise_metrics.csv")
        experiments = {f"{pathology}_minimal", f"{pathology}_br2_no_sip", f"{pathology}_br2_sip"}
        for experiment in experiments:
            for step in {"200", "400"}:
                rows = [row for row in casewise if row.get("experiment") == experiment and row.get("eval_step") == step]
                if len(rows) != 44:
                    errors.append(f"{pathology}_casewise_count:{experiment}:{step}:{len(rows)}")
        subgroup = read_csv(result_root / f"{pathology}_deployment_subgroup_metrics.csv")
        subgroup_names = {row.get("subgroup") for row in subgroup}
        for required in {"complete_trimodal", "worst_positive_center", "all_positive_centers"}:
            if required not in subgroup_names:
                errors.append(f"missing_{pathology}_subgroup:{required}")
        mechanism = read_csv(result_root / f"{pathology}_proposal_mechanism_metrics.csv")
        metric_names = {row.get("metric") for row in mechanism}
        for required in {"proposal_precision", "proposal_recall", "lesion_wise_recall", "anchor_missed_recovery", "false_positive_suppression"}:
            if required not in metric_names:
                errors.append(f"missing_{pathology}_mechanism_metric:{required}")
    decisions = read_csv(result_root / "pathology_decision_matrix.csv")
    decision_map = {row.get("decision_id"): row.get("decision") for row in decisions}
    allowed = {
        "scar_minimal": {"RETAIN", "RETIRE"},
        "scar_br2": {"RETAIN", "RETIRE", "NOT_APPLICABLE"},
        "scar_sip": {"RETAIN", "REMOVE", "NOT_APPLICABLE"},
        "edema_minimal": {"RETAIN", "RETIRE"},
        "edema_br2": {"RETAIN", "RETIRE", "NOT_APPLICABLE"},
        "edema_sip": {"RETAIN", "REMOVE", "NOT_APPLICABLE"},
    }
    for key, values in allowed.items():
        if decision_map.get(key) not in values:
            errors.append(f"missing_or_invalid_decision:{key}:{decision_map.get(key)}")
    return errors


def validate_slurm_and_completion(result_root: Path, *, final: bool) -> list[str]:
    errors: list[str] = []
    attempts = read_csv(result_root / "slurm_attempts.csv")
    if not attempts:
        errors.append("empty_slurm_attempts")
    if final:
        for row in attempts:
            state = row.get("state_at_record", "")
            evidence = row.get("completion_evidence", "")
            if state not in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "PREEMPTED"}:
                errors.append(f"slurm_attempt_not_terminal:{row.get('job_id')}:{state}")
            if any(token in evidence for token in MONITOR_TOKENS):
                errors.append(f"slurm_attempt_monitor_evidence:{row.get('job_id')}:{evidence}")
        for name in ("controller_report.md", "completion_check.md", "result.md"):
            path = result_root / name
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                for token in MONITOR_TOKENS:
                    if token in text:
                        errors.append(f"monitor_token_in_final_text:{name}:{token}")
    else:
        for row in attempts:
            if row.get("purpose", "").startswith("gpu_preflight") and row.get("formal_training_credit") != "0":
                errors.append(f"preflight_has_training_credit:{row.get('job_id')}")
    return errors


def validate_packet(result_root: Path, cfg: dict[str, Any], *, final: bool) -> list[str]:
    errors: list[str] = []
    require_files(result_root, STATIC_REQUIRED_FILES, errors)
    if final:
        require_files(result_root, FINAL_REQUIRED_FILES, errors)
    if errors:
        return errors
    errors.extend(validate_center_inventory(result_root, cfg))
    errors.extend(validate_source_eligibility(result_root))
    errors.extend(validate_resolved_losses(result_root, cfg))
    errors.extend(validate_static_mechanism_files(result_root))
    errors.extend(validate_preflight_runtime(result_root))
    errors.extend(validate_sip_calibration(result_root, final=final))
    errors.extend(validate_matched_runs(result_root, cfg, final=final))
    errors.extend(validate_slurm_and_completion(result_root, final=final))
    if final:
        errors.extend(validate_final_metrics(result_root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_minimal_decomposition.yaml")
    parser.add_argument("--result-root", default=str(DEFAULT_RESULT_ROOT.relative_to(REPO_ROOT)))
    parser.add_argument("--known-bad-root", default="")
    parser.add_argument("--preflight", action="store_true", help="Validate static/preflight gates but allow pending formal runs.")
    parser.add_argument("--write-status", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    final = not bool(args.preflight)
    errors = validate_packet(result_root, cfg, final=final)

    known_bad_errors: list[str] = []
    known_bad_rejected = True
    if args.known_bad_root:
        known_bad_errors = validate_packet(repo_path(args.known_bad_root), cfg, final=False)
        known_bad_rejected = bool(known_bad_errors)
        if not known_bad_rejected:
            errors.append("known_bad_packet_not_rejected")

    status = {
        "status": "PASS" if not errors else "FAIL",
        "mode": "final" if final else "preflight",
        "errors": errors,
        "known_bad_root": args.known_bad_root,
        "known_bad_rejected": known_bad_rejected,
        "known_bad_error_count": len(known_bad_errors),
        "known_bad_errors_sample": known_bad_errors[:24],
    }
    if args.write_status:
        write_json(result_root / "minimal_decomposition_validator_status.json", status)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Batch7 minimal decomposition validator passed ({status['mode']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
