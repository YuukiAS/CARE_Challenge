import torch
import pytest

from src.care_myocardium.training.care_ase_runtime import CAREASEFormalRuntime


def _kwargs(tmp_path):
    return {
        "model": torch.nn.Linear(1, 1),
        "optimizer": torch.optim.SGD(torch.nn.Linear(1, 1).parameters(), lr=1.0),
        "scheduler": object(),
        "sampler": object(),
        "stock_transform": None,
        "initial_patch_size": (1, 1, 1),
        "final_patch_size": (1, 1, 1),
        "device": torch.device("cpu"),
    }


def test_formal_runtime_requires_verified_full_case_target_cache(tmp_path):
    with pytest.raises(RuntimeError, match="full_case_target_cache_manifest_verified"):
        CAREASEFormalRuntime(**_kwargs(tmp_path), formal_mode=True)
