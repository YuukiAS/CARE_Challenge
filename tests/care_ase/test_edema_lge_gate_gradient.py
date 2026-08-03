import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import build_optimizer, care_ase_loss, set_stage_trainability


def test_edema_lge_gate_is_nonzero_and_trainable_after_projection_update():
    model = build_care_ase_for_fold(2)
    assert abs(float(model.edema_lge_gate().detach()) - 0.05) <= 1.0e-6
    set_stage_trainability(model, global_step=6000)
    optimizer = build_optimizer(model)
    sample = torch.randn(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, 2:6, 18:42, 18:42] = 4

    outputs = model(sample, availability, global_step=6000)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    assert float(model.edema_branch.half_projections.projections["edema_lge_to_half"].weight.grad.detach().abs().max()) > 0.0
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)

    outputs = model(sample, availability, global_step=6001)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    assert model.edema_lge_gate.raw.grad is not None
    assert float(model.edema_lge_gate.raw.grad.detach().abs()) > 0.0
