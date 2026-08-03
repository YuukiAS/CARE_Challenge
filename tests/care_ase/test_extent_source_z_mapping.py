import numpy as np

from scripts.training.care_ase.run_care_ase_r2_chunk import _slice_profile_by_source_z, source_z_mapping


def test_extent_profile_uses_patch_source_z_not_generic_downsample():
    profile = np.arange(10, dtype=np.float32)
    z_a, valid_a = source_z_mapping(origin_z=2, output_z=4, full_z=10)
    z_b, valid_b = source_z_mapping(origin_z=5, output_z=4, full_z=10)

    patch_a = _slice_profile_by_source_z(profile, z_a, valid_a)
    patch_b = _slice_profile_by_source_z(profile, z_b, valid_b)

    assert patch_a.tolist() == [2.0, 3.0, 4.0, 5.0]
    assert patch_b.tolist() == [5.0, 6.0, 7.0, 8.0]
    assert patch_a.tolist() != patch_b.tolist()


def test_padding_z_maps_to_zero_profile_and_invalid():
    profile = np.arange(3, dtype=np.float32)
    z, valid = source_z_mapping(origin_z=-1, output_z=5, full_z=3)
    patch = _slice_profile_by_source_z(profile, z, valid)
    assert valid == [False, True, True, True, False]
    assert patch.tolist() == [0.0, 0.0, 1.0, 2.0, 0.0]
