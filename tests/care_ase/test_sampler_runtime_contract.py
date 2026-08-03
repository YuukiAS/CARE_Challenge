from pathlib import Path

from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler


def test_sampler_stage_c_center_groups_are_runtime_selectable():
    sampler = CAREASEDeterministicSampler(Path.cwd(), 1)
    for step in range(10000):
        sampler.descriptor_bundle_for_step(step)

    center_b = sampler.descriptor_bundle_for_step(10000).micro_descriptors[0]
    center_c = sampler.descriptor_bundle_for_step(10001).micro_descriptors[0]

    assert center_b.case_group == "complete_centerB"
    assert center_b.center == "CenterB"
    assert center_c.case_group == "complete_centerC"
    assert center_c.center == "CenterC"
