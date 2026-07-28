from __future__ import annotations

import numpy as np
import pytest
import torch

from src.care_myocardium.inference.care_dpr_predictor import build_candidates, compose_dual_pathology
from src.care_myocardium.models.care_dpr import build_care_dpr
from src.care_myocardium.training.care_dpr_trainer import care_dpr_loss


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
