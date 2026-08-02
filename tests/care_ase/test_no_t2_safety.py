import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import care_ase_loss, set_stage_trainability


def test_no_t2_excludes_class4_and_edema_branch_gradient():
    model = build_care_ase_for_fold(2)
    set_stage_trainability(model, global_step=6000)
    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.tensor([[1.0, 0.0, 1.0]])
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, 2:4, 18:34, 18:34] = 5
    outputs = model(sample, availability, global_step=6000)
    loss, metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    edema_grad = max(
        (float(param.grad.detach().abs().max()) for name, param in model.named_parameters() if name.startswith("edema_branch.") and param.grad is not None),
        default=0.0,
    )
    assert "five_class_ce_without_class4" in metrics
    assert "six_class_ce" not in metrics
    assert metrics["edema_binary_t2_gated"] == 0.0
    assert edema_grad == 0.0
