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
            "task_key": "20260803_care_ase_r2_final_pretraining_closure_v8",
            "v8_manifest": True,
            "forbidden_old_manifest_paths_rejected": True,
            "manifest_path": "unit-test-v8-manifest.json",
            "manifest_sha256": "unit-test",
            "cases": {},
        },
    )


def test_sampler_stage_c_center_groups_are_runtime_selectable(monkeypatch):
    _patch_manifest_loader(monkeypatch)
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    for step in range(10000):
        sampler.descriptor_bundle_for_step(step)

    center_b = sampler.descriptor_bundle_for_step(10000).micro_descriptors[0]
    center_c = sampler.descriptor_bundle_for_step(10001).micro_descriptors[0]

    assert center_b.case_group == "complete_centerB"
    assert center_b.center == "CenterB"
    assert center_c.case_group == "complete_centerC"
    assert center_c.center == "CenterC"


def test_sampler_rejects_old_manifest_path_when_v7_missing(tmp_path):
    old = tmp_path / "results/20260803_care_ase_r2_full_fidelity_execution/hard_negative_manifest_fold1.json"
    old.parent.mkdir(parents=True)
    old.write_text("{}\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="hard-negative JSON manifest"):
        sampler_module._load_hard_negative_manifest(tmp_path, 1)
