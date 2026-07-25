from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import torch

from src.care_myocardium.data.care_srr_cascade_runtime import (
    ScheduleRow,
    apply_shared_spatial_augmentation,
    deterministic_schedule,
    schedule_sha256,
)
from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue, soft_union_probability
from src.care_myocardium.srr_production.anchor_runtime import build_synthetic_anchor_cache, canonicalize_probabilities
from src.care_myocardium.srr_production.case_prototypes import (
    EDEMA_NEGATIVE_CATEGORIES,
    EDEMA_POSITIVE_CATEGORIES,
    SCAR_NEGATIVE_CATEGORIES,
    build_case_prototype_record,
    select_crossfit_prototype_bank,
)
from src.care_myocardium.training.care_srr_cascade_trainer import (
    CARESRRCascadeFormalTrainer,
    FormalRuntimeConfig,
)
from scripts.evaluation import run_care_srr_cascade_rc2_preflight as rc2_preflight
from scripts.evaluation import finalize_care_srr_cascade_w3_accounting as w3_accounting
from scripts.evaluation import aggregate_care_srr_cascade_w4 as w4_aggregate
from scripts.evaluation.select_care_srr_cascade import select_candidate


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "envs/env_CARE/bin/python"


def _inputs(batch: int = 1) -> dict[str, torch.Tensor]:
    torch.manual_seed(11)
    anchor_logits = torch.randn(batch, 6, 2, 4, 4)
    anchor_probs = torch.softmax(anchor_logits, dim=1)
    return {
        "anchor_logits": anchor_logits,
        "source_features": torch.randn(batch, 32, 2, 4, 4),
        "distance_to_union_mm": torch.zeros(batch, 1, 2, 4, 4),
        "t2_present": torch.ones(batch),
        "normalized_lge": torch.randn(batch, 1, 2, 4, 4),
        "normalized_t2": torch.randn(batch, 1, 2, 4, 4),
        "teacher_anatomy_probabilities": torch.softmax(torch.randn(batch, 4, 2, 4, 4), dim=1),
        "teacher_edema_probability": torch.sigmoid(torch.randn(batch, 1, 2, 4, 4)),
        "scar_source_margin": torch.randn(batch, 1, 2, 4, 4),
        "explicit_anchor_probabilities": anchor_probs,
        "explicit_anchor_uncertainty": torch.rand(batch, 1, 2, 4, 4),
        "explicit_soft_union_probability": soft_union_probability(anchor_probs),
        "normalized_distance_to_union": torch.zeros(batch, 1, 2, 4, 4),
        "prototype_scar_positive_similarity": torch.randn(batch, 1, 2, 4, 4),
        "prototype_scar_negative_similarity": torch.randn(batch, 1, 2, 4, 4),
        "prototype_edema_positive_similarity": torch.randn(batch, 1, 2, 4, 4),
        "prototype_edema_negative_similarity": torch.randn(batch, 1, 2, 4, 4),
    }


def test_active_pathology_branches_are_independent() -> None:
    model = CARESRRCascadeRescue(source_feature_channels=32)
    with torch.no_grad():
        model.scar_output_projection.bias.fill_(1.0)
        model.edema_output_projection.bias[1].fill_(1.0)
    inputs = _inputs()
    scar = model(**inputs, active_pathology="scar")
    edema = model(**inputs, active_pathology="edema")
    assert torch.equal(scar["final_logits"][:, 4:5], inputs["anchor_logits"][:, 4:5])
    assert not torch.equal(scar["final_logits"][:, 5:6], inputs["anchor_logits"][:, 5:6])
    assert torch.equal(edema["final_logits"][:, 5:6], inputs["anchor_logits"][:, 5:6])
    assert not torch.equal(edema["final_logits"][:, 4:5], inputs["anchor_logits"][:, 4:5])

    loss = scar["final_logits"][:, 5].sum()
    loss.backward()
    assert model.scar_output_projection.bias.grad is not None
    assert model.edema_output_projection.bias.grad is None


