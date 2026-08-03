import inspect

from src.care_myocardium.models.care_ase import CAREASE
from src.care_myocardium.training import care_ase_trainer as trainer


def test_carease_constructor_can_skip_stock_checkpoint_for_deployment_load():
    signature = inspect.signature(CAREASE)
    assert "stock_checkpoint_required" in signature.parameters
    source = inspect.getsource(trainer.load_care_ase_checkpoint_for_inference)
    assert "stock_checkpoint_required=False" in source
