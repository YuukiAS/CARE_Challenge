from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import SimpleITK as sitk
import torch

from src.care_myocardium.data.care_dg_dataset import validate_care_dg_batch
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL, apply_competitive_correction, build_care_dg
from scripts.training.run_care_dg import deterministic_inner_split, support_maps, validate_inner_split_contract, validate_w0
from src.care_myocardium.training.care_dg_trainer import (
    care_dg_loss,
    load_care_dg_checkpoint,
    make_edema_zone_targets,
    make_error_targets,
    margin_improvement_loss,
    save_care_dg_checkpoint,
)


def _batch(batch: int = 2, t2: tuple[float, ...] = (1.0, 1.0)) -> dict[str, torch.Tensor]:
    torch.manual_seed(7)
    images = torch.randn(batch, 3, 4, 16, 16)
    anchor = torch.randn(batch, 6, 4, 16, 16)
    labels = anchor.argmax(dim=1)
    labels[:, 1:2, 5:8, 5:8] = 5
    labels[:, 2:3, 8:11, 8:11] = 4
    availability = torch.tensor([[1.0, float(t2[i]), 1.0] for i in range(batch)])
    return {
        "images": images,
        "anchor_logits": anchor,
        "availability": availability,
        "labels": labels,
        "anchor_mask": anchor.argmax(dim=1),
        "t2_present": availability[:, 1],
        "myocardium_support": torch.ones(batch, 1, 4, 16, 16),
        "edema_support": torch.ones(batch, 1, 4, 16, 16),
    }


def test_forward_shapes_and_nonconstant_gates() -> None:
    batch = _batch()
    validate_care_dg_batch(batch)
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    assert out["final_logits"].shape == batch["anchor_logits"].shape
    assert out["scar_q_fn"].std() > 0
    assert out["edema_q_fp"].std() > 0


def test_zero_correction_exact_anchor_identity() -> None:
    batch = _batch()
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"], force_zero_correction=True)
    torch.testing.assert_close(out["final_logits"], batch["anchor_logits"])


def test_competitive_intervention_changes_argmax() -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4, "scar_margin_cap": 8.0})
    with torch.no_grad():
        model.scar_decoder.head.bias[0] = 12.0
        model.scar_decoder.head.bias[1] = -12.0
        model.scar_decoder.head.bias[2] = 12.0
        model.scar_decoder.head.bias[3] = -12.0
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    assert torch.count_nonzero(out["final_mask"] != batch["anchor_mask"]) > 0


def test_no_t2_edema_decoder_gradient_zero() -> None:
    batch = _batch(batch=1, t2=(0.0,))
    batch["labels"].fill_(0)
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    loss, _ = care_dg_loss(out, batch["labels"], batch["anchor_mask"], t2_present=batch["t2_present"])
    loss.backward()
    for param in model.edema_decoder.parameters():
        if param.grad is not None:
            assert torch.count_nonzero(param.grad) == 0


def test_error_target_construction() -> None:
    labels = torch.tensor([[[[5, 0], [0, 0]]]])
    anchor = torch.tensor([[[[0, 5], [0, 0]]]])
    target = make_error_targets(labels, anchor, 5)
    assert target["fn"][0, 0, 0, 0, 0] == 1
    assert target["fp"][0, 0, 0, 0, 1] == 1


def test_checkpoint_reload_exact(tmp_path: Path) -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    before = model(batch["images"], batch["availability"], batch["anchor_logits"])["final_logits"]
    ckpt = tmp_path / "care_dg.pt"
    save_care_dg_checkpoint(ckpt, model, opt, step=3)
    loaded, step, _ = load_care_dg_checkpoint(ckpt)
    after = loaded(batch["images"], batch["availability"], batch["anchor_logits"])["final_logits"]
    assert step == 3
    torch.testing.assert_close(before, after)


