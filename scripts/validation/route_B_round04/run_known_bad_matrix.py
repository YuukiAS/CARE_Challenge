#!/usr/bin/env python3
"""Run Route B Round04 known-bad fixture matrices against a stage validator."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml


PYTHON = Path("/users/a/e/aereinh/CARE/envs/env_CARE/bin/python")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mutate_b0(root: Path, mutation: str) -> None:
    mapping = {
        "STALE_PLANNING_BINDING": ("source_fingerprint_audit.json", ("origin_route_B", "bad")),
        "PLANNING_SOURCE_UNREADABLE": ("source_fingerprint_audit.json", ("source_blobs", {"missing.py": ""})),
        "PLANNING_SNAPSHOT_INCOMPLETE": ("planning_snapshot_gate_receipt.json", ("materialization_receipt_status", "FAIL")),
        "PLANNING_SNAPSHOT_HASH_MISMATCH": ("planning_snapshot_gate_receipt.json", ("hash_audit_status", "FAIL")),
        "CURRENT_REREVIEW_MISSING_OR_NOT_READY": ("planning_snapshot_gate_receipt.json", ("critic_token", "ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION")),
        "CURRENT_HANDOFF_MISSING": ("planning_snapshot_gate_receipt.json", ("manifest_status", "FAIL")),
        "CURRENT_COORDINATOR_RECEIPT_MISSING_OR_STALE": ("completion.json", ("completion_token", "STALE")),
        "DISALLOWED_MAIN_DESCENDANT_PATH": ("planning_snapshot_gate_receipt.json", ("descendant_diff_audit_status", "FAIL")),
        "ROUTE_EVIDENCE_REF_MISMATCH": ("source_fingerprint_audit.json", ("expected_route_B", "bad")),
        "MANIFEST_HASH_MISMATCH": ("manifest_freeze_receipt.json", ("primary_case_count", 0)),
        "ANATOMY_TARGET_LABEL_ROUNDTRIP_FAILED": ("label_target_audit.json", ("roundtrip_pass", False)),
        "SAME_SPLIT_BASELINE_MISSING": ("same_split_baseline_receipt.json", ("status", "FAIL")),
        "VALIDATOR_MATRIX_INCOMPLETE": ("validator_fixture_index.json", ("fixture_count", 0)),
    }
    if mutation not in mapping:
        raise KeyError(f"unsupported B0 mutation {mutation}")
    filename, (key, value) = mapping[mutation]
    path = root / filename
    payload = load_json(path)
    payload[key] = value
    write_json(path, payload)


def mutate_csv(path: Path, row_key: str, row_value: str, target_key: str, target_value: str) -> None:
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []
    if target_key not in fieldnames:
        fieldnames.append(target_key)
    for row in rows:
        if row.get(row_key) == row_value:
            row[target_key] = target_value
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def mutate_b1(root: Path, mutation: str) -> None:
    if mutation == "PURE_MYOCARDIUM_UNION_TARGET":
        path = root / "anatomy_target_roundtrip.json"
        payload = load_json(path)
        payload["compact_union_labels"] = [1]
        write_json(path, payload)
        return
    if mutation == "ANATOMY_MICRO_OVERFIT_INADEQUATE":
        mutate_csv(root / "training_adequacy.csv", "stage", "B1", "train_loop_seconds", "1.0")
        return
    if mutation == "ROUTED_ANATOMY_GRADIENT_MISSING":
        mutate_csv(root / "anatomy_gradient_receipt.csv", "branch", "routed", "grad_l1", "0.0")
        return
    if mutation == "LATERAL_ANATOMY_GRADIENT_MISSING":
        mutate_csv(root / "anatomy_gradient_receipt.csv", "branch", "lateral", "grad_l1", "0.0")
        return
    if mutation == "ANCHOR_SUPPORT_FLOOR_BECAME_FINAL_BASE":
        mutate_csv(root / "anatomy_intervention_receipt.csv", "intervention", "anchor_support_floor", "became_final_base", "True")
        return
    if mutation == "SAVE_RELOAD_MISMATCH":
        path = root / "save_reload_report.json"
        payload = load_json(path)
        payload["status"] = "FAIL"
        payload["reload_max_abs_diff"] = 1.0
        write_json(path, payload)
        return
    raise KeyError(f"unsupported B1 mutation {mutation}")


def mutate_b2(root: Path, mutation: str) -> None:
    if mutation == "NNUNET_ONLY_BYPASS":
        path = root / "tensor_contract.json"
        payload = load_json(path)
        payload["scale_channels"] = [32]
        write_json(path, payload)
        return
    if mutation == "DISCONNECTED_RETRIEVAL_PROPOSAL_REFINER":
        path = root / "tensor_contract.json"
        payload = load_json(path)
        payload["route_b_owned_changed_logit_l1"] = 0.0
        write_json(path, payload)
        return
    if mutation == "INVALID_SLOT_WEIGHT_NONZERO":
        path = root / "tensor_contract.json"
        payload = load_json(path)
        payload["invalid_weight_max"] = 0.5
        write_json(path, payload)
        return
    if mutation == "PATTERN_SIP_ALIAS_OR_NO_GRADIENT":
        mutate_csv(root / "forward_gradient_intervention.csv", "component", "myops_final_logits", "grad_l1", "0.0")
        return
    if mutation == "FAKE_CINEMA_SOURCE_OR_WRONG_SHA":
        path = root / "cinema_source_fidelity.json"
        payload = load_json(path)
        payload["weight_sha256_observed"] = "bad"
        write_json(path, payload)
        return
    if mutation == "DIRECT_VELOCITY_AS_DISPLACEMENT":
        path = root / "registration_temporal_smoke.json"
        payload = load_json(path)
        payload["registration_integration_steps"] = 0
        write_json(path, payload)
        return
    if mutation == "TEMPORAL_REQUIRED_INPUT_UNCONSUMED":
        path = root / "registration_temporal_smoke.json"
        payload = load_json(path)
        payload["temporal_required_fields"] = ["reference_logits"]
        write_json(path, payload)
        return
    if mutation == "OFFICIAL_LABEL_ROUNDTRIP_FAILED":
        mutate_csv(root / "forward_gradient_intervention.csv", "component", "no_t2_edema_guard", "delta_abs_max", "1.0")
        return
    if mutation == "LEGACY_ROUND03_WRAPPER_BYPASS":
        path = root / "completion.json"
        payload = load_json(path)
        payload["completion_token"] = "ROUTE_B_ROUND03_B2_IMPLEMENTATION_GATE_PASSED"
        write_json(path, payload)
        return
    raise KeyError(f"unsupported B2 mutation {mutation}")


def mutate_b3(root: Path, mutation: str) -> None:
    if mutation == "ROUND03_B3_GLOBAL_STOP_REUSED":
        path = root / "completion.json"
        payload = load_json(path)
        payload["completion_token"] = "ROUTE_B_ROUND03_B3_GLOBAL_STOP"
        write_json(path, payload)
        return
    if mutation == "SAMPLER_CONTRACT_MISMATCH":
        path = root / "sampler_receipt.json"
        payload = load_json(path)
        payload["sampler_contract"] = "wrong_split"
        write_json(path, payload)
        return
    if mutation == "FORMAL_TRAINING_INADEQUATE":
        mutate_csv(root / "training_adequacy.csv", "stage", "B3", "train_loop_seconds", "1.0")
        return
    if mutation == "INVALID_SLOT_WEIGHT_NONZERO":
        mutate_csv(root / "router_slot_evidence.csv", "slot", "missing_T2", "max_weight", "0.25")
        return
    if mutation == "NO_T2_EDEMA_NONZERO":
        mutate_csv(root / "no_t2_safety.csv", "case_subset", "missing_T2", "edema_delta_abs_max", "1.0")
        return
    if mutation == "ROUTER_FAMILY_GRADIENT_MISSING":
        mutate_csv(root / "pattern_sip_gradient.csv", "component", "route_b_myops_representation", "grad_l1", "0.0")
        return
    if mutation == "LEARNED_ANATOMY_NONFINITE_OR_CONSTANT":
        mutate_csv(root / "learned_anatomy_metrics.csv", "component", "learned_representation", "std", "0.0")
        return
    if mutation == "B3_FULL_ROUTE_NEGATIVE_TOKEN_FORBIDDEN":
        path = root / "completion.json"
        payload = load_json(path)
        payload["completion_token"] = "ROUTE_B_NEGATIVE"
        write_json(path, payload)
        return
    raise KeyError(f"unsupported B3 mutation {mutation}")


def mutate_b7(root: Path, mutation: str) -> None:
    if mutation == "FAKE_CINEMA_SOURCE_OR_WRONG_SHA":
        path = root / "cinema_provenance.json"
        payload = load_json(path)
        payload["weight_sha256_observed"] = "bad"
        write_json(path, payload)
        return
    if mutation == "CINEMA_LICENSE_OR_COMMIT_MISSING":
        path = root / "cinema_provenance.json"
        payload = load_json(path)
        payload["license_or_commit_recorded"] = False
        payload["code_commit"] = ""
        write_json(path, payload)
        return
    if mutation == "PRETRAINED_RANDOM_ARCHITECTURE_MISMATCH":
        path = root / "pretrained_random_match_receipt.json"
        payload = load_json(path)
        payload["architecture_match"] = False
        write_json(path, payload)
        return
    if mutation == "DOWNSTREAM_INITIALIZATION_MISMATCH":
        path = root / "pretrained_random_match_receipt.json"
        payload = load_json(path)
        payload["downstream_initialization_match"] = False
        write_json(path, payload)
        return
    if mutation == "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH":
        mutate_csv(root / "adapter_training_adequacy.csv", "source", "official_pretrained", "train_loop_seconds", "1.0")
        return
    if mutation == "SOURCE_INITIALIZATION_NOT_ONLY_DIFFERENCE":
        path = root / "pretrained_random_match_receipt.json"
        payload = load_json(path)
        payload["source_initialization_only_difference"] = False
        write_json(path, payload)
        return
    if mutation == "SELECTED_CHECKPOINT_NOT_RELOADED":
        path = root / "selected_checkpoint_reload.json"
        payload = load_json(path)
        payload["status"] = "FAIL"
        write_json(path, payload)
        return
    if mutation == "INTERNAL_SMALL_WRAPPER_USED_AS_OFFICIAL":
        path = root / "cinema_provenance.json"
        payload = load_json(path)
        payload["source_alias"] = "internal_small_wrapper"
        write_json(path, payload)
        return
    raise KeyError(f"unsupported B7 mutation {mutation}")


def mutate_b4(root: Path, mutation: str) -> None:
    if mutation == "OOF_CURRENT_CASE_LEAKAGE":
        path = root / "prototype_leakage_audit.json"
        payload = load_json(path)
        payload["current_case_leakage"] = True
        write_json(path, payload)
        return
    if mutation == "OOF_VALIDATION_OR_TEST_LEAKAGE":
        path = root / "prototype_leakage_audit.json"
        payload = load_json(path)
        payload["validation_or_test_leakage"] = True
        write_json(path, payload)
        return
    if mutation == "BOOTSTRAP_OR_EMA_FORMAL_BANK":
        mutate_csv(root / "prototype_bank_inventory.csv", "bank", "scar_positive", "bootstrap", "True")
        return
    if mutation == "NO_T2_EDEMA_NEGATIVE":
        path = root / "hard_negative_queue_receipt.json"
        payload = load_json(path)
        payload["edema_safe_negative_t2_present_only"] = False
        write_json(path, payload)
        return
    if mutation == "PROTOTYPE_SIMILARITY_DISCONNECTED":
        mutate_csv(root / "proposal_metrics.csv", "target", "scar", "similarity_connected", "False")
        return
    if mutation == "CONSTANT_PROPOSAL":
        mutate_csv(root / "proposal_metrics.csv", "target", "scar", "constant", "True")
        return
    if mutation == "HARD_ROI_DELETION":
        path = root / "hard_negative_queue_receipt.json"
        payload = load_json(path)
        payload["hard_roi_deletion"] = True
        write_json(path, payload)
        return
    if mutation == "WEAK_VALID_PROPOSAL_PREMATURE_STOP":
        mutate_csv(root / "training_adequacy.csv", "stage", "B4", "train_loop_seconds", "1.0")
        return
    raise KeyError(f"unsupported B4 mutation {mutation}")


def mutate_b5(root: Path, mutation: str) -> None:
    if mutation == "SHARED_UNDIFFERENTIATED_REFINER":
        mutate_csv(root / "edema_refiner_metrics.csv", "refiner", "edema", "separate_refiner", "False")
        return
    if mutation == "REFINER_FINAL_EFFECT_ZERO":
        mutate_csv(root / "refiner_final_effect.csv", "target", "scar", "final_effect_l1", "0.0")
        return
    if mutation == "PROPOSAL_TO_FINAL_RETENTION_FAILED":
        mutate_csv(root / "proposal_to_final_retention.csv", "target", "scar", "retention", "0.0")
        return
    if mutation == "SCAR_REMOTE_FP_REGRESSION":
        mutate_csv(root / "remote_fp_and_component_matrix.csv", "target", "scar", "remote_fp_regression", "True")
        return
    if mutation == "NO_T2_EDEMA_NONZERO":
        mutate_csv(root / "no_t2_safety.csv", "case_subset", "missing_T2", "edema_delta_abs_max", "1.0")
        return
    if mutation == "HARD_ROI_DELETION":
        mutate_csv(root / "proposal_to_final_retention.csv", "target", "scar", "hard_roi_deleted", "True")
        return
    if mutation == "WEAK_B4_CONTROL_MISSING":
        parent = root.parent / "B4" / "completion.json"
        if parent.is_file():
            parent.unlink()
        else:
            marker = root / "completion.json"
            payload = load_json(marker)
            payload["b4_control_missing"] = True
            write_json(marker, payload)
        return
    if mutation == "WEAK_FAITHFUL_REFINER_PREMATURE_STOP":
        mutate_csv(root / "training_adequacy.csv", "stage", "B5", "train_loop_seconds", "1.0")
        return
    raise KeyError(f"unsupported B5 mutation {mutation}")


def mutate_b8(root: Path, mutation: str) -> None:
    if mutation == "DIRECT_VELOCITY_AS_DISPLACEMENT":
        path = root / "registration_training_adequacy.json"
        payload = load_json(path)
        payload["uses_direct_velocity_as_displacement"] = True
        write_json(path, payload)
        return
    if mutation == "SCALING_SQUARING_STEPS_NOT_SEVEN":
        path = root / "registration_training_adequacy.json"
        payload = load_json(path)
        payload["integration_steps"] = 6
        write_json(path, payload)
        return
    if mutation == "PROXY_JACOBIAN":
        path = root / "jacobian_histograms.json"
        payload = load_json(path)
        payload["proxy_jacobian"] = True
        payload["source"] = "intensity_residual_proxy"
        write_json(path, payload)
        return
    if mutation == "INVERSE_CONSISTENCY_MISSING":
        mutate_csv(root / "inverse_consistency.csv", "case_id", "Case1001", "composition_checked", "False")
        return
    if mutation == "SYN_OUTPUT_COPIED_OR_PROXY":
        mutate_csv(root / "real_syn_control.csv", "case_id", "Case1001", "copied_or_proxy", "True")
        return
    if mutation == "PAIR_AS_CASE_AGGREGATION":
        mutate_csv(root / "registration_case_full_gate.csv", "case_id", "Case1001", "pair_as_case_aggregation", "True")
        return
    if mutation == "FULL_DENOMINATOR_MISSING":
        mutate_csv(root / "registration_case_full_gate.csv", "case_id", "Case1001", "full_denominator_present", "False")
        return
    if mutation == "SELECTED_REGISTRATION_NOT_RELOADED":
        path = root / "selected_checkpoint_reload.json"
        payload = load_json(path)
        payload["status"] = "FAIL"
        write_json(path, payload)
        return
    if mutation == "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME":
        path = root / "registration_training_adequacy.json"
        payload = load_json(path)
        payload["train_loop_seconds"] = 1.0
        write_json(path, payload)
        decision = root / "registration_method_decision.json"
        decision_payload = load_json(decision)
        decision_payload["decision"] = "CINE_REGISTRATION_BLOCKER"
        decision_payload["learned_runtime_faithful"] = False
        write_json(decision, decision_payload)
        return
    raise KeyError(f"unsupported B8 mutation {mutation}")


def mutate_b6(root: Path, mutation: str) -> None:
    if mutation == "SAME_SPLIT_BASELINE_MISSING":
        path = root / "fresh_force_evaluation_receipt.json"
        payload = load_json(path)
        payload["same_split_baseline_status"] = "FAIL"
        write_json(path, payload)
        return
    if mutation == "FRESH_FORCE_EVALUATION_MISSING":
        path = root / "fresh_force_evaluation_receipt.json"
        payload = load_json(path)
        payload["fresh_force_evaluation"] = False
        write_json(path, payload)
        return
    if mutation == "SCAR_POSITIVE_ROWS_MISSING":
        mutate_csv(root / "casewise_help_harm.csv", "scar_positive", "True", "scar_positive", "False")
        mutate_csv(root / "hard_subgroup_matrix.csv", "subgroup", "scar_positive", "row_count", "0")
        return
    if mutation == "T2_PRESENT_EDEMA_POSITIVE_ROWS_MISSING":
        mutate_csv(root / "casewise_help_harm.csv", "t2_edema_positive", "True", "t2_edema_positive", "False")
        mutate_csv(root / "hard_subgroup_matrix.csv", "subgroup", "t2_present_edema_positive", "row_count", "0")
        return
    if mutation == "NO_T2_SAFETY_ROWS_MISSING":
        mutate_csv(root / "casewise_help_harm.csv", "no_t2", "True", "no_t2", "False")
        mutate_csv(root / "hard_subgroup_matrix.csv", "subgroup", "no_t2_safety", "row_count", "0")
        return
    if mutation == "CENTERB_OR_CENTERC_ROWS_MISSING":
        mutate_csv(root / "casewise_help_harm.csv", "center", "CenterB", "center", "CenterA")
        mutate_csv(root / "casewise_help_harm.csv", "center", "CenterC", "center", "CenterA")
        mutate_csv(root / "hard_subgroup_matrix.csv", "subgroup", "CenterB", "row_count", "0")
        mutate_csv(root / "hard_subgroup_matrix.csv", "subgroup", "CenterC", "row_count", "0")
        return
    if mutation == "EMPTY_GT_COUNTED_AS_HELP":
        mutate_csv(root / "casewise_help_harm.csv", "case_id", "Case1002", "empty_gt_counted_as_help", "True")
        return
    if mutation == "SUMMARY_MISNAMED_AS_ABLATION":
        path = root / "fresh_force_evaluation_receipt.json"
        payload = load_json(path)
        payload["summary_type"] = "ablation"
        write_json(path, payload)
        return
    if mutation == "SELECTED_CHECKPOINT_NOT_RELOADED":
        path = root / "selected_checkpoint_reload.json"
        payload = load_json(path)
        payload["status"] = "FAIL"
        write_json(path, payload)
        return
    if mutation == "FINAL_OUTPUT_INTERVENTION_ZERO_OR_MISSING":
        mutate_csv(root / "myops_intervention_matrix.csv", "component", "final_scar_logits", "final_output_delta_l1", "0.0")
        mutate_csv(root / "myops_intervention_matrix.csv", "component", "final_edema_logits", "final_output_delta_l1", "0.0")
        return
    if mutation == "PROXY_METRIC_AS_HOSTED":
        mutate_csv(root / "casewise_help_harm.csv", "case_id", "Case1002", "metric_scope", "hosted")
        return
    raise KeyError(f"unsupported B6 mutation {mutation}")


def mutate_b10(root: Path, mutation: str) -> None:
    if mutation == "EARLY_TERMINAL_BRANCH_UNREACHABLE":
        path = root / "terminal_branch_coverage.json"
        payload = load_json(path)
        payload["early_terminal_branches_reachable"] = False
        write_json(path, payload)
        return
    if mutation == "B1_FAILURE_FINALIZER_NOT_LAUNCHED":
        path = root / "terminal_branch_coverage.json"
        payload = load_json(path)
        payload["b1_failure_finalizer_launch_covered"] = False
        write_json(path, payload)
        return
    if mutation == "B2_EXTERNAL_BLOCKER_FINALIZER_NOT_LAUNCHED":
        path = root / "terminal_branch_coverage.json"
        payload = load_json(path)
        payload["b2_external_blocker_finalizer_launch_covered"] = False
        write_json(path, payload)
        return
    if mutation == "B7_BLOCKER_FINALIZER_NOT_LAUNCHED":
        path = root / "terminal_branch_coverage.json"
        payload = load_json(path)
        payload["b7_blocker_finalizer_launch_covered"] = False
        write_json(path, payload)
        return
    if mutation == "B8_REGISTRATION_BLOCKER_FINALIZER_NOT_LAUNCHED":
        path = root / "terminal_branch_coverage.json"
        payload = load_json(path)
        payload["b8_registration_blocker_finalizer_launch_covered"] = False
        payload["b9_absence_justified"] = False
        write_json(path, payload)
        return
    if mutation == "TIMEOUT_PREEMPTION_CANCELLED_LOSER_NOT_ACCOUNTED":
        path = root / "terminal_registry_snapshot.json"
        payload = load_json(path)
        payload["terminal_accounting"] = [row for row in payload.get("terminal_accounting", []) if str(row.get("job_id")) != "59548314"]
        write_json(path, payload)
        return
    if mutation == "SUCCESSFUL_B6_B9_NOT_ACCOUNTED":
        mutate_csv(root / "training_adequacy.csv", "stage", "B9", "status", "MISSING")
        path = root / "terminal_branch_coverage.json"
        payload = load_json(path)
        payload["b6_terminal_accounted"] = False
        write_json(path, payload)
        return
    if mutation == "PENDING_OR_RUNNING_PRESENTED_AS_COMPLETE":
        path = root / "terminal_registry_snapshot.json"
        payload = load_json(path)
        rows = payload.get("terminal_accounting", [])
        if rows:
            rows[-1]["state"] = "RUNNING"
            rows[-1]["terminal_accounted"] = False
        write_json(path, payload)
        return
    if mutation == "AGGREGATION_MISSING_OR_NONZERO":
        path = root / "finalizer_state.json"
        payload = load_json(path)
        payload["aggregation_command_exit_code"] = 2
        write_json(path, payload)
        return
    if mutation == "SUPERSEDED_RECEIPT_NOT_RECONCILED":
        path = root / "terminal_registry_snapshot.json"
        payload = load_json(path)
        payload["superseded_attempts_reconciled"] = False
        write_json(path, payload)
        return
    if mutation == "CONTROLLER_PUSH_OR_REVIEW_AUTHORITY_VIOLATION":
        path = root / "finalizer_state.json"
        payload = load_json(path)
        payload.setdefault("forbidden_actions", {})["push"] = True
        write_json(path, payload)
        return
    if mutation == "HEAVY_ARTIFACT_TRACKED":
        path = root / "heavy_artifact_scan.json"
        payload = load_json(path)
        payload["status"] = "FAIL"
        payload["tracked_heavy_artifacts"] = [{"path": "results/route_B/round04/heavy.pth", "bytes": 1}]
        write_json(path, payload)
        return
    if mutation == "VALIDATOR_FILE_EXISTENCE_ONLY":
        path = root / "validator_packet_report.json"
        payload = load_json(path)
        payload["semantic_checks_performed"] = False
        payload["only_file_existence"] = True
        write_json(path, payload)
        return
    raise KeyError(f"unsupported B10 mutation {mutation}")


def validator_command(validator: str, input_dir: Path, report: Path, token: str) -> list[str]:
    return [
        str(PYTHON),
        validator,
        "--strict",
        "--input",
        str(input_dir),
        "--report",
        str(report),
        "--require-token",
        token,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--validator", required=True)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--source-input", type=Path)
    args = parser.parse_args()

    matrix = yaml.safe_load(args.matrix.read_text(encoding="utf-8"))
    fixtures = matrix.get("fixtures", [])
    source_input = args.source_input or Path(matrix["source_input"])
    token = str(matrix["require_token"])
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"route_B_round04_{args.stage}_known_bad_") as tmpdir:
        tmp_root = Path(tmpdir)
        for fixture in fixtures:
            name = str(fixture["name"])
            expected_key = str(fixture["expected_failure_key"])
            case_dir = tmp_root / name
            shutil.copytree(source_input, case_dir)
            if args.stage == "B0":
                mutate_b0(case_dir, expected_key)
            elif args.stage == "B1":
                mutate_b1(case_dir, expected_key)
            elif args.stage == "B2":
                mutate_b2(case_dir, expected_key)
            elif args.stage == "B3":
                mutate_b3(case_dir, expected_key)
            elif args.stage == "B4":
                mutate_b4(case_dir, expected_key)
            elif args.stage == "B5":
                mutate_b5(case_dir, expected_key)
            elif args.stage == "B6":
                mutate_b6(case_dir, expected_key)
            elif args.stage == "B7":
                mutate_b7(case_dir, expected_key)
            elif args.stage == "B8":
                mutate_b8(case_dir, expected_key)
            elif args.stage == "B10":
                mutate_b10(case_dir, expected_key)
            else:
                raise KeyError(f"unsupported stage {args.stage}")
            report_path = case_dir / "validator_report.json"
            proc = subprocess.run(
                validator_command(args.validator, case_dir, report_path, token),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            payload = load_json(report_path) if report_path.is_file() else {}
            failure_keys = set(payload.get("failure_keys", []))
            passed = proc.returncode == int(fixture.get("expected_validator_exit", 1)) and expected_key in failure_keys
            rows.append(
                {
                    "name": name,
                    "expected_failure_key": expected_key,
                    "validator_exit": proc.returncode,
                    "failure_keys": sorted(failure_keys),
                    "passed": passed,
                }
            )
    ok = all(row["passed"] for row in rows) and len(rows) == int(matrix.get("expected_fixture_count", len(rows)))
    report = {
        "status": "PASS" if ok else "FAIL",
        "stage": args.stage,
        "fixture_count": len(rows),
        "rows": rows,
    }
    write_json(args.report, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
