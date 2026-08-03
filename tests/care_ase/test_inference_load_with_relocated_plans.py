import inspect

from src.care_myocardium.training import care_ase_trainer as trainer


def test_inference_loader_accepts_explicit_relocated_plans_path():
    source = inspect.getsource(trainer.load_care_ase_checkpoint_for_inference)
    assert "plans_path is not None" in source
    assert "config_payload[\"plans_path\"]" in source