def test_anchor_canonicalization_and_wrong_fold_rejection(tmp_path: Path) -> None:
    probs = torch.rand(1, 6, 2, 3, 4)
    logits, canon = canonicalize_probabilities(probs)
    assert logits.shape == probs.shape
    assert torch.allclose(canon.sum(dim=1), torch.ones_like(canon[:, 0]), atol=1e-6)
    rec = build_synthetic_anchor_cache(case_id="Case0001", probabilities=probs, output_dir=tmp_path, fold=0, allowed_fold=0)
    assert rec.decision == "PASS"
    try:
        build_synthetic_anchor_cache(case_id="Case0001", probabilities=probs, output_dir=tmp_path, fold=1, allowed_fold=0)
    except ValueError as exc:
        assert "OOF_case_uses_wrong_fold" in str(exc)
    else:
        raise AssertionError("wrong fold accepted")


def test_prototype_categories_preserved_and_hash_sampling_not_first_n() -> None:
    features = torch.arange(8 * 2 * 8 * 8, dtype=torch.float32).view(8, 2, 8, 8)
    mask = torch.ones(2, 8, 8, dtype=torch.bool)
    masks = {"GT_scar": mask}
    for category in SCAR_NEGATIVE_CATEGORIES:
        masks[category] = mask.clone()
    records = [
        build_case_prototype_record(case_id=f"case{i}", shard=i % 4, t2_present=True, features=features + i, masks=masks, cap=32, min_voxels=8)
        for i in range(10)
    ]
    assert set(SCAR_NEGATIVE_CATEGORIES).issubset(records[0].category_vectors)
    bank, meta = select_crossfit_prototype_bank(records, query_case_id="case1", query_shard=1, pathology="scar", minimum_positive=4, minimum_negative=8)
    assert bank["negative"].shape[0] >= 8
    assert meta["negative_categories_preserved"] is True
    sampled = records[0].category_vectors["GT_scar"]
    first_n_mean = torch.nn.functional.normalize(features.reshape(8, -1).transpose(0, 1)[:32].mean(dim=0, keepdim=True), dim=1)
    assert not torch.allclose(sampled, first_n_mean)


def test_edema_prototype_bank_excludes_no_t2_sources() -> None:
    features = torch.arange(8 * 2 * 8 * 8, dtype=torch.float32).view(8, 2, 8, 8)
    mask = torch.ones(2, 8, 8, dtype=torch.bool)
    t2_masks = {category: mask.clone() for category in (*EDEMA_POSITIVE_CATEGORIES, *EDEMA_NEGATIVE_CATEGORIES)}
    no_t2_masks = {category: mask.clone() for category in EDEMA_NEGATIVE_CATEGORIES}
    records = [
        build_case_prototype_record(case_id=f"t2_{i}", shard=i % 4, t2_present=True, features=features + i, masks=t2_masks, cap=32, min_voxels=8)
        for i in range(12)
    ]
    records.extend(
        build_case_prototype_record(case_id=f"no_t2_{i}", shard=(i + 1) % 4, t2_present=False, features=features + 100 + i, masks=no_t2_masks, cap=32, min_voxels=8)
        for i in range(4)
    )

    bank, meta = select_crossfit_prototype_bank(
        records,
        query_case_id="t2_0",
        query_shard=0,
        pathology="edema",
        minimum_positive=4,
        minimum_negative=8,
    )

    expected_source_cases = [r for r in records if r.case_id != "t2_0" and r.shard != 0 and r.t2_present]
    assert meta["source_eligibility_rule"] == "edema_requires_t2_present_sources"
    assert meta["excluded_no_t2_source_count"] > 0
    assert meta["no_t2_source_records_in_bank"] is False
    assert meta["allowed_case_count_after_source_filter"] == len(expected_source_cases)
    assert bank["positive"].shape[0] == len(expected_source_cases)
    assert bank["negative"].shape[0] == len(expected_source_cases) * len(EDEMA_NEGATIVE_CATEGORIES)


def test_matched_schedule_and_actual_augmentation_fiducial() -> None:
    control = deterministic_schedule(cases=["a", "b"], pathology="scar", variant="scar_cascade_control", seed=1, optimizer_steps=2)
    srr = deterministic_schedule(cases=["a", "b"], pathology="scar", variant="scar_cascade_control", seed=1, optimizer_steps=2)
    assert schedule_sha256(control) == schedule_sha256(srr)
    tensor = torch.zeros(1, 2, 3, 4)
    tensor[0, 1, 2, 3] = 1
    row = ScheduleRow(0, 1, 0, "v", "scar", "target", "case", (0, 0, 0), 1, True, False, True, 1)
    out = apply_shared_spatial_augmentation({"raw_modalities": tensor, "label": tensor.clone()}, row)
    assert torch.equal(out["raw_modalities"], out["label"])
    assert not torch.equal(out["raw_modalities"], tensor)


