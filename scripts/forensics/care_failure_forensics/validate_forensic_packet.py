#!/usr/bin/env python3
"""Strict validator for the CARE failure-forensics packet.

The validator is intentionally honest: a packet may be readable and useful while
still returning NEEDS_REPAIR when required diagnostic waves were not completed.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path


REQUIRED_FILES = [
    "controller_context.json",
    "controller_ledger.csv",
    "controller_bootstrap_snapshot.md",
    "task_scope_receipt.json",
    "source_read_manifest.csv",
    "evidence_inventory.csv",
    "checkpoint_inventory.csv",
    "prediction_inventory.csv",
    "external_local_repo_inventory.csv",
    "path_resolution_log.jsonl",
    "hash_manifest.csv",
    "data_case_manifest.csv",
    "data_center_modality_matrix.csv",
    "label_availability_matrix.csv",
    "label_semantics_contract.json",
    "official_internal_label_mapping.csv",
    "split_integrity_report.json",
    "spatial_geometry_audit.csv",
    "pathology_prevalence_summary.csv",
    "lesion_component_summary.csv",
    "data_truth_report.md",
    "reference_metric_known_bad_report.json",
    "metric_cross_implementation_report.json",
    "metric_semantics_validator_report.json",
    "model_lineage.csv",
    "experiment_lineage.csv",
    "historical_results_matrix.csv",
    "historical_failure_evidence.csv",
    "result_comparability_matrix.csv",
    "stale_evidence_report.md",
    "architecture_fidelity_matrix.csv",
    "loss_to_parameter_trace.csv",
    "component_final_output_effect.csv",
    "train_deploy_parity_matrix.csv",
    "implementation_maturity_report.md",
    "model_code_fingerprint_manifest.csv",
    "standardized_casewise_metrics.csv",
    "standardized_model_summary.csv",
    "pathology_population_summary.csv",
    "subgroup_performance_matrix.csv",
    "help_harm_matrix.csv",
    "hd_component_matrix.csv",
    "prediction_manifest.csv",
    "metric_reaggregation_report.md",
    "case_error_taxonomy.csv",
    "case_review_selection.csv",
    "manual_visual_review_notes.md",
    "case_montage_manifest.csv",
    "case_oracle_summary.csv",
    "voxel_error_overlap_matrix.csv",
    "fn_overlap_matrix.csv",
    "fp_overlap_matrix.csv",
    "model_disagreement_matrix.csv",
    "selector_feature_manifest.csv",
    "selector_nested_cv_results.csv",
    "complementarity_report.md",
    "feature_probe_inventory.csv",
    "feature_probe_case_split.json",
    "feature_probe_summary.csv",
    "feature_probe_full_results.csv",
    "feature_probe_random_control.csv",
    "feature_separability_report.md",
    "decoder_reset_contract.json",
    "decoder_reset_training_summary.csv",
    "decoder_reset_checkpoint_manifest.csv",
    "decoder_reset_inner_casewise.csv",
    "decoder_reset_comparison.csv",
    "decoder_reset_diagnostic_report.md",
    "mosaic_repo_weight_recipe_binding.json",
    "mosaic_ablation_contract.json",
    "mosaic_recipe_decomposition_casewise.csv",
    "mosaic_recipe_decomposition_summary.csv",
    "mosaic_clean_full_data_gap.csv",
    "mosaic_help_harm_vs_nnunet.csv",
    "mosaic_gap_forensics_report.md",
    "cross_modal_alignment_casewise.csv",
    "slice_correspondence_quality.csv",
    "alignment_error_correlation.csv",
    "alignment_forensics_report.md",
    "cine_data_manifest.csv",
    "cine_model_lineage.csv",
    "cine_implementation_fidelity_matrix.csv",
    "cine_casewise_metrics.csv",
    "cine_temporal_signal_probe.csv",
    "cine_motion_quality.csv",
    "cine_forensics_report.md",
    "root_cause_evidence_graph.json",
    "root_cause_ranked_table.csv",
    "research_decision_tree.md",
    "local_evidence_conclusions.md",
    "external_deep_research_question_bank.md",
    "external_deep_research_question_bank.json",
    "evidence_claim_ledger.csv",
    "deep_research_evidence_index.md",
    "deep_research_upload_manifest.json",
    "deep_research_prompt_seed.md",
    "report_source/CARE_failure_forensics_20260730.tex",
    "report_source/build_commands.txt",
    "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf",
    "pdfinfo.txt",
    "pdf_text_extract.txt",
    "pdf_render_manifest.csv",
    "pdf_page_quality.csv",
    "pdf_validation_report.json",
    "completion_check.md",
    "controller_report.md",
    "MANIFEST.md",
]

FORBIDDEN_STATUS_IN_BRIEF = ["PENDING", "RUNNING", "NEEDS_MONITOR", "JOB_SUBMITTED", "AWAITING_SACCT"]


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        return {"_error": str(exc)}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        return p.returncode, p.stdout
    except Exception as exc:
        return 99, str(exc)


def validate(root: Path) -> tuple[dict, int]:
    checks: list[dict[str, object]] = []
    missing = [p for p in REQUIRED_FILES if not (root / p).exists()]
    checks.append({"name": "required_outputs_exist", "status": "PASS" if not missing else "FAIL", "missing": missing})

    known_bad = _read_json(root / "reference_metric_known_bad_report.json")
    checks.append({"name": "reference_metric_known_bad", "status": known_bad.get("status", "FAIL")})

    claim_rows = _csv_rows(root / "evidence_claim_ledger.csv")
    checks.append({"name": "claim_ledger_nonempty", "status": "PASS" if len(claim_rows) >= 10 else "FAIL", "rows": len(claim_rows)})

    pdf_path = root / "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf"
    pdf_exists = pdf_path.exists() and pdf_path.stat().st_size > 10000
    checks.append({"name": "pdf_exists_nonempty", "status": "PASS" if pdf_exists else "FAIL", "size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0})

    text_path = root / "pdf_text_extract.txt"
    text = text_path.read_text(errors="ignore") if text_path.exists() else ""
    checks.append({"name": "pdf_searchable_text", "status": "PASS" if "失败取证" in text and len(text) > 1000 else "FAIL", "chars": len(text)})

    page_rows = _csv_rows(root / "pdf_page_quality.csv")
    bad_pages = [r for r in page_rows if r.get("status") not in {"PASS", "WARN"}]
    checks.append({"name": "pdf_page_quality", "status": "PASS" if page_rows and not bad_pages else "FAIL", "bad_pages": bad_pages[:20], "pages": len(page_rows)})

    ctx = _read_json(root / "controller_context.json")
    checks.append({"name": "no_push_authorized", "status": "PASS" if ctx.get("authorization", {}).get("auto_git_push") is False else "FAIL"})
    checks.append({"name": "no_validation_upload_authorized", "status": "PASS" if ctx.get("authorization", {}).get("validation_upload_authorized") is False else "FAIL"})

    diag_required = [
        "D0_FULL_PRETRAINED_IDENTITY",
        "D1_DECODER_RESET_ENCODER_FROZEN",
        "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE",
        "D3_FULL_MODEL_SHORT_FINETUNE",
        "FEATURE_PROBE_HELDOUT",
        "MOSAIC_RECIPE_DECOMPOSITION",
        "CINE_TEMPORAL_PROBE",
    ]
    finalizer = _read_json(root / "finalizer_state.json")
    completed = set(finalizer.get("completed_diagnostics", []))
    missing_diag = [d for d in diag_required if d not in completed]
    checks.append({"name": "required_diagnostic_waves_terminal", "status": "PASS" if not missing_diag else "FAIL", "missing": missing_diag})

    brief = root / "notification_brief.json"
    if brief.exists():
        btxt = brief.read_text(errors="ignore")
        checks.append({"name": "notification_brief_no_monitor_tokens", "status": "PASS" if not any(s in btxt for s in FORBIDDEN_STATUS_IN_BRIEF) else "FAIL"})
    else:
        checks.append({"name": "notification_brief_present", "status": "FAIL"})

    hard_fail = [c for c in checks if c["status"] == "FAIL"]
    terminal_status = "VERIFIED_COMPLETE" if not hard_fail else "NEEDS_REPAIR"
    report = {
        "validator": "care_failure_forensics",
        "root": str(root),
        "status": "PASS" if not hard_fail else "FAIL",
        "controller_verification_decision": terminal_status,
        "checks": checks,
        "hard_fail_count": len(hard_fail),
    }
    return report, 0 if not hard_fail else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    report, code = validate(args.root)
    (args.root / "strict_validator_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