def test_aligned_crop_preserves_image_label_error_map_coordinates() -> None:
    from src.care_myocardium.data.care_dg_dataset import aligned_spatial_crop

    batch = _batch(batch=1, t2=(1.0,))
    batch["fn_error_map"] = torch.zeros(1, 1, 4, 16, 16)
    batch["images"].zero_()
    batch["labels"].zero_()
    batch["anchor_mask"].zero_()
    batch["images"][0, 0, 2, 9, 10] = 5.0
    batch["labels"][0, 2, 9, 10] = 5
    batch["anchor_mask"][0, 2, 9, 10] = 0
    batch["fn_error_map"][0, 0, 2, 9, 10] = 1.0
    cropped = aligned_spatial_crop(batch, (1, 5, 6), (2, 8, 8))
    assert cropped["images"][0, 0, 1, 4, 4] == 5.0
    assert cropped["labels"][0, 1, 4, 4] == 5
    assert cropped["fn_error_map"][0, 0, 1, 4, 4] == 1.0



def test_fn_and_fp_margin_directions_are_opposite() -> None:
    target = {
        "fn": torch.ones(1, 1, 1, 1, 1),
        "fp": torch.zeros(1, 1, 1, 1, 1),
    }
    mask = torch.ones(1, 1, 1, 1, 1)
    anchor = torch.full((1, 1, 1, 1, 1), -2.0)
    final_good = torch.full((1, 1, 1, 1, 1), -0.5)
    final_bad = torch.full((1, 1, 1, 1, 1), -3.0)
    assert margin_improvement_loss(final_good, anchor, target, mask, margin=1.0) < 1e-6
    assert margin_improvement_loss(final_bad, anchor, target, mask, margin=1.0) > 1.0

    target = {"fn": torch.zeros_like(mask), "fp": torch.ones_like(mask)}
    anchor = torch.full((1, 1, 1, 1, 1), 2.0)
    final_good = torch.full((1, 1, 1, 1, 1), 0.5)
    final_bad = torch.full((1, 1, 1, 1, 1), 3.0)
    assert margin_improvement_loss(final_good, anchor, target, mask, margin=1.0) < 1e-6
    assert margin_improvement_loss(final_bad, anchor, target, mask, margin=1.0) > 1.0


def test_scar_competitor_can_convert_anchor_edema_to_scar() -> None:
    anchor = torch.zeros(1, 6, 1, 1, 1)
    anchor[:, EDEMA_CHANNEL] = 2.0
    anchor[:, SCAR_CHANNEL] = -2.0
    delta = torch.full((1, 1, 1, 1, 1), 5.0)
    final = apply_competitive_correction(
        anchor,
        delta,
        torch.ones_like(delta),
        SCAR_CHANNEL,
        8.0,
        competitor_channels=tuple(c for c in range(6) if c != SCAR_CHANNEL),
    )
    assert final.argmax(dim=1).item() == SCAR_CHANNEL


def test_edema_zone_target_is_scar_union_edema() -> None:
    labels = torch.tensor([[[[SCAR_CHANNEL, EDEMA_CHANNEL, 0]]]])
    anchor = torch.tensor([[[[0, 0, SCAR_CHANNEL]]]])
    target = make_edema_zone_targets(labels, anchor)
    assert target["gt"][0, 0, 0, 0, 0] == 1
    assert target["gt"][0, 0, 0, 0, 1] == 1
    assert target["fn"][0, 0, 0, 0, 0] == 1
    assert target["fn"][0, 0, 0, 0, 1] == 1
    assert target["fp"][0, 0, 0, 0, 2] == 1


def test_decode_edema_zone_includes_scar_and_pure_edema_excludes_scar() -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(batch["images"], batch["availability"], batch["anchor_logits"], force_zero_correction=True)
    scar_voxels = out["scar_mask"]
    assert torch.equal(out["edema_zone_mask"] & scar_voxels, scar_voxels)
    assert torch.count_nonzero(out["pure_edema_mask"] & scar_voxels) == 0


def test_bounded_magnitude_and_zero_gate_cannot_change_logits() -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4, "scar_margin_cap": 2.5, "edema_margin_cap": 3.5})
    with torch.no_grad():
        for decoder in (model.scar_decoder, model.edema_decoder):
            decoder.head.weight.zero_()
            decoder.head.bias[0] = -100.0
            decoder.head.bias[1] = -100.0
            decoder.head.bias[2] = 100.0
            decoder.head.bias[3] = 100.0
    out = model(batch["images"], batch["availability"], batch["anchor_logits"])
    assert float(out["scar_m_fn"].detach().max()) <= 2.5
    assert float(out["edema_m_fn"].detach().max()) <= 3.5
    torch.testing.assert_close(out["final_logits"], batch["anchor_logits"], atol=1e-5, rtol=0.0)


