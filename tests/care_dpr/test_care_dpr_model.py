from __future__ import annotations

import copy
import random

import numpy as np
import pytest
import torch

from src.care_myocardium.data.care_dpr_dataset import DPR_SAMPLER_PATTERN, sampler_slots_for_cursor
from src.care_myocardium.inference.care_dpr_predictor import aggregate_patch_outputs, build_candidates, compose_dual_pathology
from src.care_myocardium.models.care_dpr import build_care_dpr
from src.care_myocardium.training.care_dpr_trainer import care_dpr_loss, load_care_dpr_checkpoint, save_care_dpr_checkpoint


def _batch(t2: float = 1.0) -> dict[str, torch.Tensor]:
    torch.manual_seed(7)
    images = torch.randn(2, 3, 4, 16, 16)
    availability = torch.tensor([[1.0, t2, 1.0], [1.0, t2, 1.0]])
    anchor_logits = torch.randn(2, 6, 4, 16, 16)
    anchor_logits[:, 0] += 2.0
    labels = torch.zeros(2, 4, 16, 16, dtype=torch.long)
    labels[:, 1, 4:8, 4:8] = 5
    if t2:
        labels[:, 2, 8:12, 8:12] = 4
    support = torch.ones(2, 1, 4, 16, 16)
    return {"images": images, "availability": availability, "anchor_logits": anchor_logits, "labels": labels, "uncertainty": torch.zeros(2, 1, 4, 16, 16), "myocardium_support": support, "edema_support": support, "distance_to_myocardium": torch.zeros(2, 1, 4, 16, 16), "t2_present": torch.full((2,), float(t2))}


def _forward(model, batch, **kwargs):
    return model(batch["images"], batch["availability"], batch["anchor_logits"], uncertainty=batch["uncertainty"], myocardium_support=batch["myocardium_support"], edema_support=batch["edema_support"], distance_to_myocardium=batch["distance_to_myocardium"], t2_present=batch["t2_present"], strict_inputs=True, anchor_value_kind="log_probabilities", **kwargs)


def test_shared_encoder_independent_branches_and_five_outputs() -> None:
    model = build_care_dpr()
    assert model.scar_branch is not model.edema_branch
    assert {id(p) for p in model.scar_branch.parameters()}.isdisjoint({id(p) for p in model.edema_branch.parameters()})
    batch = _batch(t2=1.0)
    out = _forward(model, batch)
    for prefix in ("scar", "edema"):
        for key in ("p_coarse", "q_fn", "q_fp", "p_refined", "utility_accept_prob"):
            assert f"{prefix}_{key}" in out
            assert out[f"{prefix}_{key}"].shape == (2, 1, 4, 16, 16)


def test_teacher_roi_forbidden_in_eval_or_inference() -> None:
    model = build_care_dpr()
    batch = _batch(t2=1.0)
    with pytest.raises(ValueError, match="TEACHER_ROI_FORBIDDEN"):
        _forward(model, batch, scar_teacher_roi=torch.ones(2, 1, 4, 16, 16), edema_teacher_roi=torch.ones(2, 1, 4, 16, 16), teacher_roi_fraction=0.5, allow_teacher_roi=False)


