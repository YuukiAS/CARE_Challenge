import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import build_optimizer, care_ase_loss, set_stage_trainability


def _fixture():
    sample = torch.randn(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, 2:4, 20:34, 20:34] = 5
    seg[:, 4:6, 30:44, 30:44] = 4
    return sample, availability, seg


def test_modality_adapter_receives_gradient_after_projection_update():
    model = build_care_ase_for_fold(2)
    set_stage_trainability(model, global_step=6000)
    optimizer = build_optimizer(model)
    sample, availability, seg = _fixture()

    outputs = model(sample, availability, global_step=6000)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    projection_grad0 = float(model.edema_branch.half_projections.projections["edema_lge_to_half"].weight.grad.detach().abs().max())
    assert projection_grad0 > 0.0
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)

    outputs = model(sample, availability, global_step=6001)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    adapter_grad1 = float(model.edema_lge_half_adapter.net[-1].weight.grad.detach().abs().max())
    assert adapter_grad1 > 0.0
