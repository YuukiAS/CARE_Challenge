from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, build_optimizer
from src.care_myocardium.training.care_ase_runtime import optimizer_lr_by_group


def test_logged_lr_reads_actual_optimizer_param_groups():
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    scheduler.step(2000)
    observed = optimizer_lr_by_group(optimizer)
    actual = {str(group["name"]): float(group["lr"]) for group in optimizer.param_groups}
    assert observed == actual
    assert observed["new_modules"] == optimizer.param_groups[0]["lr"]
