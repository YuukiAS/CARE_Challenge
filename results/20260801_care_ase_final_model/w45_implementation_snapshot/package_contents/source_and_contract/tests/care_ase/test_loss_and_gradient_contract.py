import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold, care_ase_contract_summary
from src.care_myocardium.training.care_ase_trainer import care_ase_loss, set_stage_trainability


def test_step0_stock_clone_parity_synthetic_crop():
    model = build_care_ase_for_fold(2)
    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    report = model.step0_parity_report(sample, availability)
    assert report["status"] == "PASS"
    assert report["step0_scar_logit_parity_vs_stock_class5_max_abs_error"] <= 1.0e-6
    assert report["step0_edema_logit_parity_vs_stock_class4_max_abs_error"] <= 1.0e-6
    summary = care_ase_contract_summary(model)
    assert summary["scar_cloned_decoder_stage_indices"] == [4, 5]
    assert summary["normal_forward_reads_stock_pathology_logits"] is False


def test_loss_backward_has_finite_gradients():
    model = build_care_ase_for_fold(2)
    set_stage_trainability(model, global_step=6000)
    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, 2:4, 20:32, 20:32] = 5
    outputs = model(sample, availability, global_step=6000)
    loss, metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    assert metrics["all_finite"] == 1.0
    assert metrics["all_nonnegative"] == 1.0
    grad_max = max(float(p.grad.detach().abs().max()) for p in model.parameters() if p.grad is not None)
    assert grad_max > 0.0
