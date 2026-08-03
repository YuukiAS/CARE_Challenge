import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import care_ase_loss


def test_single_row_pathology_classifiers_receive_gradients():
    model = build_care_ase_for_fold(2)
    sample = torch.randn(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, 2:4, 20:34, 20:34] = 5
    seg[:, 4:6, 30:44, 30:44] = 4

    outputs = model(sample, availability, global_step=1)
    loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()

    classifier_params = {
        name: param
        for name, param in model.named_parameters()
        if ".seg_layers." in name and ("scar_branch" in name or "edema_branch" in name)
    }
    assert classifier_params
    assert all(param.grad is not None for param in classifier_params.values())
    assert all(torch.isfinite(param.grad).all() for param in classifier_params.values())
    assert all(float(param.grad.detach().abs().max()) > 0.0 for param in classifier_params.values())
