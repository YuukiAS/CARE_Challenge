from pathlib import Path

import pytest

from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler


def test_formal_sampler_returns_four_independent_micro_descriptors():
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    bundle = sampler.descriptor_bundle_for_step(0, microbatch_count=4)

    assert len(bundle.micro_descriptors) == 4
    assert bundle.optimizer_step_stratum["case_group"] == "complete"
    assert all(desc.case_group == "complete" for desc in bundle.micro_descriptors)
    state = sampler.state_dict(next_descriptor=sampler.peek_descriptor_bundle_for_step(1))
    assert state["micro_case_rng_state_by_group"]
    assert state["next_optimizer_step_micro_descriptor_sha256"]


def test_descriptor_for_step_fails_closed_to_prevent_hidden_bundle_consumption():
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    with pytest.raises(RuntimeError, match="descriptor_bundle_for_step"):
        sampler.descriptor_for_step(0)
