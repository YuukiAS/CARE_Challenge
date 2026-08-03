from pathlib import Path

import numpy as np
import pytest

from src.care_myocardium.training.care_ase_augmentation import (
    build_stock_augmentation_contract,
    build_stock_training_transform_preserve_ignore,
    apply_stock_training_transform_with_targets,
)


def _center_of_mass(mask: np.ndarray) -> np.ndarray:
    coords = np.argwhere(mask)
    if len(coords) == 0:
        return np.array([-1.0, -1.0, -1.0])
    return coords.astype(np.float32).mean(axis=0)


def test_stock_transform_multitarget_spatial_identity():
    plans = Path("data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json")
    if not plans.is_file():
        pytest.skip("Dataset501 plans are not available")
    contract = build_stock_augmentation_contract(plans)
    transform = build_stock_training_transform_preserve_ignore(plans)
    shape = tuple(int(v) for v in contract.initial_patch_size)
    center = tuple(int(v // 2) for v in shape)
    image = np.zeros((3, *shape), dtype=np.float32)
    seg = np.zeros(shape, dtype=np.int64)
    regression = np.zeros((1, *shape), dtype=np.float32)
    component = np.zeros((1, *shape), dtype=np.int64)
    image[(0, *center)] = 1000.0
    seg[center] = 5
    regression[(0, *center)] = 1.0
    component[(0, *center)] = 7

    out_image, out_seg, out_regression, out_component = apply_stock_training_transform_with_targets(
        image,
        seg,
        transform=transform,
        availability=(1, 1, 1),
        regression_target_patch=regression,
        segmentation_extra_patch=component,
        seed=12345,
    )

    assert out_regression is not None
    assert out_component is not None
    seg_center = _center_of_mass(out_seg == 5)
    comp_center = _center_of_mass(out_component[0] == 7)
    reg_center = np.asarray(np.unravel_index(int(np.argmax(out_regression[0])), out_regression[0].shape), dtype=np.float32)
    img_center = np.asarray(np.unravel_index(int(np.argmax(out_image[0])), out_image[0].shape), dtype=np.float32)
    assert np.linalg.norm(seg_center - comp_center) <= 1.0
    assert np.linalg.norm(seg_center - reg_center) <= 2.0
    assert np.linalg.norm(seg_center - img_center) <= 2.0
