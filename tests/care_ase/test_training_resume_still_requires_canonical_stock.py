import inspect

from src.care_myocardium.training import care_ase_trainer as trainer


def test_training_resume_still_requires_requested_fold_canonical_stock():
    source = inspect.getsource(trainer.load_care_ase_checkpoint_for_training_resume)
    assert "stock_checkpoint_required=True" in source
    assert "CAREASEConfig.for_fold" in source
    assert "canonical stock checkpoint" in source
