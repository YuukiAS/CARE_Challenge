import torch
import pytest

from src.care_myocardium.training.care_ase_runtime import CAREASEFormalRuntime


def test_missing_target_manifest_fails_before_forward(tmp_path):
    with pytest.raises(RuntimeError, match="full-case target cache manifest"):
        CAREASEFormalRuntime(
            model=torch.nn.Linear(1, 1),
            optimizer=torch.optim.SGD(torch.nn.Linear(1, 1).parameters(), lr=1.0),
            scheduler=object(),
            sampler=object(),
            stock_transform=None,
            initial_patch_size=(1, 1, 1),
            final_patch_size=(1, 1, 1),
            device=torch.device("cpu"),
            formal_mode=True,
            full_case_target_cache_manifest_path=tmp_path / "missing.json",
            target_builder_provenance="full_case_target_cache_manifest_verified",
        )
