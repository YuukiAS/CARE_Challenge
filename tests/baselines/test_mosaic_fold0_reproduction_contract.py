from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mosaic_fair_protocol import (  # noqa: E402
    DEFAULT_RESULT_ROOT,
    load_fold_train_cases,
    load_fold_val_cases,
    load_yaml,
    protocol_receipt,
)
from scripts.training.run_mosaic_fold0_reproduction import sitk_write_like  # noqa: E402
from scripts.evaluation.finalize_mosaic_fold0_reproduction import (  # noqa: E402
    RESULT_BATCH7_MIN,
    expected_spooled_job_ids,
    find_manifest_prediction_rows,
    historical_summary,
    is_terminal_slurm_state,
    load_prediction_for_metrics,
    notification_brief_payload,
    pairwise,
    required_fold0_subgroups,
    secondary_comparison_summary,
    slurm_terminal_accounting,
    source_fingerprints,
    summarize,
    update_slurm_attempts,
    write_reports,
)
from controller_notifications.notify_goal_watcher import notification_brief_error  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


def write_preexisting_finalizer_inputs(root: Path, *, adapter_status: str = "PASS", omit: set[str] | None = None) -> None:
    omit = omit or set()
    for name in ["benchmark_contract.json", "weight_provenance.json"]:
        if name not in omit:
            (root / name).write_text("{}\n", encoding="utf-8")
    if "runtime_adapter_audit.json" not in omit:
        (root / "runtime_adapter_audit.json").write_text(
            json.dumps({"status": adapter_status, "myops_only": True, "cine_called": False, "normalized_case_count": 44}) + "\n",
            encoding="utf-8",
        )
    if "fold0_split_audit.csv" not in omit:
        (root / "fold0_split_audit.csv").write_text("case_id,status\n", encoding="utf-8")
    if "slurm_attempts.csv" not in omit:
        (root / "slurm_attempts.csv").write_text("job_id,state\n1,COMPLETED\n", encoding="utf-8")
    if "fair_comparison_audit.json" not in omit:
        (root / "fair_comparison_audit.json").write_text(
            json.dumps(
                {
                    "status": "PASS_PRETERMINAL_CONTRACT",
                    "exact_fold0_split": True,
                    "mosaic_random_init_required": True,
                    "full_data_weights_forbidden_for_fold0": True,
                    "full_data_weights_used_for_fold0": False,
                    "same_canonical_evaluator": True,
                    "single_finalizer_job_for_all_comparisons": True,
                    "split_sha256": "6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b",
                    "config_sha256": "162f56a3ef834dd96f17f82ac6e427c4f7b6ffaa3fab42f348381f915a494642",
                    "runtime_source_fingerprints": source_fingerprints(),
                    "spooled_scripts": {
                        "60589655": {"calls_stage_runner": True, "calls_finalizer": False, "contains_external_full_data_root": False},
                        "60589656": {"calls_stage_runner": True, "calls_finalizer": False, "contains_external_full_data_root": False},
                        "60589657": {"calls_stage_runner": True, "calls_finalizer": False, "contains_external_full_data_root": False},
                        "60589658": {"calls_stage_runner": False, "calls_finalizer": True, "contains_external_full_data_root": False},
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )


def complete_casewise_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    cases = load_fold_val_cases(REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json", 0)
    metadata = load_myops_case_metadata(REPO_ROOT)
    casewise = []
    geometry_rows = []
    for model_id in ["nnunet_fold0", "mosaic_fold0_random_init"]:
        for case_id in cases:
            meta = metadata[case_id]
            geometry_rows.append({"model_id": model_id, "case_id": case_id, "status": "PASS"})
            for pathology, class_id in [("pure_edema", 4), ("scar", 5)]:
                casewise.append(
                    {
                        "model_id": model_id,
                        "case_id": case_id,
                        "center": meta.center,
                        "modality_group": meta.modality_group,
                        "t2_present": int(meta.t2_present),
                        "pathology": pathology,
                        "compact_class": class_id,
                        "gt_positive": 1,
                        "prediction_positive": 1,
                        "Dice": 1.0,
                        "exact_HD": 0.0,
                        "HD95": 0.0,
                        "precision": 1.0,
                        "recall": 1.0,
                        "remote_FP_mm3": 0.0,
                        "component_count": 1,
                        "pred_volume_mm3": 10.0,
                        "gt_volume_mm3": 10.0,
                        "volume_ratio": 1.0,
                        "empty_prediction": 0,
                    }
                )
    return casewise, geometry_rows


def terminal_accounting_complete() -> dict[str, object]:
    return {
        "expected_job_ids": ["1"],
        "terminal_job_ids": ["1"],
        "missing_job_ids": [],
        "nonterminal_jobs": [],
        "all_expected_terminal": True,
    }


def complete_summary_and_history(cfg: dict[str, object], result_root: Path, casewise: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    secondary_rows, history_rows = secondary_comparison_summary(cfg, result_root)
    return summarize(casewise) + secondary_rows, history_rows


def test_exact_fold0_split_is_176_train_44_val():
    split = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
    train = load_fold_train_cases(split, 0)
    val = load_fold_val_cases(split, 0)
    assert len(train) == 176
    assert len(val) == 44
    assert set(train).isdisjoint(val)


def test_contract_forbids_full_data_weights_for_fold0_training_or_comparison():
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    guardrails = cfg["guardrails"]
    assert guardrails["training_authorized"] is True
    assert guardrails["fold0_training_from_random_init_required"] is True
    assert guardrails["full_data_weights_forbidden_for_fold0_training_or_comparison"] is True
    assert guardrails["full_data_weights_allowed_only_for_load_or_validation_deploy_smoke"] is True
    receipt = protocol_receipt(cfg, result_status="TEST", reason="unit")
    assert receipt["training_authorized"] is True
    assert receipt["train_count"] == 176
    assert receipt["val_count"] == 44


def test_default_result_root_uses_current_required_task_directory():
    assert DEFAULT_RESULT_ROOT == REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"


def test_sitk_writer_orients_zxy_prediction_to_reference_zyx(tmp_path: Path):
    ref = sitk.GetImageFromArray(np.zeros((6, 251, 264), dtype=np.int16))
    ref.SetSpacing((1.3, 1.4, 9.0))
    ref.SetOrigin((2.0, 3.0, 4.0))
    ref_path = tmp_path / "Case2002_gt.nii.gz"
    out_path = tmp_path / "Case2002_pred.nii.gz"
    sitk.WriteImage(ref, str(ref_path))
    zxy_prediction = np.zeros((6, 264, 251), dtype=np.int16)
    zxy_prediction[:, 10, 20] = 2221
    sitk_write_like(zxy_prediction, ref_path, out_path)
    out = sitk.ReadImage(str(out_path))
    assert out.GetSize() == ref.GetSize()
    assert np.allclose(out.GetSpacing(), ref.GetSpacing())
    assert np.allclose(out.GetOrigin(), ref.GetOrigin())
    out_arr = sitk.GetArrayFromImage(out)
    assert out_arr.shape == (6, 251, 264)
    assert int(out_arr[:, 20, 10].max()) == 2221


def test_raw_geometry_mismatch_is_reported_before_standardization(tmp_path: Path):
    gt = sitk.GetImageFromArray(np.zeros((3, 4, 5), dtype=np.int16))
    gt.SetSpacing((1.0, 1.0, 2.0))
    gt_path = tmp_path / "gt.nii.gz"
    sitk.WriteImage(gt, str(gt_path))

    pred = sitk.GetImageFromArray(np.ones((3, 4, 5), dtype=np.int16) * 1220)
    pred.SetSpacing((1.0, 1.0, 3.0))
    pred_path = tmp_path / "pred.nii.gz"
    sitk.WriteImage(pred, str(pred_path))

    pred_arr, audit = load_prediction_for_metrics(pred_path, gt, "official")
    assert audit["raw_geometry_match"] is False
    assert audit["standardized_geometry_match"] is True
    assert sorted(np.unique(pred_arr).tolist()) == [4]


def test_mosaic_finalizer_notification_brief_matches_existing_notifier_schema(tmp_path: Path):
    payload = notification_brief_payload(
        tmp_path,
        {"status": "READY_FOR_LOCAL_PACKET_COMMIT"},
        {"status": "PASS"},
    )
    assert payload["task_name"] == "20260725_care_myops_mosaic_fold0_reproduction"
    assert payload["final_status"] == "VERIFIED_COMPLETE"
    assert payload["commit_status"] == "local_commit_not_yet_recorded"
    assert payload["push_status"] == "not_pushed_not_authorized"
    assert payload["evidence_paths"]
    assert notification_brief_error(payload) == ""


def test_pending_slurm_job_fails_terminal_accounting_known_bad():
    rows = [{"job_id": "1", "state": "PENDING"}, {"job_id": "2", "state": "COMPLETED"}]
    report = slurm_terminal_accounting(rows, ["1", "2"])
    assert report["all_expected_terminal"] is False
    assert {row["job_id"] for row in report["nonterminal_jobs"]} == {"1"}
    assert is_terminal_slurm_state("COMPLETED") is True
    assert is_terminal_slurm_state("CANCELLED by 397557") is True
    assert is_terminal_slurm_state("RUNNING") is False


def test_update_slurm_attempts_preserves_submit_columns_and_marks_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    attempts = tmp_path / "slurm_attempts.csv"
    attempts.write_text(
        "timestamp,job_id,stage,partition,dependency,state,exit_code,elapsed,node_list,log_path,submit_stdout,submit_stderr,queue_evidence\n"
        "2026-07-25T00:00:00Z,123,coarse,htzhulab,,SUBMITTED,,,,,123,,queue.txt\n",
        encoding="utf-8",
    )

    class Completed:
        returncode = 0
        stdout = "123|MoSAICF0|htzhulab|COMPLETED|0:0|00:10:00|g0001\n"
        stderr = ""

    def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None):
        return Completed()

    monkeypatch.setattr("scripts.evaluation.finalize_mosaic_fold0_reproduction.subprocess.run", fake_run)
    report = update_slurm_attempts(tmp_path, ["123"])
    content = attempts.read_text(encoding="utf-8")
    assert "submit_stdout" in content
    assert "queue_evidence" in content
    assert "queue.txt" in content
    assert "terminal_accounted" in content
    assert report["all_expected_terminal"] is True


def test_failed_finalizer_report_does_not_claim_completion(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    terminal_accounting = {
        "expected_job_ids": ["1"],
        "terminal_job_ids": [],
        "missing_job_ids": [],
        "nonterminal_jobs": [{"job_id": "1", "state": "PENDING"}],
        "all_expected_terminal": False,
    }
    write_reports(cfg, tmp_path, [], [], [], {}, [], [], terminal_accounting)
    report = (tmp_path / "controller_report.md").read_text(encoding="utf-8")
    completion = (tmp_path / "completion_check.md").read_text(encoding="utf-8")
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "controller_verification_decision: NEEDS_REPAIR" in report
    assert "operational_completion_status: LOCAL_AGGREGATION_NEEDS_REPAIR" in report
    assert "公平复现已经完成" not in report.splitlines()[0]
    assert "本地聚合未通过终态验证" in completion.splitlines()[0]
    assert "controller_verification_decision: NEEDS_REPAIR" in completion


def test_successful_finalizer_first_run_counts_outputs_written_in_same_call(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    pairs, oracle = pairwise(casewise)
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    state = json.loads((tmp_path / "finalizer_state.json").read_text(encoding="utf-8"))
    report = (tmp_path / "controller_report.md").read_text(encoding="utf-8")
    assert state["status"] == "READY_FOR_LOCAL_PACKET_COMMIT"
    assert state["aggregation_complete"] is True
    assert (tmp_path / "complementarity_report.md").is_file()
    assert "controller_verification_decision: VERIFIED_COMPLETE" in report


def test_pairwise_rows_include_case_level_disagreement_fields():
    base = {
        "case_id": "Case0001",
        "center": "CenterB",
        "modality_group": "C0+LGE+T2",
        "t2_present": 1,
        "pathology": "scar",
        "gt_positive": 1,
    }
    rows, oracle = pairwise(
        [
            {
                **base,
                "model_id": "nnunet_fold0",
                "prediction_positive": 1,
                "Dice": 0.4,
                "exact_HD": 10.0,
                "HD95": 5.0,
                "precision": 0.5,
                "recall": 0.3,
                "remote_FP_mm3": 20.0,
                "component_count": 3,
                "volume_ratio": 0.8,
                "empty_prediction": 0,
            },
            {
                **base,
                "model_id": "mosaic_fold0_random_init",
                "prediction_positive": 0,
                "Dice": 0.6,
                "exact_HD": 8.0,
                "HD95": 4.0,
                "precision": 0.7,
                "recall": 0.6,
                "remote_FP_mm3": 5.0,
                "component_count": 1,
                "volume_ratio": 1.1,
                "empty_prediction": 1,
            },
        ]
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["help_harm"] == "help"
    assert row["precision_delta_mosaic_minus_nnunet"] == pytest.approx(0.2)
    assert row["recall_delta_mosaic_minus_nnunet"] == pytest.approx(0.3)
    assert row["exact_HD_delta_mosaic_minus_nnunet"] == pytest.approx(-2.0)
    assert row["HD95_delta_mosaic_minus_nnunet"] == pytest.approx(-1.0)
    assert row["remote_FP_delta_mosaic_minus_nnunet"] == pytest.approx(-15.0)
    assert row["component_count_delta_mosaic_minus_nnunet"] == pytest.approx(-2.0)
    assert row["volume_ratio_delta_mosaic_minus_nnunet"] == pytest.approx(0.3)
    assert row["empty_prediction_disagreement"] == 1
    assert row["prediction_presence_disagreement"] == 1
    assert row["oracle_gain_over_nnunet_Dice"] == pytest.approx(0.2)
    assert "prediction_presence" in row["disagreement_flags"]
    assert oracle["help_harm_counts"] == {"scar::help": 1}
    assert oracle["disagreement_row_count"] == 1


def test_secondary_comparison_adds_batch10_and_batch7_to_canonical_summary(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    canonical_rows, history_rows = secondary_comparison_summary(cfg, tmp_path)
    canonical_ids = {row["model_id"] for row in canonical_rows}
    assert "Batch10_MMRD::distill_epoch25_two_seed_mean" in canonical_ids
    assert "Batch7_minimal" in canonical_ids
    assert any(row["model_id"] == "Batch10_MMRD::distill_epoch25_two_seed_mean" and row["subgroup"] == "all" for row in canonical_rows)
    assert any(row["model_id"] == "Batch7_minimal" and row["subgroup"] == "all" for row in canonical_rows)
    assert any(row["model_id"] == "SCR_R1_generic_cascade_control" and str(row["status"]).startswith("historical_noncanonical") for row in history_rows)
    assert any(row["model_id"] == "Batch10_MMRD::distill_epoch25_two_seed_mean" and row["status"] == "canonical_recomputed_in_canonical_model_summary" for row in history_rows)
    assert any(row["model_id"] == "Batch7_minimal" and row["status"] == "canonical_recomputed_in_canonical_model_summary" for row in history_rows)


def test_finalizer_wrapper_is_single_slurm_job_for_inference_and_all_comparisons():
    wrapper = (REPO_ROOT / "jobs/evaluation/mosaic_fold0_reproduction_finalizer.sh").read_text(encoding="utf-8")
    assert "--job-name=MoSAICF0Fin" in wrapper
    assert "finalize_mosaic_fold0_reproduction.py" in wrapper
    assert "--job-ids" in wrapper
    submitter = (REPO_ROOT / "scripts/evaluation/submit_mosaic_fold0_reproduction.py").read_text(encoding="utf-8")
    assert 'submit("finalizer", dependency=f"afterany:{scar}:{edema}:{coarse}"' in submitter


def test_historical_summary_uses_canonical_recompute_when_batch10_manifest_complete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    cases = load_fold_val_cases(REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json", 0)
    pred_map, missing = find_manifest_prediction_rows(
        REPO_ROOT / "results/20260724_care_myops_batch10_deadline_rescue/ensemble_manifest.csv",
        "distill_epoch25_two_seed_mean",
        cases,
    )
    assert len(pred_map) == 44
    assert missing == []

    def fake_canonical(config, model_id, prediction_map, *, source_path, source_status):
        assert model_id == "Batch10_MMRD::distill_epoch25_two_seed_mean"
        assert len(prediction_map) == 44
        return [{"model_id": model_id, "status": "canonical_recomputed_from_existing_predictions", "source_status": source_status}]

    def fake_batch7(config, model_id, prediction_map, *, source_path, source_status):
        assert model_id == "Batch7_minimal"
        return [{"model_id": model_id, "status": "canonical_recomputed_from_existing_predictions", "source_status": source_status}]

    monkeypatch.setattr("scripts.evaluation.finalize_mosaic_fold0_reproduction.canonical_summary_from_prediction_map", fake_canonical)
    monkeypatch.setattr("scripts.evaluation.finalize_mosaic_fold0_reproduction.canonical_summary_from_pathology_prediction_map", fake_batch7)
    canonical_rows, history_rows = secondary_comparison_summary(cfg, tmp_path)
    assert canonical_rows[0]["model_id"] == "Batch10_MMRD::distill_epoch25_two_seed_mean"
    assert canonical_rows[0]["status"] == "canonical_recomputed_from_existing_predictions"
    assert any(row["model_id"] == "Batch10_MMRD::distill_epoch25_two_seed_mean" and row["status"] == "canonical_recomputed_in_canonical_model_summary" for row in history_rows)


def test_batch7_minimal_historical_path_points_to_existing_terminal_evidence():
    assert RESULT_BATCH7_MIN == REPO_ROOT / "results/20260722_srr_batch7_minimal_pathology_decomposition"
    assert (RESULT_BATCH7_MIN / "casewise_metrics.csv").is_file()


def test_failed_runtime_adapter_audit_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path, adapter_status="FAIL")
    casewise, geometry_rows = complete_casewise_rows()
    pairs, oracle = pairwise(casewise)
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "runtime_adapter_audit_not_pass" in validator["errors"]


def test_required_fold0_subgroups_include_center_t2_and_modality_groups():
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    assert required_fold0_subgroups(cfg) == [
        "all",
        "CenterB",
        "CenterC",
        "T2-present",
        "modality:C0+LGE",
        "modality:C0+LGE+T2",
        "modality:LGE-only",
    ]


def test_missing_required_summary_subgroup_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    summary = [row for row in summarize(casewise) if row["subgroup"] != "CenterB"]
    pairs, oracle = pairwise(casewise)
    _, history_rows = secondary_comparison_summary(cfg, tmp_path)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert any(error.startswith("canonical_summary_required_subgroups_missing:") for error in validator["errors"])
    assert "canonical_required_subgroups" in validator["known_bad_checks"]


def test_missing_casewise_metric_field_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    summary = summarize(casewise)
    pairs, oracle = pairwise(casewise)
    del casewise[0]["HD95"]
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, [], terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "canonical_casewise_required_fields_missing:HD95" in validator["errors"]
    assert "casewise_required_metric_fields" in validator["known_bad_checks"]


def test_empty_pairwise_rows_block_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    write_reports(cfg, tmp_path, casewise, summary, [], {}, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "pairwise_help_harm_row_count_0_expected_88" in validator["errors"]
    assert any(error.startswith("pairwise_disagreement_fields_missing:") for error in validator["errors"])
    assert "pairwise_help_harm_row_count" in validator["known_bad_checks"]


def test_missing_fair_comparison_audit_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path, omit={"fair_comparison_audit.json"})
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "fair_comparison_audit_missing" in validator["errors"]
    assert "preexisting_required_outputs_missing:fair_comparison_audit.json" in validator["errors"]
    assert "fair_comparison_audit_required" in validator["known_bad_checks"]


def test_stale_fair_comparison_audit_source_fingerprint_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    payload = json.loads((tmp_path / "fair_comparison_audit.json").read_text(encoding="utf-8"))
    first_key = sorted(payload["runtime_source_fingerprints"])[0]
    payload["runtime_source_fingerprints"][first_key] = "stale"
    (tmp_path / "fair_comparison_audit.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "fair_comparison_audit_source_fingerprint_mismatch" in validator["errors"]


def test_false_fair_comparison_audit_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    (tmp_path / "fair_comparison_audit.json").write_text(
        json.dumps(
            {
                "status": "FAIL",
                "exact_fold0_split": True,
                "mosaic_random_init_required": False,
                "full_data_weights_forbidden_for_fold0": True,
                "full_data_weights_used_for_fold0": True,
                "same_canonical_evaluator": True,
                "single_finalizer_job_for_all_comparisons": True,
                "split_sha256": "6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b",
                "config_sha256": "162f56a3ef834dd96f17f82ac6e427c4f7b6ffaa3fab42f348381f915a494642",
                "runtime_source_fingerprints": source_fingerprints(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "fair_comparison_audit_not_pass" in validator["errors"]
    assert "fair_comparison_audit_mosaic_random_init_required_not_true" in validator["errors"]
    assert "fair_comparison_audit_full_data_weights_used" in validator["errors"]


def test_missing_spooled_script_audit_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    payload = json.loads((tmp_path / "fair_comparison_audit.json").read_text(encoding="utf-8"))
    payload.pop("spooled_scripts")
    (tmp_path / "fair_comparison_audit.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "fair_comparison_audit_spooled_scripts_missing" in validator["errors"]
    assert "fair_comparison_audit_stage_job_not_bound_to_runner:60589655" in validator["errors"]
    assert "slurm_spooled_script_runtime_binding" in validator["known_bad_checks"]


def test_spooled_script_audit_uses_submission_receipt_job_ids(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    (tmp_path / "slurm_submission_receipt.json").write_text(
        json.dumps({"coarse_job_id": "11", "scar_job_id": "12", "edema_job_id": "13", "finalizer_job_id": "14"}) + "\n",
        encoding="utf-8",
    )
    payload = json.loads((tmp_path / "fair_comparison_audit.json").read_text(encoding="utf-8"))
    payload["spooled_scripts"] = {
        "11": {"calls_stage_runner": True, "calls_finalizer": False, "contains_external_full_data_root": False},
        "12": {"calls_stage_runner": True, "calls_finalizer": False, "contains_external_full_data_root": False},
        "13": {"calls_stage_runner": True, "calls_finalizer": False, "contains_external_full_data_root": False},
        "14": {"calls_stage_runner": False, "calls_finalizer": True, "contains_external_full_data_root": False},
    }
    (tmp_path / "fair_comparison_audit.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    assert expected_spooled_job_ids(tmp_path) == {"stage_job_ids": ["11", "12", "13"], "finalizer_job_id": "14"}
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert "fair_comparison_audit_stage_job_not_bound_to_runner:60589655" not in validator["errors"]
    assert "fair_comparison_audit_finalizer_job_not_bound_to_finalizer" not in validator["errors"]


def test_bad_spooled_script_binding_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    payload = json.loads((tmp_path / "fair_comparison_audit.json").read_text(encoding="utf-8"))
    payload["spooled_scripts"]["60589655"]["calls_stage_runner"] = False
    payload["spooled_scripts"]["60589656"]["contains_external_full_data_root"] = True
    payload["spooled_scripts"]["60589658"]["calls_finalizer"] = False
    (tmp_path / "fair_comparison_audit.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "fair_comparison_audit_stage_job_not_bound_to_runner:60589655" in validator["errors"]
    assert "fair_comparison_audit_spooled_script_contains_full_data_root:60589656" in validator["errors"]
    assert "fair_comparison_audit_finalizer_job_not_bound_to_finalizer" in validator["errors"]
    assert "slurm_spooled_script_runtime_binding" in validator["known_bad_checks"]


def test_missing_preexisting_required_output_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path, omit={"benchmark_contract.json"})
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "preexisting_required_outputs_missing:benchmark_contract.json" in validator["errors"]
    assert "preexisting_required_outputs" in validator["known_bad_checks"]


def test_missing_primary_casewise_key_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    casewise = [row for row in casewise if not (row["model_id"] == "mosaic_fold0_random_init" and row["case_id"] == "Case1002" and row["pathology"] == "scar")]
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "canonical_casewise_primary_key_count_175_expected_176" in validator["errors"]
    assert any(error.startswith("canonical_casewise_primary_keys_missing:") for error in validator["errors"])
    assert "canonical_casewise_primary_key_count" in validator["known_bad_checks"]


def test_missing_secondary_canonical_summary_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    summary = [row for row in summary if row.get("model_id") != "Batch7_minimal"]
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert any(error.startswith("secondary_canonical_summary_required_rows_missing:") for error in validator["errors"])
    assert "secondary_canonical_summary_rows" in validator["known_bad_checks"]


def test_missing_scr_historical_boundary_blocks_strict_validator(tmp_path: Path):
    cfg = load_yaml(REPO_ROOT / "configs/baselines/mosaic_fold0_fair.yaml")
    write_preexisting_finalizer_inputs(tmp_path)
    casewise, geometry_rows = complete_casewise_rows()
    summary, history_rows = complete_summary_and_history(cfg, tmp_path, casewise)
    history_rows = [row for row in history_rows if row.get("model_id") != "SCR_R1_generic_cascade_control"]
    pairs, oracle = pairwise(casewise)
    write_reports(cfg, tmp_path, casewise, summary, pairs, oracle, geometry_rows, history_rows, terminal_accounting_complete())
    validator = json.loads((tmp_path / "strict_validator_report.json").read_text(encoding="utf-8"))
    assert validator["status"] == "FAIL"
    assert "scr_r1_historical_noncanonical_boundary_missing" in validator["errors"]
    assert "historical_noncanonical_boundary" in validator["known_bad_checks"]


def test_runtime_adapter_audit_contract_keys_are_documented():
    expected = {
        "status",
        "myops_only",
        "cine_called",
        "expected_case_count",
        "normalized_case_count",
        "flat_prediction_dir",
        "compact_prediction_dir",
        "raw_nested_prediction_dir",
        "rows",
    }
    example = {
        "status": "PASS",
        "myops_only": True,
        "cine_called": False,
        "expected_case_count": 44,
        "normalized_case_count": 44,
        "flat_prediction_dir": "results/task/native_mosaic_predictions",
        "compact_prediction_dir": "results/task/native_mosaic_predictions_compact",
        "raw_nested_prediction_dir": "results/task/native_mosaic_raw_nested/MyoPS/Anonymous Center",
        "rows": [{"nested_output_normalized": 1, "label_space": "official", "standardized_geometry_status": "PASS"}],
    }
    assert expected <= set(example)
    assert example["myops_only"] is True
    assert example["cine_called"] is False
    assert example["rows"][0]["nested_output_normalized"] == 1
