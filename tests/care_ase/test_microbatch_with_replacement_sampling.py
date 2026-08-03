from pathlib import Path

import pytest

import src.care_myocardium.training.care_ase_sampler as sampler_module
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler


def _patch_manifest_loader(monkeypatch):
    monkeypatch.setattr(
        sampler_module,
        "_load_hard_negative_manifest",
        lambda _repo_root, _fold: {
            "source": "canonical_patient_held_out_stock_nnunet_oof_only",
            "v7_manifest": True,
            "forbidden_old_manifest_paths_rejected": True,
            "manifest_path": "unit-test-v7-manifest.json",
            "manifest_sha256": "unit-test",
            "cases": {},
        },
    )


def test_formal_sampler_returns_four_independent_micro_descriptors(monkeypatch):
    _patch_manifest_loader(monkeypatch)
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    bundle = sampler.descriptor_bundle_for_step(0, microbatch_count=4)

    assert len(bundle.micro_descriptors) == 4
    assert bundle.optimizer_step_stratum["case_group"] == "complete"
    assert all(desc.case_group == "complete" for desc in bundle.micro_descriptors)
    state = sampler.state_dict(next_descriptor=sampler.peek_descriptor_bundle_for_step(1))
    assert state["micro_case_rng_state_by_group"]
    assert state["next_optimizer_step_micro_descriptor_sha256"]


def test_descriptor_for_step_fails_closed_to_prevent_hidden_bundle_consumption(monkeypatch):
    _patch_manifest_loader(monkeypatch)
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    with pytest.raises(RuntimeError, match="descriptor_bundle_for_step"):
        sampler.descriptor_for_step(0)


def test_micro_patch_rng_selects_manifest_coordinate_and_resumes(monkeypatch):
    _patch_manifest_loader(monkeypatch)
    coords = ((1, 2, 3), (4, 5, 6), (7, 8, 9))
    monkeypatch.setattr(
        sampler_module,
        "_hard_negative_category",
        lambda _manifest, _case_id, _pathology_focus, _within_focus: (
            "scar_oof_fn",
            {"scar_fp_voxels": 0, "scar_fn_voxels": 3, "edema_fp_voxels": 0, "edema_fn_voxels": 0},
            coords,
        ),
    )
    sampler_a = CAREASEDeterministicSampler(Path.cwd(), 1)
    bundle_a = sampler_a.descriptor_bundle_for_step(0, microbatch_count=4)
    assert all(desc.selected_target_coordinate in coords for desc in bundle_a.micro_descriptors)
    assert all(desc.coordinate_selection_source == "micro_patch_rng_manifest_coordinate" for desc in bundle_a.micro_descriptors)

    state = sampler_a.state_dict(next_descriptor=sampler_a.peek_descriptor_bundle_for_step(1))
    sampler_b = CAREASEDeterministicSampler(Path.cwd(), 1)
    sampler_b.load_state_dict(state)
    assert sampler_a.peek_descriptor_bundle_for_step(1).sha256() == sampler_b.peek_descriptor_bundle_for_step(1).sha256()
