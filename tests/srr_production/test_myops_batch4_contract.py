from __future__ import annotations

import argparse
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest
import torch
import yaml

from scripts.srr_production import infer_myops
from scripts.training import run_srr_propref_myops_fold0 as train_myops
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint


def batch4_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "batch4_production_contract": True,
        "variant": "m10_d3_hierarchical_memory_propref",
        "encoder_profile": "full_4scale",
        "base_channels": 32,
        "final_output_mode": "anchor_bounded_srr_correction",
        "batch_size": 1,
        "max_steps": 1800,
        "overfit_steps": 60,
        "limit_train_cases": 0,
        "limit_val_cases": 0,
        "max_eval_cases": 0,
        "prototype_bank_cases": 176,
        "min_overfit_loss_decrease": 0.05,
        "enforce_min_train_loop_seconds": True,
        "min_train_loop_seconds_for_plateau": 1800.0,
        "full_volume_eval_steps": "600,1200,1800",
        "disable_local_refinement": False,
        "disable_anatomy_roi_prior": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_batch4_contract_rejects_undertraining_controls() -> None:
    train_myops.enforce_batch4_contract(batch4_args(), 176, 44)
    with pytest.raises(ValueError, match="max_steps"):
        train_myops.enforce_batch4_contract(batch4_args(max_steps=60), 176, 44)
    with pytest.raises(ValueError, match="limit"):
        train_myops.enforce_batch4_contract(batch4_args(limit_train_cases=8), 8, 44)
    with pytest.raises(ValueError, match="full_volume_eval_steps"):
        train_myops.enforce_batch4_contract(batch4_args(full_volume_eval_steps="600,1800"), 176, 44)


def test_batch4_overfit_loss_drop_is_relative_fraction() -> None:
    assert train_myops.relative_loss_decrease(2.0, 1.8) == pytest.approx(0.10)
    assert train_myops.relative_loss_decrease(None, 1.0) is None
    source = inspect.getsource(train_myops.run_one_batch_overfit)
    assert "loss_decrease_fraction" in source
    assert "relative_fraction_of_first_loss" in source


def test_batch4_overfit_uses_full_train_prototype_bank() -> None:
    source = inspect.getsource(train_myops.run_one_batch_overfit)
    assert "prototype_fit_cases = train_cases if bool(getattr(args, \"batch4_production_contract\", False)) else [case]" in source
    assert "fit_and_load_runtime_prototype_bank(model, [case], patch_shape, device, args, variant_dir)" not in source


def test_preflight_only_stops_before_formal_training() -> None:
    source = inspect.getsource(train_myops.train_variant)
    assert "preflight_only_after_one_batch_overfit" in source
    assert "PREFLIGHT_PASS_FORMAL_TRAINING_NOT_STARTED" in source
    parser_source = inspect.getsource(train_myops.main)
    assert "--preflight-only" in parser_source


def test_vectors_from_mask_shape_empty_and_cap() -> None:
    features = torch.arange(1 * 2 * 2 * 2 * 3, dtype=torch.float32).reshape(1, 2, 2, 2, 3)
    labels = torch.zeros((1, 2, 2, 3), dtype=torch.long)
    mask = torch.zeros_like(labels, dtype=torch.bool)
    empty = train_myops.vectors_from_mask(features, labels, mask, max_vectors=4)
    assert tuple(empty.shape) == (0, 2)

    mask[..., :] = True
    capped = train_myops.vectors_from_mask(features, labels, mask, max_vectors=5)
    assert tuple(capped.shape) == (5, 2)
    full = train_myops.vectors_from_mask(features, labels, mask, max_vectors=12)
    assert tuple(full.shape) == (12, 2)


def test_batch4_gate_usage_accepts_nested_gate_means() -> None:
    rows: list[dict[str, object]] = []
    outputs = {
        "gates": {"scar_memory": torch.tensor([[[0.2, 0.4], [0.6, 0.8]]])},
        "gate_valid_masks": {"scar_memory": torch.tensor([[[1.0, 0.0], [1.0, 1.0]]])},
        "dictionary_slot_metadata": {
            "scar_memory": [
                {"group": "scar", "kind": "positive", "modality": "LGE", "modalities": ("LGE",)},
                {"group": "scar", "kind": "negative", "modality": "T2", "modalities": ("T2", "C0")},
            ]
        },
    }
    train_myops.record_gate_usage(rows, "batch4", 1, ["Case2013"], outputs)
    assert len(rows) == 2
    assert rows[0]["mean_weight"] == pytest.approx(0.3)
    assert rows[1]["mean_weight"] == pytest.approx(0.7)
    assert rows[0]["valid_fraction"] == pytest.approx(0.5)
    assert rows[1]["valid_fraction"] == pytest.approx(1.0)