def test_mixed_batch_no_t2_sample_has_zero_edema_outputs_and_no_t2_gradients() -> None:
    mixed_batch = _batch(batch=2, t2=(1.0, 0.0))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(mixed_batch["images"], mixed_batch["availability"], mixed_batch["anchor_logits"], t2_present=mixed_batch["t2_present"])
    assert torch.count_nonzero(out["edema_q_fn"][1]) == 0
    assert torch.count_nonzero(out["edema_q_fp"][1]) == 0
    assert torch.count_nonzero(out["edema_delta"][1]) == 0

    no_t2_batch = _batch(batch=1, t2=(0.0,))
    no_t2_batch["labels"].fill_(EDEMA_CHANNEL)
    model.zero_grad(set_to_none=True)
    no_t2_out = model(no_t2_batch["images"], no_t2_batch["availability"], no_t2_batch["anchor_logits"], t2_present=no_t2_batch["t2_present"])
    loss, _ = care_dg_loss(no_t2_out, no_t2_batch["labels"], no_t2_batch["anchor_mask"], t2_present=no_t2_batch["t2_present"])
    loss.backward()
    for param in model.edema_decoder.parameters():
        if param.grad is not None:
            assert torch.count_nonzero(param.grad) == 0


def test_remote_penalty_uses_raw_pre_support_delta() -> None:
    logits = torch.zeros(1, 6, 1, 2, 2)
    outputs = {
        "final_logits": logits.clone(),
        "anchor_logits": logits.clone(),
        "scar_q_fn": torch.zeros(1, 1, 1, 2, 2),
        "scar_q_fp": torch.zeros(1, 1, 1, 2, 2),
        "edema_q_fn": torch.zeros(1, 1, 1, 2, 2),
        "edema_q_fp": torch.zeros(1, 1, 1, 2, 2),
        "scar_delta": torch.zeros(1, 1, 1, 2, 2),
        "edema_delta": torch.zeros(1, 1, 1, 2, 2),
        "scar_delta_raw": torch.ones(1, 1, 1, 2, 2),
        "edema_delta_raw": torch.ones(1, 1, 1, 2, 2),
        "scar_support": torch.zeros(1, 1, 1, 2, 2),
        "edema_support": torch.zeros(1, 1, 1, 2, 2),
    }
    labels = torch.zeros(1, 1, 2, 2, dtype=torch.long)
    anchor = torch.zeros_like(labels)
    _loss, metrics = care_dg_loss(outputs, labels, anchor, t2_present=torch.ones(1))
    assert metrics["remote"] > 1.0


def test_formal_mode_rejects_missing_inputs_and_anchor_kind() -> None:
    batch = _batch(batch=1, t2=(1.0,))
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    with pytest.raises(ValueError, match="anchor_value_kind"):
        model(
            batch["images"],
            batch["availability"],
            batch["anchor_logits"],
            uncertainty=torch.zeros(1, 1, 4, 16, 16),
            myocardium_support=torch.ones(1, 1, 4, 16, 16),
            edema_support=torch.ones(1, 1, 4, 16, 16),
            distance_to_myocardium=torch.zeros(1, 1, 4, 16, 16),
            strict_inputs=True,
        )
    with pytest.raises(ValueError, match="uncertainty"):
        model(
            batch["images"],
            batch["availability"],
            batch["anchor_logits"],
            myocardium_support=torch.ones(1, 1, 4, 16, 16),
            edema_support=torch.ones(1, 1, 4, 16, 16),
            distance_to_myocardium=torch.zeros(1, 1, 4, 16, 16),
            strict_inputs=True,
            anchor_value_kind="log_probabilities",
        )