def test_trainer_checkpoint_resume_cursor_roundtrip(tmp_path: Path) -> None:
    model = CARESRRCascadeRescue(source_feature_channels=32)
    cfg = FormalRuntimeConfig(logical_run_id="scar_seed20260724", pathology="scar", variant="scar_cascade_control", seed=1, optimizer_steps=1)
    trainer = CARESRRCascadeFormalTrainer(model=model, config=cfg)
    batch = _inputs()
    batch["labels"] = torch.zeros(1, 2, 4, 4, dtype=torch.long)
    batch["labels"][0, 0, 0, 0] = 5
    batch["distance_to_gt_union_mm"] = torch.zeros(1, 1, 2, 4, 4)
    batch["distance_to_gt_pathology_surface_mm"] = torch.zeros(1, 1, 2, 4, 4)
    stats = trainer.train_microbatches([batch, batch], max_optimizer_steps=1)
    assert stats["optimizer_step"] == 1
    ckpt = tmp_path / "checkpoint.pt"
    hashes = {k: "x" for k in ("schedule_sha256", "initial_state_sha256", "code_sha256", "config_sha256", "source_cache_sha256", "anchor_cache_sha256", "prototype_cache_sha256")}
    trainer.save_checkpoint(ckpt, **hashes)
    reloaded = CARESRRCascadeFormalTrainer(model=CARESRRCascadeRescue(source_feature_channels=32), config=cfg)
    payload = reloaded.load_checkpoint(ckpt, expected=hashes)
    assert payload["optimizer_step"] == 1
    assert reloaded.microbatch_cursor == trainer.microbatch_cursor


def test_cli_contracts_and_orchestrator_no_hardcoded_job_ids() -> None:
    commands = [
        [str(PYTHON), "scripts/training/run_care_srr_cascade_formal.py", "--print-contract"],
        [str(PYTHON), "scripts/inference/run_care_srr_cascade_inference.py", "--print-contract"],
        [str(PYTHON), "scripts/evaluation/evaluate_care_srr_cascade.py", "--print-contract"],
        [str(PYTHON), "scripts/evaluation/select_care_srr_cascade.py", "--print-contract"],
        [str(PYTHON), "scripts/evaluation/validate_care_srr_cascade_packet.py", "--print-contract"],
        [str(PYTHON), "scripts/evaluation/orchestrate_care_srr_cascade_w3.py", "--print-contract"],
    ]
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)
    text = (ROOT / "scripts/evaluation/orchestrate_care_srr_cascade_w3.py").read_text()
    assert "60451021" not in text
    assert "60451022" not in text


def test_gpu_preflight_gate_accepts_any_compatible_pass(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc2_preflight, "RC1_ROOT", tmp_path)
    rows = [
        {"attempt_id": "bad_l40", "partition": "l40-gpu", "exit_code": "0", "decision": "PASS"},
        {"attempt_id": "failed_a100", "partition": "a100-gpu", "exit_code": "2", "decision": "NEEDS_REPAIR"},
    ]
    path = tmp_path / "gpu_preflight_attempts_v2.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["attempt_id", "partition", "exit_code", "decision"])
        writer.writeheader()
        writer.writerows(rows)
    assert rc2_preflight.gpu_preflight_passed() is False

    rows.append({"attempt_id": "pass_htzhulab", "partition": "htzhulab", "exit_code": "0", "decision": "PASS"})
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["attempt_id", "partition", "exit_code", "decision"])
        writer.writeheader()
        writer.writerows(rows)
    status = rc2_preflight.gpu_preflight_status()
    assert status["decision"] == "PASS"
    assert status["policy"] == "any_compatible_partition_pass"
    assert status["passed_partitions"] == ["htzhulab"]
    assert rc2_preflight.gpu_preflight_passed() is True


