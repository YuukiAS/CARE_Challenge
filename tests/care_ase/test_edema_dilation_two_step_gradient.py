import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import build_optimizer, care_ase_loss, set_stage_trainability


def test_edema_dilation_receives_gradient_after_projection_update():
    model = build_care_ase_for_fold(2)
    set_stage_trainability(model, global_step=6000)
    optimizer = build_optimizer(model)
    sample = torch.randn(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, 3:6, 24:40, 24:40] = 4

    outputs = model(sample, availability, global_step=6000)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    projection_grad0 = max(
        float(model.edema_branch.half_projections.projections["edema_context_to_half"].weight.grad.detach().abs().max()),
        float(model.edema_branch.full_projections.projections["edema_dilation1_to_full"].weight.grad.detach().abs().max())
        if model.edema_branch.full_projections.projections["edema_dilation1_to_full"].weight.grad is not None
        else 0.0,
    )
    assert projection_grad0 > 0.0
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)

    outputs = model(sample, availability, global_step=6001)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    dilation_grad1 = float(model.edema_dilation_context.dilated["1"][-1].weight.grad.detach().abs().max())
    assert dilation_grad1 > 0.0
