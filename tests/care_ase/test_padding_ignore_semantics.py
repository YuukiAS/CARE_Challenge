import numpy as np
import torch

from scripts.training.care_ase.run_care_ase_r2_chunk import crop_or_pad
from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import build_care_ase_targets, care_ase_loss


def test_segmentation_padding_is_ignore_not_background():
    seg = np.zeros((1, 4, 8, 8), dtype=np.int64)
    cropped = crop_or_pad(seg, center=(-2, 2, 2), patch_size=(6, 10, 10), pad_value=-1)[0]

    assert int((cropped == -1).sum()) > 0
    assert cropped[0, 0, 0] == -1


def test_padding_voxels_are_invalid_for_targets_and_loss():
    model = build_care_ase_for_fold(2)
    image = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    seg[:, :2] = -1
    outputs = model(image, availability, global_step=0)
    targets = build_care_ase_targets(seg, availability, outputs, {"spacing": torch.ones(1, 3)})
    loss, metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability, "spacing": torch.ones(1, 3)})

    assert torch.isfinite(loss)
    assert float(targets["valid_label_mask"][:, :, :2].sum()) == 0.0
    assert int((targets["scar_context_target"][:, :2] >= 0).sum()) == 0
    assert int((targets["edema_context_target"][:, :2] >= 0).sum()) == 0
    assert metrics["all_finite"] == 1.0
