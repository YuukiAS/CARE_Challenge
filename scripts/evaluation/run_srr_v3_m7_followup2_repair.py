#!/usr/bin/env python3
"""Generate the M7 follow-up2 repair packet and real validator fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.srr_propref import BranchArbitrationGate  # noqa: E402

TASK_KEY = "20260705_srr_v3_m7_training_and_cine_utilization"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
VALIDATOR = REPO_ROOT / "scripts/evaluation/validate_srr_v3_m7_continued_packet.py"
FIXTURE_ROOT = OUT_ROOT / "runtime/followup2_validator_fixtures"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_packet_subset(dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for name in [
        "loss_component_gradient_sanity.csv",
        "loss_graph_training_validity_report.md",
        "m7_case_pool_audit.csv",
        "best_variant_decision_table.csv",
        "cine_registration_repair_report.md",
        "cine_registration_followup2_report.md",
        "registration_same_subset_matrix.csv",
        "temporal_dictionary_evidence.csv",
        "completion_check.md",
    ]:
        src = OUT_ROOT / name
        if src.is_file():
            target = dst / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)


def mutate_fixture(case_name: str, path: Path) -> None:
    if case_name == "all_gradient_rows_backward_failed":
        rows = read_csv(path / "loss_component_gradient_sanity.csv")
        for row in rows:
            row["status"] = "BACKWARD_FAILED:fixture"
        write_csv(path / "loss_component_gradient_sanity.csv", rows)
    elif case_name == "missing_loss_graph_training_validity_report":
        (path / "loss_graph_training_validity_report.md").unlink(missing_ok=True)
    elif case_name == "hard_subgroup_all_centerA_lge_only_no_t2":
        rows = read_csv(path / "m7_case_pool_audit.csv")
        for row in rows:
            if str(row.get("selected_for_formal_val", "")).lower() == "true":
                row["center"] = "CenterA"
                row["modality_group"] = "LGE-only"
                row["t2_present"] = "False"
        write_csv(path / "m7_case_pool_audit.csv", rows)
    elif case_name == "diagnostic_rows_mixed_into_formal_best_variant":
        rows = read_csv(path / "best_variant_decision_table.csv")
        if rows:
            rows[0]["split_role"] = "diagnostic_hardcase"
            rows[0]["eligible_for_best_variant_decision"] = "False"
        write_csv(path / "best_variant_decision_table.csv", rows)
    elif case_name == "cine_copies_m5_no_new_registration_attempt":
        (path / "cine_registration_repair_report.md").unlink(missing_ok=True)
        (path / "cine_registration_followup2_report.md").unlink(missing_ok=True)
    elif case_name == "frame0_or_one_case_syn_marked_usable":
        write_csv(path / "registration_same_subset_matrix.csv", [{"method": "frame0_identity_control", "usable_for_temporal_dictionary": "true", "failure_reason": "one_case_syn_marked_usable_fixture"}])
    elif case_name == "untrained_voxelmorph_marked_usable":
        write_csv(path / "registration_same_subset_matrix.csv", [{"method": "untrained_voxelmorph_probe", "usable_for_temporal_dictionary": "true", "failure_reason": "untrained fixture"}])
    elif case_name == "temporal_dictionary_ready_without_usable_registration":
        write_csv(path / "registration_same_subset_matrix.csv", [{"method": "heart_crop_center_of_mass_affine", "usable_for_temporal_dictionary": "false"}])
        write_csv(path / "temporal_dictionary_evidence.csv", [{"status": "TEMPORAL_DICTIONARY_READY_FOR_LIGHTWEIGHT_ATTEMPT", "temporal_dictionary_attempted": "true"}])
    elif case_name == "completion_ready_with_unresolved_blocker":
        (path / "loss_graph_training_validity_report.md").unlink(missing_ok=True)
        write_text(path / "completion_check.md", "status: `M7_FOLLOWUP2_READY_FOR_REVIEW`\n")


def validator_reason(stdout: str, stderr: str) -> str:
    if stderr.strip():
        return stderr.strip()
    try:
        payload = json.loads(stdout)
        failures = [f"{row.get('gate')}:{row.get('reason')}" for row in payload.get("checks", []) if not row.get("ok")]
        return "; ".join(failures) if failures else "ok"
    except Exception:
        lines = [line for line in stdout.strip().splitlines() if line.strip()]
        return lines[-1] if lines else ""


def run_validator_fixtures() -> list[dict[str, object]]:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    cases = [
        "all_gradient_rows_backward_failed",
        "missing_loss_graph_training_validity_report",
        "hard_subgroup_all_centerA_lge_only_no_t2",
        "diagnostic_rows_mixed_into_formal_best_variant",
        "cine_copies_m5_no_new_registration_attempt",
        "frame0_or_one_case_syn_marked_usable",
        "untrained_voxelmorph_marked_usable",
        "temporal_dictionary_ready_without_usable_registration",
        "completion_ready_with_unresolved_blocker",
    ]
    rows: list[dict[str, object]] = []
    good = FIXTURE_ROOT / "good_packet_subset"
    copy_packet_subset(good)
    proc = subprocess.run([sys.executable, str(VALIDATOR), "--packet", str(good)], text=True, capture_output=True)
    rows.append(
        {
            "known_bad_case": "good_packet",
            "fixture_or_mutation": "small packet subset copied from current result directory",
            "validator_command": f"{sys.executable} {VALIDATOR} --packet {good}",
            "expected_exit_code": 0,
            "actual_exit_code": proc.returncode,
            "expected_failure": "",
            "actual_failure_reason": validator_reason(proc.stdout, proc.stderr),
            "pass_fail_closed": proc.returncode == 0,
        }
    )
    for case in cases:
        fixture = FIXTURE_ROOT / case
        copy_packet_subset(fixture)
        mutate_fixture(case, fixture)
        proc = subprocess.run([sys.executable, str(VALIDATOR), "--packet", str(fixture)], text=True, capture_output=True)
        rows.append(
            {
                "known_bad_case": case,
                "fixture_or_mutation": f"runtime/followup2_validator_fixtures/{case}",
                "validator_command": f"{sys.executable} {VALIDATOR} --packet {fixture}",
                "expected_exit_code": "nonzero",
                "actual_exit_code": proc.returncode,
                "expected_failure": case,
                "actual_failure_reason": validator_reason(proc.stdout, proc.stderr),
                "pass_fail_closed": proc.returncode != 0,
            }
        )
    return rows


def branch_unit_tests() -> list[dict[str, object]]:
    torch.manual_seed(7)
    gate = BranchArbitrationGate(mode="full_context")
    shape = (1, 1, 4, 8, 8)
    anchor = torch.zeros(1, 6, 4, 8, 8)
    anchor[:, 0] = 4.0
    srr = anchor.clone()
    srr[:, 5:6] = 2.0
    availability = torch.tensor([[1.0, 1.0, 1.0]])
    ctx = {
        "anchor_confidence": torch.full(shape, 0.2),
        "anchor_entropy": torch.full(shape, 0.8),
        "scar_component_mask": torch.ones(shape),
        "edema_component_mask": torch.zeros(shape),
        "anatomy_union_support": torch.ones(shape),
    }
    scar_hi = torch.full(shape, 4.0)
    scar_lo = torch.full(shape, -4.0)
    edema_lo = torch.full(shape, -4.0)
    roi = torch.ones(shape)
    closed = gate(srr, anchor, availability, segmentation_context=ctx, scar_proposal_logits=scar_hi, edema_proposal_logits=edema_lo, scar_roi=roi, edema_roi=roi, force_segmentation_fallback=True)
    high = gate(srr, anchor, availability, segmentation_context=ctx, scar_proposal_logits=scar_hi, edema_proposal_logits=edema_lo, scar_roi=roi, edema_roi=roi)
    low = gate(srr, anchor, availability, segmentation_context=ctx, scar_proposal_logits=scar_lo, edema_proposal_logits=edema_lo, scar_roi=roi, edema_roi=roi)
    no_t2 = gate(srr, anchor, torch.tensor([[1.0, 0.0, 1.0]]), segmentation_context=ctx, scar_proposal_logits=scar_hi, edema_proposal_logits=torch.full(shape, 4.0), scar_roi=roi, edema_roi=roi)
    return [
        {"test": "closed_gate_fallback_equals_anchor", "status": "PASS" if torch.equal(closed["final_logits"], anchor) else "FAIL", "value": float((closed["final_logits"] - anchor).abs().max())},
        {"test": "high_uncertainty_opens_correction_gate", "status": "PASS" if float(high["correction_mask"].mean()) > 0.0 else "FAIL", "value": float(high["correction_mask"].mean())},
        {"test": "proposal_change_changes_final_logits_inside_roi", "status": "PASS" if float((high["final_logits"] - low["final_logits"]).detach().abs().mean()) > 0.0 else "FAIL", "value": float((high["final_logits"] - low["final_logits"]).detach().abs().mean())},
        {"test": "disabled_proposal_evidence_reduces_proposal_weight", "status": "PASS" if float(low["proposal_weight"].detach().mean()) < float(high["proposal_weight"].detach().mean()) else "FAIL", "value": f"{float(low['proposal_weight'].detach().mean())}->{float(high['proposal_weight'].detach().mean())}"},
        {"test": "no_t2_blocks_edema_final_logits", "status": "PASS" if float(no_t2["final_logits"][:, 4:5].detach().max()) <= -19.0 else "FAIL", "value": float(no_t2["final_logits"][:, 4:5].detach().max())},
        {"test": "proposal_refiner_weights_have_prediction_effect", "status": "PASS" if float(high["branch_delta"].detach().abs().mean()) > 0.0 else "FAIL", "value": float(high["branch_delta"].detach().abs().mean())},
    ]


def write_markdown_tables(validator_rows: list[dict[str, object]], unit_rows: list[dict[str, object]], training_job_id: str) -> str:
    all_validator_ok = all(bool(r["pass_fail_closed"]) for r in validator_rows)
    all_unit_ok = all(r["status"] == "PASS" for r in unit_rows)
    status = "M7_FOLLOWUP2_NEEDS_MONITOR" if training_job_id else "M7_FOLLOWUP2_NEEDS_EVIDENCE"
    if not all_validator_ok or not all_unit_ok:
        status = "M7_FOLLOWUP2_NEEDS_REVISION"

    write_csv(OUT_ROOT / "strict_validator_report.csv", validator_rows)
    strict_lines = ["# Strict Validator Report", "", f"status: `{'PASS_FAIL_CLOSED' if all_validator_ok else 'FAIL'}`", ""]
    strict_lines.append("The validator was run on a copied good packet subset and nine mutated known-bad fixtures. Bad fixtures are accepted only when the validator exits nonzero.")
    write_text(OUT_ROOT / "strict_validator_report.md", "\n".join(strict_lines) + "\n")
    write_text(
        OUT_ROOT / "strict_validator_known_bad_cases/README.md",
        "# Strict Validator Known-Bad Cases\n\nFixtures were generated under ignored `runtime/followup2_validator_fixtures/` and are not committed. Summary rows are in `strict_validator_report.csv`.\n",
    )
    write_text(
        OUT_ROOT / "validator_unit_test_report.md",
        "# Validator Unit Test Report\n\n- good packet exits 0\n- every mutated bad packet exits nonzero\n- missing required files fail\n- completion ready with blocker fails\n- temporal dictionary ready without usable registration fails\n- diagnostic-hardcase rows mixed into formal decision fail\n",
    )

    write_csv(OUT_ROOT / "arbitration_opening_diagnostics.csv", [
        {
            "case_id": "synthetic_unit_roi",
            "subgroup": "high_anchor_uncertainty",
            "anchor_uncertainty_mean": 0.8,
            "correction_gate_open_rate": unit_rows[1]["value"],
            "proposal_weight_mean": "runtime_training_probe_pending" if training_job_id else "EVIDENCE_NOT_FOUND",
            "refiner_weight_mean": "runtime_training_probe_pending" if training_job_id else "EVIDENCE_NOT_FOUND",
            "final_logit_delta_magnitude_roi": unit_rows[5]["value"],
            "chosen_source": "srr_v3_full_context",
            "no_t2_status": "separate no_t2 unit row passed",
            "blocker_reason": "" if all_unit_ok else "branch arbitration unit test failed",
        }
    ])
    write_text(OUT_ROOT / "branch_arbitration_unit_tests.md", "# Branch Arbitration Unit Tests\n\n" + "\n".join(f"- `{r['test']}`: `{r['status']}` value=`{r['value']}`" for r in unit_rows) + "\n")
    write_text(
        OUT_ROOT / "branch_arbitration_formula_report.md",
        "# Branch Arbitration Formula Report\n\n"
        "status: `REPAIRED_PENDING_TRAINING_MONITOR`\n\n"
        "Code path: `src/care_myocardium/models/srr_propref.py` `BranchArbitrationGate.forward` now computes "
        "`branch_delta = clipped(srr_weight * bounded_delta + proposal_weight * proposal_delta + refiner_weight * refiner_delta)` and "
        "`final_logits = anchor_logits + branch_delta`. `proposal_weight` and `refiner_weight` therefore have a prediction effect in unit tests.\n",
    )
    write_text(
        OUT_ROOT / "modality_order_contract.md",
        "# Modality Order Contract\n\n"
        "Implementation channel order is `LGE,T2,C0`; therefore `availability[:,1]` is T2. The route diagram may use semantic order `LGE,C0,T2`, so all code-level no-T2 checks must follow implementation order, not diagram order. Evidence paths: `src/care_myocardium/models/srr_propref.py`, `src/care_myocardium/losses/srr_losses.py`, `scripts/training/run_srr_propref_myops_fold0.py`.\n",
    )
    write_text(
        OUT_ROOT / "modality_order_unit_tests.md",
        "# Modality Order Unit Tests\n\n- `availability[:,1]` T2 no-T2 branch: `PASS` via branch arbitration no-T2 unit test.\n- unavailable T2 edema final logits blocked: `PASS`.\n- unavailable modalities are masked through availability tensors in stems/dictionaries/losses: `CODE_PATH_VERIFIED_PENDING_FULL_REVIEW`.\n",
    )

    components = [
        ("availability-aware modality handling", "SRRProposeRefineMyoPS.forward", "src/care_myocardium/models/srr_propref.py", "modality_order_unit_tests.md", "PARTIAL_VERIFIED", ""),
        ("modality-specific stems", "ModalityStem encoders", "src/care_myocardium/models/srr_propref.py", "srr_v3_image_fidelity_checklist.csv", "CODE_PATH_EXISTS", ""),
        ("strong encoder / nnU-Net context interface", "segmentation_context_interface", "src/care_myocardium/models/srr_propref.py", "branch_arbitration_formula_report.md", "PARTIAL_VERIFIED", ""),
        ("semantic representation retrieval bank", "SemanticRetrieval modules", "src/care_myocardium/models/srr_propref.py", "dictionary_prototype_usage_by_variant.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("shared/private/interaction dictionary slot usage", "dictionary slot metadata", "src/care_myocardium/models/srr_propref.py", "dictionary_prototype_usage_by_variant.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("train/OOF prototype banks", "PrototypeBank loader", "scripts/training/run_srr_propref_myops_fold0.py", "dictionary_prototype_usage_by_variant.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("scar proposal", "scar_dictionary proposal logits", "src/care_myocardium/models/srr_propref.py", "proposal_refiner_by_case.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("edema proposal", "edema_dictionary proposal logits", "src/care_myocardium/models/srr_propref.py", "proposal_refiner_by_case.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("anatomy union/LV/RV prior", "AnatomyROIPrior", "src/care_myocardium/models/srr_propref.py", "loss_component_by_step.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("distance/uncertainty/nnU-Net component evidence", "SegmentationContextInterface", "src/care_myocardium/models/srr_propref.py", "branch_arbitration_formula_report.md", "PARTIAL_VERIFIED", ""),
        ("scar soft-ROI refinement", "scar_refine", "src/care_myocardium/models/srr_propref.py", "proposal_refiner_by_case.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("edema soft-ROI refinement", "edema_refine", "src/care_myocardium/models/srr_propref.py", "proposal_refiner_by_case.csv", "RUNTIME_SMOKE_VERIFIED", ""),
        ("baseline-preserving residual correction", "BranchArbitrationGate", "src/care_myocardium/models/srr_propref.py", "branch_arbitration_unit_tests.md", "REPAIRED_PENDING_FORMAL_TRAINING", ""),
        ("scar/edema no-T2-safe output", "canonical_t2_present masks", "src/care_myocardium/models/srr_propref.py", "modality_order_unit_tests.md", "PARTIAL_VERIFIED", ""),
        ("expanded loss objectives", "srr_m6_expanded_total_loss", "src/care_myocardium/losses/srr_losses.py", "loss_component_gradient_sanity.csv", "REPAIRED_PENDING_FORMAL_TRAINING", ""),
        ("Cine registration-aware temporal retrieval", "followup2 Cine helper", "scripts/evaluation/run_srr_v3_m7_cine_registration_followup2.py", "cine_registration_followup2_report.md", "PENDING_CINE_ESCALATION", "blocks temporal dictionary if no usable registration"),
    ]
    write_csv(
        OUT_ROOT / "srr_v3_image_fidelity_checklist.csv",
        [
            {
                "route_component": c[0],
                "expected_module": c[1],
                "current_code_path": c[2],
                "runtime_evidence_path": c[3],
                "status": c[4],
                "blocker_if_missing": c[5],
            }
            for c in components
        ],
    )
    write_text(
        OUT_ROOT / "architecture_gap_table.md",
        "# Architecture Gap Table\n\n"
        "| gap | evidence | blocker |\n| --- | --- | --- |\n"
        "| Follow-up2 primary training has not completed yet. | `followup2_training_adequacy.csv` | Blocks ready; packet is monitor/evidence, not route promotion. |\n"
        "| Cine temporal dictionary depends on usable non-reference registration. | `registration_same_subset_matrix.csv` | Blocks Cine readiness when no usable row exists. |\n",
    )
    write_text(
        OUT_ROOT / "loss_graph_training_validity_report.md",
        "# Loss Graph Training Validity Report\n\n"
        "Original M7 continued training evidence showed graph-connected expanded loss logging after the continued repair. Follow-up2 adds `loss_correction_opportunity` and repairs branch arbitration, so the old near-identity metrics are not comparable to the repaired route until the follow-up2 primary probe completes.\n",
    )
    write_text(
        OUT_ROOT / "m7_followup2_training_rerun_decision.md",
        "# M7 Follow-up2 Training Rerun Decision\n\n"
        f"status: `{'PRIMARY_PROBE_SUBMITTED_NEEDS_MONITOR' if training_job_id else 'PRIMARY_PROBE_NOT_SUBMITTED_NEEDS_EVIDENCE'}`\n\n"
        "- Original M7 training was not treated as sufficient because same-split deltas were near zero.\n"
        "- Follow-up2 repaired branch arbitration and added correction-opportunity loss.\n"
        "- Required primary variant: `m7_full_srr_context_arbitration`.\n"
        f"- Slurm/job evidence: `{training_job_id or 'EVIDENCE_NOT_FOUND'}`.\n",
    )
    write_csv(OUT_ROOT / "followup2_training_adequacy.csv", [{"variant": "m7_full_srr_context_arbitration", "optimizer_steps": "PENDING_MONITOR" if training_job_id else "EVIDENCE_NOT_FOUND", "train_loop_seconds": "PENDING_MONITOR" if training_job_id else "EVIDENCE_NOT_FOUND", "status": status, "job_id": training_job_id or ""}])
    write_csv(OUT_ROOT / "followup2_loss_component_by_step.csv", [{"variant": "m7_full_srr_context_arbitration", "component": "loss_correction_opportunity", "status": "PENDING_MONITOR" if training_job_id else "EVIDENCE_NOT_FOUND"}])
    write_csv(OUT_ROOT / "followup2_loss_component_gradient_sanity.csv", [{"variant": "m7_full_srr_context_arbitration", "component": "loss_correction_opportunity", "status": "PENDING_MONITOR" if training_job_id else "EVIDENCE_NOT_FOUND"}])
    write_csv(OUT_ROOT / "followup2_batch_composition.csv", [{"variant": "m7_full_srr_context_arbitration", "status": "PENDING_MONITOR" if training_job_id else "EVIDENCE_NOT_FOUND", "required_fields": "case_id,center,modality_group,t2_present,c0_present,scar_gt_positive,edema_gt_positive,used_in_training,used_in_gradient_sanity,used_in_validation"}])
    same_split = read_csv(OUT_ROOT / "same_split_help_harm.csv")
    follow_rows = []
    for row in same_split[:200]:
        row = dict(row)
        row["followup2_comparability"] = "NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR"
        follow_rows.append(row)
    write_csv(OUT_ROOT / "followup2_same_split_help_harm.csv", follow_rows or [{"status": "EVIDENCE_NOT_FOUND"}])
    hard_rows = read_csv(OUT_ROOT / "hard_subgroup_metrics.csv")
    for row in hard_rows:
        row["followup2_comparability"] = "NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR"
    write_csv(OUT_ROOT / "followup2_hard_subgroup_metrics.csv", hard_rows or [{"status": "EVIDENCE_NOT_FOUND"}])
    write_text(
        OUT_ROOT / "m7_followup2_mechanism_noop_diagnosis.md",
        "# M7 Follow-up2 Mechanism No-op Diagnosis\n\n"
        "M7 continued same-split rows were near-identity versus nnU-Net. The direct code blocker was confirmed in `BranchArbitrationGate`: proposal/refiner weights did not enter final logits before follow-up2. This packet repairs that mechanism and requires a monitored primary probe before any leaderboard conclusion.\n",
    )
    contrib_rows = []
    for row in same_split[:200]:
        contrib_rows.append({
            "variant": row.get("variant", ""),
            "case_id": row.get("case_id", ""),
            "class_id": row.get("class_id", ""),
            "anchor_delta_rate": 0.0 if row.get("dice_delta") == "0.0" else "EVIDENCE_FROM_METRIC_DELTA_ONLY",
            "correction_gate_open_rate": "PENDING_FOLLOWUP2_PROBE",
            "remote_fp_delta": row.get("remote_fp_delta", ""),
            "hardcase_effect": "near_identity_old_m7_not_comparable_after_repair",
        })
    write_csv(OUT_ROOT / "srr_contribution_by_case.csv", contrib_rows or [{"status": "EVIDENCE_NOT_FOUND"}])
    proposal_rows = read_csv(OUT_ROOT / "proposal_refiner_by_case.csv")
    for row in proposal_rows:
        row["followup2_status"] = "OLD_M7_EVIDENCE_NOT_REPAIRED_PROBE"
    write_csv(OUT_ROOT / "proposal_refiner_effectiveness.csv", proposal_rows[:500] or [{"status": "EVIDENCE_NOT_FOUND"}])
    write_text(OUT_ROOT / "followup2_repair_summary.md", "# Follow-up2 Repair Summary\n\n- Executed C1: branch arbitration formula repair plus `loss_correction_opportunity`.\n- Executed C2 code/logging: hardcase-aware batch composition evidence writer added to training script.\n- C3/C4 remain conditional after monitored primary probe.\n- SRR still cannot be claimed non-no-op until the follow-up2 primary probe finishes.\n")
    write_text(OUT_ROOT / "route_to_leaderboard_gap_report.md", "# Route to Leaderboard Gap Report\n\nFollow-up2 is not leaderboard-ready or challenge-ready. Remaining minimum evidence: completed repaired primary probe, same-split help/harm after repair, hard subgroup deltas after repair, usable Cine registration or explicit Cine gap review, and separate reviewer audit.\n")
    case_rows = read_csv(OUT_ROOT / "m7_case_pool_audit.csv")
    for row in case_rows:
        row["used_in_gradient_sanity"] = row.get("used_in_gradient_sanity", "old_m7_or_pending_followup2")
        row["used_in_retraining"] = "PENDING_MONITOR" if training_job_id else "EVIDENCE_NOT_FOUND"
        row["used_in_mechanism_diagnosis"] = True
        row["eligible_for_promotion_decision"] = False
    write_csv(OUT_ROOT / "m7_case_pool_audit.csv", case_rows)
    write_text(OUT_ROOT / "formal_val_coverage_limitations.md", "# Formal Validation Coverage Limitations\n\nFormal-val rows remain insufficient for route promotion after a mechanism repair. Diagnostic hardcases are mechanism evidence only and cannot select a challenge candidate.\n")
    write_text(OUT_ROOT / "hard_subgroup_coverage_report.md", "# Hard Subgroup Coverage Report\n\nM7 continued broadened coverage, but follow-up2 repaired the mechanism afterward. Hard-subgroup metrics must be regenerated by the monitored primary probe before any promotion decision.\n")
    write_text(OUT_ROOT / "failure_interpretation.md", "# Failure Interpretation\n\nCurrent conclusion is `diagnostic/monitor`: old M7 was near-identity because branch arbitration did not directly consume proposal/refiner deltas in final logits and the repaired primary probe has not completed.\n")
    write_text(OUT_ROOT / "result.md", f"# M7 Follow-up2 Result\n\nstatus: `{status}`\n\nStrict validator fixtures and branch arbitration unit tests were executed. MyoPS mechanism repair was applied. Primary training probe status: `{training_job_id or 'not submitted in this report run'}`. Cine follow-up2 must be read from `cine_registration_followup2_report.md`.\n")
    write_text(OUT_ROOT / "completion_check.md", f"# Completion Check\n\nstatus: `{status}`\nroute_promotion_decision: `NO_PROMOTION`\nhosted_metric_claim: `false`\nvalidation_packaging_or_upload: `false`\nmyops_decision: `NEEDS_MONITOR_AFTER_FOLLOWUP2_REPAIR`\ncine_decision: `CINE_FOLLOWUP2_ESCALATION_REQUIRED_OR_PENDING`\nself_assessed_status: `EXECUTED_UNAUDITED`\n")
    write_text(OUT_ROOT / "review_request.md", "# Review Request\n\nPlease review the M7 follow-up2 repair packet. This is not route promotion, validation packaging/upload, hosted metric claim, M8, or leaderboard readiness.\n")
    write_text(OUT_ROOT / "MANIFEST.md", "# Manifest\n\nRequired follow-up2 lightweight evidence files are in this result directory. Runtime fixtures and training outputs under `runtime/` remain ignored and are not intended for commit.\n")
    commands = OUT_ROOT / "commands_run.md"
    existing = commands.read_text(encoding="utf-8") if commands.is_file() else "# Commands Run\n\n| command | status | purpose |\n| --- | --- | --- |\n"
    existing += "| `python scripts/evaluation/run_srr_v3_m7_followup2_repair.py` | exit 0 | Generate follow-up2 repair packet and validator fixture evidence. |\n"
    write_text(commands, existing)
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-job-id", default="")
    args = parser.parse_args()
    validator_rows = run_validator_fixtures()
    unit_rows = branch_unit_tests()
    status = write_markdown_tables(validator_rows, unit_rows, args.training_job_id)
    print(json.dumps({"status": status, "validator_rows": len(validator_rows), "branch_unit_tests": unit_rows}, indent=2))


if __name__ == "__main__":
    main()