def test_formal_gate_accepts_single_compatible_gpu_preflight_pass(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc2_preflight, "RC1_ROOT", tmp_path)
    path = tmp_path / "gpu_preflight_attempts_v2.csv"
    rows = [
        {"attempt_id": "pass_l40", "partition": "l40-gpu", "exit_code": "0", "decision": "PASS"},
        {"attempt_id": "failed_a100", "partition": "a100-gpu", "exit_code": "2", "decision": "NEEDS_REPAIR"},
        {"attempt_id": "pass_htzhulab", "partition": "htzhulab", "exit_code": "0", "decision": "PASS"},
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["attempt_id", "partition", "exit_code", "decision"])
        writer.writeheader()
        writer.writerows(rows)

    monkeypatch.setattr(rc2_preflight, "anchor_cache_receipt_status", lambda: {"decision": "PASS"})
    monkeypatch.setattr(rc2_preflight, "source_cache_status", lambda verify_file_hashes=False: {"decision": "PASS"})
    monkeypatch.setattr(rc2_preflight, "prototype_receipt_status", lambda: {"decision": "PASS"})
    monkeypatch.setattr(rc2_preflight, "json_receipt_decision", lambda *args, **kwargs: "PASS")
    monkeypatch.setattr(rc2_preflight, "csv_receipt_decision", lambda *args, **kwargs: "PASS")

    gate = rc2_preflight.write_gate({})
    assert gate["decision"] == "PASS"
    assert gate["formal_jobs_authorized"] is True
    assert gate["gpu_preflight_status"]["policy"] == "any_compatible_partition_pass"
    assert gate["gpu_preflight_status"]["passed_partitions"] == ["htzhulab"]
    assert gate["gpu_preflight_status"]["selected_attempt"]["attempt_id"] == "pass_htzhulab"