def test_training_checkpoint_helper_writes_schema_v2_mode_independent_architecture(tmp_path: Path) -> None:
    args = batch4_args()
    model = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="anchor_bounded_srr_correction")
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    ckpt = tmp_path / "checkpoint_validation_step_600.pt"
    train_myops.save_training_checkpoint(
        path=ckpt,
        model=model,
        optimizer=optimizer,
        args=args,
        global_step=600,
        epoch=0,
        anchor_manifest_hash="anchor-hash",
        prototype_memory_provenance={"source": "unit"},
        best_metric_state={"checkpoint_role": "validation_milestone"},
    )
    reloaded = SRRProposeRefineMyoPS(base_channels=2, encoder_profile="tiny_3scale", final_output_mode="srr_no_anchor_control")
    opt_reloaded = torch.optim.AdamW(reloaded.parameters(), lr=1e-4)
    payload = load_srr_checkpoint(
        path=ckpt,
        model=reloaded,
        optimizer=opt_reloaded,
        scheduler=None,
        amp_scaler=None,
        restore_rng=False,
    )
    assert payload["schema_version"] == 2
    assert payload["global_step"] == 600
    assert "final_output_mode" not in payload["architecture_config"]
    assert "srr_no_anchor_control" in payload["architecture_config"]["runtime_final_output_modes_supported"]


def test_inference_architecture_config_is_runtime_mode_independent() -> None:
    cfg = {"model": {"base_channels": 32, "variant": "m10_d3_hierarchical_memory_propref", "encoder_profile": "full_4scale"}}
    identity = infer_myops.architecture_config(cfg, "anchor_identity_control")
    no_anchor = infer_myops.architecture_config(cfg, "srr_no_anchor_control")
    assert identity == no_anchor
    assert "final_output_mode" not in identity
    assert infer_myops.runtime_final_output_mode("srr_no_anchor_control") == "srr_no_anchor_control"


def test_identity_export_source_is_model_logits_not_raw_anchor() -> None:
    source = inspect.getsource(infer_myops.run)
    assert "out_arr = model_labels" in source
    assert "out_arr = raw_anchor_labels if mode == \"anchor_identity_control\" else model_labels" not in source
    assert "identity_export_source" in source


def test_batch4_config_exposes_infer_and_eval_paths() -> None:
    cfg = yaml.safe_load((train_myops.REPO_ROOT / "configs/srr_production/myops_batch4.yaml").read_text(encoding="utf-8"))
    paths = cfg["paths"]
    for key in ("gt_dir", "anchor_fold0_pred_dir", "inference_root", "evaluation_root", "runtime_root", "log_root", "lock_root"):
        assert paths[key]
    assert set(cfg["modes"]) == {"anchor_identity_control", "anchor_bounded_srr_correction", "srr_no_anchor_control"}


def test_training_cli_print_contract_for_batch4() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(train_myops.REPO_ROOT / "scripts/training/run_srr_propref_myops_fold0.py"),
            "--variant",
            "m10_d3_hierarchical_memory_propref",
            "--encoder-profile",
            "full_4scale",
            "--base-channels",
            "32",
            "--final-output-mode",
            "anchor_bounded_srr_correction",
            "--batch-size",
            "1",
            "--max-steps",
            "1800",
            "--overfit-steps",
            "60",
            "--min-overfit-loss-decrease",
            "0.05",
            "--prototype-bank-cases",
            "176",
            "--full-volume-eval-steps",
            "600,1200,1800",
            "--enforce-min-train-loop-seconds",
            "--batch4-production-contract",
            "--print-contract",
        ],
        cwd=train_myops.REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["status"] == "CONTRACT_VALID"
    assert payload["train_case_count"] == 176
    assert payload["validation_case_count"] == 44