def test_validate_w0_accepts_only_preregistered_pass_statuses(tmp_path: Path) -> None:
    (tmp_path / "strict_validator_report.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    for status in [
        "W1_IMPLEMENTATION_AND_REAL_CASE_GATES_PASS_FORMAL_TRAINING_NOT_STARTED",
        "GATE_A_REPAIRED_IMPLEMENTATION_PASS",
    ]:
        (tmp_path / "implementation_contract.json").write_text(f'{{"status":"{status}"}}\n', encoding="utf-8")
        validate_w0(tmp_path)
    for status in ["", "NEEDS_REPAIR", "GATE_A_REPAIRED_IMPLEMENTATION_PASS_EXTRA", "SOME_PASS_STRING"]:
        (tmp_path / "implementation_contract.json").write_text(f'{{"status":"{status}"}}\n', encoding="utf-8")
        with pytest.raises(SystemExit, match="CARE_DG_FORMAL_TRAINING_BLOCKED_W1_NOT_PASS"):
            validate_w0(tmp_path)


def test_inner_split_excludes_selection_from_stage_a_stage_b_and_records_hashes() -> None:
    class Meta:
        def __init__(self, group: str) -> None:
            self.modality_group = group

    cases = [f"Case{i:04d}" for i in range(30)]
    metadata = {case: Meta("C0+LGE+T2" if i < 15 else "C0+LGE") for i, case in enumerate(cases)}
    split = deterministic_inner_split(cases, fold=0, metadata=metadata)
    assert split["counts"]["inner_select"] >= 8
    assert split["counts"]["complete_inner_select"] == split["counts"]["inner_select"]
    assert not (set(split["actual_train_cases"]) & set(split["inner_select_cases"]))
    assert not (set(split["complete_actual_train_cases"]) & set(split["inner_select_cases"]))
    assert split["sha256"]["actual_train"]
    assert split["sha256"]["inner_select"]
    bad = dict(split)
    bad["actual_train_cases"] = list(split["actual_train_cases"]) + [split["inner_select_cases"][0]]
    with pytest.raises(ValueError, match="INNER_SELECT_LEAKS_INTO_STAGE_A"):
        validate_inner_split_contract(bad)
    bad = dict(split)
    bad["complete_actual_train_cases"] = list(split["complete_actual_train_cases"]) + [split["inner_select_cases"][0]]
    with pytest.raises(ValueError, match="INNER_SELECT_LEAKS_INTO_STAGE_B"):
        validate_inner_split_contract(bad)


def test_soft_myocardium_support_excludes_lv_rv_and_decays_continuously() -> None:
    anchor = np.zeros((21, 64, 64), dtype=np.int16)
    anchor[10, 10:15, 10:15] = 1
    anchor[10, 22, 22] = SCAR_CHANNEL
    anchor[10, 30, 30] = EDEMA_CHANNEL
    anchor[10, 52, 52] = 2
    anchor[10, 56, 56] = 3
    ref = sitk.GetImageFromArray(anchor.astype(np.float32))
    ref.SetSpacing((1.0, 1.0, 1.0))
    scar_support, edema_support, dist = support_maps(anchor, ref)
    assert float(scar_support[0, 10, 12, 12]) > 0.90
    assert float(scar_support[0, 10, 22, 22]) > 0.90
    assert float(edema_support[0, 10, 30, 30]) > 0.90
    assert float(dist[0, 10, 52, 52]) > 6.0
    assert float(scar_support[0, 10, 52, 52]) < 0.10
    assert float(scar_support[0, 10, 56, 56]) < 0.10
    near_shell = float(scar_support[0, 10, 17, 12])
    far_background = float(scar_support[0, 10, 35, 12])
    assert 0.0 < far_background < near_shell < 1.0


def test_zero_correction_identity_with_soft_support_inputs() -> None:
    batch = _batch(batch=1, t2=(1.0,))
    batch["myocardium_support"].fill_(0.25)
    batch["edema_support"].fill_(0.5)
    batch["distance_to_myocardium"] = torch.ones(1, 1, 4, 16, 16)
    model = build_care_dg({"encoder_channels": (8, 12, 16), "context_channels": 4})
    out = model(
        batch["images"],
        batch["availability"],
        batch["anchor_logits"],
        myocardium_support=batch["myocardium_support"],
        edema_support=batch["edema_support"],
        distance_to_myocardium=batch["distance_to_myocardium"],
        t2_present=batch["t2_present"],
        force_zero_correction=True,
    )
    torch.testing.assert_close(out["final_logits"], batch["anchor_logits"])