def test_orchestrator_replaces_cancelled_zero_credit_attempt(tmp_path: Path) -> None:
    gate = tmp_path / "formal_authorization_gate.json"
    gate.write_text(json.dumps({"decision": "PASS"}))
    state = tmp_path / "state.json"
    attempts = tmp_path / "slurm_attempts.csv"
    adequacy = tmp_path / "training_adequacy.csv"
    state.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "logical_runs": {
                    "scar_seed20260724": {
                        "logical_run_id": "scar_seed20260724",
                        "pathology": "scar",
                        "seed": 20260724,
                        "partition": "htzhulab",
                        "variants": ["scar_cascade_control", "scar_srr_cascade"],
                        "job_id": "123456",
                        "state": "CANCELLED",
                        "command": "old sbatch command",
                    }
                },
            }
        )
    )
    proc = subprocess.run(
        [
            str(PYTHON),
            "scripts/evaluation/orchestrate_care_srr_cascade_w3.py",
            "--dry-run",
            "--submit",
            "--state-file",
            str(state),
            "--formal-gate",
            str(gate),
            "--slurm-attempts",
            str(attempts),
            "--training-adequacy",
            str(adequacy),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(state.read_text())
    scar = payload["logical_runs"]["scar_seed20260724"]
    assert scar["job_id"] == "DRY_RUN"
    assert scar["attempt_number"] == 2
    assert scar["attempt_history"][0]["job_id"] == "123456"
    assert scar["attempt_history"][0]["formal_training_credit"] == 0
    attempt_rows = list(csv.DictReader(attempts.open()))
    old_rows = [row for row in attempt_rows if row["slurm_job_id"] == "123456"]
    assert old_rows
    assert old_rows[0]["decision"] == "ZERO_CREDIT_REPLACED_ATTEMPT"


def test_w3_accounting_excludes_auxiliary_jobs_from_training_attempts() -> None:
    state = {
        "logical_runs": {
            "scar_seed20260725": {
                "job_id": "111",
                "attempt_history": [{"job_id": "110"}],
                "race_mirrors": [{"job_id": "112"}],
            }
        },
        "afterany_finalizer": {"job_id": "200"},
        "formal_race_watcher": {"job_id": "201"},
    }
    assert w3_accounting.collect_training_attempt_ids(state) == ["110", "111", "112"]
    assert w3_accounting.collect_auxiliary_job_ids(state) == ["200", "201"]


def test_w4_aggregation_waits_for_w3_terminal_accounting(tmp_path: Path) -> None:
    rc1 = tmp_path / "runtime_closure_repair_rc1"
    rc1.mkdir(parents=True)
    (rc1 / "formal_terminal_accounting_v2.json").write_text(json.dumps({"decision": "NEEDS_MONITOR"}))
    payload = w4_aggregate.aggregate(tmp_path)
    assert payload["decision"] == "NEEDS_MONITOR_W3_NOT_TERMINAL"
    assert payload["completion_claim"] is False


def test_w4_aggregation_rejects_candidate_outside_six(tmp_path: Path) -> None:
    rc1 = tmp_path / "runtime_closure_repair_rc1"
    rc1.mkdir(parents=True)
    (rc1 / "formal_terminal_accounting_v2.json").write_text(json.dumps({"decision": "PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION"}))
    for pathology in ("scar", "edema"):
        (tmp_path / f"w4_calibration_metrics_{pathology}_v2.csv").write_text(
            "split,candidate,Dice,exact_HD,remote_FP_mm3,help_harm\ncalibration,bad_candidate,0.1,1.0,0.0,0.0\n"
        )
        (tmp_path / f"w4_audit_metrics_{pathology}_v2.csv").write_text(
            "split,candidate,Dice,exact_HD,remote_FP_mm3,help_harm\naudit,srr_seed20260724,0.1,1.0,0.0,0.0\n"
        )
        (tmp_path / f"w4_selection_{pathology}_v2.json").write_text(json.dumps({"decision": "PASS", "selected_candidate": "bad_candidate"}))
        (tmp_path / f"w4_final_decision_{pathology}_v2.json").write_text(json.dumps({"decision": "USE_SRR_CASCADE", "audit_used_for_selection": False}))
    payload = w4_aggregate.aggregate(tmp_path)
    assert payload["decision"] == "NEEDS_REPAIR_W4_OUTPUTS"
    assert any("candidate_not_in_six" in blocker for blocker in payload["blockers"])


def test_selector_uses_six_candidate_for_audit_evidence_when_all_ineligible() -> None:
    rows = [
        {
            "split": "calibration",
            "candidate": "control_seed20260724",
            "candidate_eligible": "false",
            "positive_GT_Dice_delta": "0.01",
            "exact_HD_delta": "1.0",
            "HD95_relative_worsening": "0.1",
            "remote_FP_ratio": "1.0",
            "help_minus_harm": "2",
            "optimizer_step": "6250",
        },
        {
            "split": "calibration",
            "candidate": "srr_seed20260724",
            "candidate_eligible": "false",
            "positive_GT_Dice_delta": "0.02",
            "exact_HD_delta": "1.0",
            "HD95_relative_worsening": "0.1",
            "remote_FP_ratio": "1.0",
            "help_minus_harm": "2",
            "optimizer_step": "6250",
        },
    ]
    selected = select_candidate(rows)
    assert selected["decision"] == "PASS_AUDIT_EVIDENCE_ONLY_CALIBRATION_INELIGIBLE"
    assert selected["selected_candidate"] == "srr_seed20260724"
    assert selected["deployable_after_calibration"] is False


def test_w4_aggregation_accepts_fallback_when_audit_metrics_exist(tmp_path: Path) -> None:
    rc1 = tmp_path / "runtime_closure_repair_rc1"
    rc1.mkdir(parents=True)
    (rc1 / "formal_terminal_accounting_v2.json").write_text(json.dumps({"decision": "PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION"}))
    metric_header = "split,pathology,candidate,Dice,exact_HD,remote_FP_mm3,help_harm\n"
    for pathology in ("scar", "edema"):
        (tmp_path / f"w4_calibration_metrics_{pathology}_v2.csv").write_text(
            metric_header + f"calibration,{pathology},srr_seed20260724,0.1,1.0,0.0,0\n"
        )
        (tmp_path / f"w4_audit_metrics_{pathology}_v2.csv").write_text(
            metric_header + f"audit,{pathology},srr_seed20260724,0.1,1.0,0.0,0\n"
        )
        (tmp_path / f"w4_selection_{pathology}_v2.json").write_text(
            json.dumps(
                {
                    "decision": "PASS_AUDIT_EVIDENCE_ONLY_CALIBRATION_INELIGIBLE",
                    "selected_candidate": "srr_seed20260724",
                    "selection_split": "calibration",
                    "audit_used_for_selection": False,
                }
            )
        )
        (tmp_path / f"w4_final_decision_{pathology}_v2.json").write_text(
            json.dumps({"decision": "FALLBACK_TO_NNUNET", "audit_used_for_selection": False})
        )
    payload = w4_aggregate.aggregate(tmp_path)
    assert payload["decision"] == "PASS_READY_FOR_STRICT_VALIDATOR"
