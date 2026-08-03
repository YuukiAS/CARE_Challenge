import torch
import pytest

from src.care_myocardium.training.care_ase_runtime import CAREASEFormalRuntime


def test_formal_runtime_rejects_patch_local_target_fallback(tmp_path):
    manifest = tmp_path / "cache.json"
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="full_case_target_cache_manifest_verified"):
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
            full_case_target_cache_manifest_path=manifest,
            target_builder_provenance="patch_local_fallback_for_tests_only",
        )
