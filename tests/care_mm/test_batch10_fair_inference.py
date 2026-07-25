from __future__ import annotations

import numpy as np
import pytest
import torch

from scripts.inference.run_care_mm_batch10_fair_inference import (
    sliding_window_logits,
    validate_properties_dict,
)


class _Plans:
    transpose_forward = [0, 1, 2]
    transpose_backward = [0, 1, 2]


class _TinyModel(torch.nn.Module):
    def forward(self, x, availability, return_features=False):
        b, _c, d, h, w = x.shape
        logits = torch.zeros((b, 6, d, h, w), dtype=x.dtype, device=x.device)
        logits[:, 4] = 10.0
        logits[:, 5] = 1.0
        return {"six_class_logits": logits}


def _valid_props():
    return {
        "spacing": [10.0, 1.0, 1.0],
        "shape_before_cropping": (4, 5, 6),
        "shape_after_cropping_and_before_resampling": (2, 3, 4),
        "bbox_used_for_cropping": [[1, 3], [1, 4], [1, 5]],
    }


def test_validate_properties_rejects_missing_required_key():
    props = _valid_props()
    props.pop("bbox_used_for_cropping")
    with pytest.raises(ValueError, match="missing nnU-Net properties"):
        validate_properties_dict(props, _Plans())


def test_validate_properties_rejects_wrong_crop_bbox():
    props = _valid_props()
    props["bbox_used_for_cropping"] = [[0, 1], [0, 1], [0, 1]]
    with pytest.raises(ValueError, match="invalid crop bbox"):
        validate_properties_dict(props, _Plans())


def test_sliding_window_masks_no_t2_edema_before_argmax():
    image = np.zeros((3, 2, 4, 4), dtype=np.float32)
    logits, meta = sliding_window_logits(
        _TinyModel(),
        image,
        (1.0, 0.0, 0.0),
        patch_size=(2, 4, 4),
        tile_step_size=0.5,
        use_gaussian=True,
        mirror_axes=(),
        device=torch.device("cpu"),
    )
    assert meta["formal_inference_never_calls_whole_volume_shortcut"] is True
    assert meta["tile_count"] == 1
    assert np.all(logits[4] < -1e30)
    assert np.all(logits[5] == pytest.approx(1.0))