def test_no_t2_edema_zero_and_no_gradient() -> None:
    model = build_care_dpr()
    batch = _batch(t2=0.0)
    out = _forward(model, batch)
    for key in ("edema_delta", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"):
        assert torch.count_nonzero(out[key]).item() == 0
    loss, _ = care_dpr_loss(out, batch["labels"], batch["anchor_logits"].argmax(1), t2_present=batch["t2_present"])
    loss.backward()
    edema_grad = 0.0
    for p in model.edema_branch.parameters():
        if p.grad is not None:
            edema_grad += float(p.grad.abs().sum())
    assert edema_grad == 0.0


def test_exact_anchor_fallback() -> None:
    model = build_care_dpr()
    batch = _batch(t2=1.0)
    out = _forward(model, batch, force_anchor_fallback=True)
    assert torch.equal(out["final_logits"], batch["anchor_logits"])


def test_add_and_revise_candidates_are_distinct_and_no_t2_edema_has_zero_candidates() -> None:
    anchor = np.zeros((4, 16, 16), dtype=np.uint8)
    anchor[:, 1:3, 1:3] = 5
    maps = {k: np.zeros_like(anchor, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    maps["scar_p_refined"][:, 8:10, 8:10] = 1.0
    maps["scar_p_coarse"][:, 8:10, 8:10] = 1.0
    maps["scar_q_fp"][:, 1:3, 1:3] = 1.0
    cands = build_candidates(anchor, maps, pathology="scar", threshold=0.5)
    assert {c.candidate_type for c, _, _ in cands} == {"ADD_FN", "REVISE_FP"}
    assert build_candidates(anchor, maps, pathology="edema_zone", t2_present=False) == []


def test_zero_accepted_candidates_exact_anchor_labels() -> None:
    anchor = np.zeros((4, 16, 16), dtype=np.uint8)
    anchor[:, 1:3, 1:3] = 5
    maps = {k: np.zeros_like(anchor, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    out, audit = compose_dual_pathology(anchor, maps, utility_threshold=0.99, t2_present=True)
    assert np.array_equal(out, anchor)
    assert audit == []


def test_sampler_cursor_rotates_across_batches_not_scar_only() -> None:
    slots0, cursor = sampler_slots_for_cursor(0, 4)
    slots1, cursor = sampler_slots_for_cursor(cursor, 4)
    assert slots0 == list(DPR_SAMPLER_PATTERN[:4])
    assert slots1 == list(DPR_SAMPLER_PATTERN[4:])
    assert cursor == 0
    long = []
    cursor = 0
    for _ in range(4):
        slots, cursor = sampler_slots_for_cursor(cursor, 4)
        long.extend(slots)
    assert {slot: long.count(slot) for slot in DPR_SAMPLER_PATTERN} == {slot: 2 for slot in DPR_SAMPLER_PATTERN}


def test_local_refiner_roi_sizes_and_boundary_padding_forward() -> None:
    model = build_care_dpr()
    assert model.scar_branch.local_refiner.roi_context_zyx == (8, 96, 96)
    assert model.edema_branch.local_refiner.roi_context_zyx == (8, 128, 128)
    batch = _batch(t2=1.0)
    batch["images"] = batch["images"][:, :, :, :12, :12]
    batch["anchor_logits"] = batch["anchor_logits"][:, :, :, :12, :12]
    batch["labels"] = batch["labels"][:, :, :12, :12]
    for key in ("uncertainty", "myocardium_support", "edema_support", "distance_to_myocardium"):
        batch[key] = batch[key][:, :, :, :12, :12]
    out = _forward(model, batch)
    assert out["scar_p_refined"].shape[-3:] == (4, 12, 12)
    assert out["edema_p_refined"].shape[-3:] == (4, 12, 12)


def test_revise_candidate_uses_whole_anchor_component_not_qfp_intersection() -> None:
    anchor = np.zeros((4, 16, 16), dtype=np.uint8)
    anchor[:, 1:6, 1:6] = 5
    maps = {k: np.zeros_like(anchor, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    maps["scar_q_fp"][:, 1:2, 1:2] = 1.0
    cands = [item for item in build_candidates(anchor, maps, pathology="scar", threshold=0.5) if item[0].candidate_type == "REVISE_FP"]
    assert len(cands) == 1
    cand, anchor_local, refined = cands[0]
    assert anchor_local.sum() == (anchor == 5).sum()
    assert refined.sum() == 0
    assert cand.voxel_count == int((anchor == 5).sum())


def test_unaccepted_candidate_does_not_partially_write_back() -> None:
    anchor = np.zeros((4, 16, 16), dtype=np.uint8)
    anchor[:, 1:6, 1:6] = 5
    maps = {k: np.zeros_like(anchor, dtype=np.float32) for k in ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]}
    maps["scar_q_fp"][:, 1:2, 1:2] = 1.0
    maps["scar_p_refined"][:, 1:3, 1:3] = 1.0
    out, audit = compose_dual_pathology(anchor, maps, utility_threshold=0.99, t2_present=True)
    assert audit and not any(item["accepted"] for item in audit)
    assert np.array_equal(out, anchor)


def test_full_volume_aggregation_returns_shared_feature_before_components() -> None:
    model = build_care_dpr()
    batch = _batch(t2=1.0)
    batch_np = {
        "images": batch["images"][0].numpy(),
        "availability": batch["availability"][0].numpy(),
        "anchor_logits": batch["anchor_logits"][0].numpy(),
        "uncertainty": batch["uncertainty"][0].numpy(),
        "myocardium_support": batch["myocardium_support"][0].numpy(),
        "edema_support": batch["edema_support"][0].numpy(),
        "distance_to_myocardium": batch["distance_to_myocardium"][0].numpy(),
        "t2_present": True,
    }
    maps = aggregate_patch_outputs(model, batch_np, patch_shape=(4, 16, 16), device=torch.device("cpu"))
    assert maps["aggregate_before_components"].item() is True
    assert maps["shared_full_resolution_feature"].shape[1:] == (4, 16, 16)
    assert "final_mask" not in maps


def test_checkpoint_resume_restores_exact_runtime_state(tmp_path) -> None:
    torch.manual_seed(11); np.random.seed(11); random.seed(11)
    model = build_care_dpr(); opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    rng = random.Random(99)
    batch = _batch(t2=1.0)
    def step_once(m, o):
        o.zero_grad(set_to_none=True)
        out = _forward(m, batch, teacher_roi_fraction=0.0)
        loss, _ = care_dpr_loss(out, batch["labels"], batch["anchor_logits"].argmax(1), t2_present=batch["t2_present"])
        loss.backward(); o.step()
        return {k: v.detach().clone() for k, v in out.items() if isinstance(v, torch.Tensor) and k in {"scar_p_coarse", "edema_p_coarse", "scar_utility_accept_prob", "edema_utility_accept_prob"}}
    uninterrupted = copy.deepcopy(model); opt_un = torch.optim.AdamW(uninterrupted.parameters(), lr=1e-4)
    opt_un.load_state_dict(opt.state_dict())
    for _ in range(4):
        out_un = step_once(uninterrupted, opt_un)
    resumed = copy.deepcopy(model); opt_res = torch.optim.AdamW(resumed.parameters(), lr=1e-4)
    opt_res.load_state_dict(opt.state_dict())
    for _ in range(2):
        step_once(resumed, opt_res)
    ckpt = tmp_path / "dpr.pt"
    save_care_dpr_checkpoint(ckpt, resumed, opt_res, 2, {}, local_rng=rng, stage="A1", local_step=2, sampler_slot_cursor=0, teacher_roi_schedule_cursor=2, resolved_training_contract_hash="abc")
    resumed2, step, extra = load_care_dpr_checkpoint(ckpt, model=resumed, optimizer=opt_res, local_rng=rng, restore_rng=True)
    assert step == 2
    assert extra["runtime_state"]["sampler_slot_cursor"] == 0
    assert extra["runtime_state"]["resolved_training_contract_hash"] == "abc"
    for _ in range(2):
        out_res = step_once(resumed2, opt_res)
    for (name_a, param_a), (name_b, param_b) in zip(uninterrupted.named_parameters(), resumed2.named_parameters()):
        assert name_a == name_b
        assert torch.equal(param_a, param_b)
    assert opt_un.state_dict().keys() == opt_res.state_dict().keys()
    for key in out_un:
        assert torch.equal(out_un[key], out_res[key])
