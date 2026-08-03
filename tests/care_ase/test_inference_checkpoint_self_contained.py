import inspect

from src.care_myocardium.training import care_ase_trainer as trainer


def test_inference_checkpoint_loader_is_self_contained_api():
    source = inspect.getsource(trainer.load_care_ase_checkpoint_for_inference)
    assert "stock_checkpoint_required=False" in source
    assert "deployment_load_requires_stock_checkpoint" in source
    assert "__CARE_ASE_INFERENCE_LOAD_STOCK_CHECKPOINT_FORBIDDEN__" in source
