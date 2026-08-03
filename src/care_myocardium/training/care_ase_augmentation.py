"""CARE-ASE binding to the Dataset501 stock nnU-Net augmentation contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch

from batchgeneratorsv2.transforms.utils.compose import ComposeTransforms

from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager


@dataclass(frozen=True)
class CAREASEStockAugmentationContract:
    plans_path: str
    configuration: str
    trainer_class: str
    trainer_source_path: str
    trainer_source_sha256: str
    final_patch_size: tuple[int, int, int]
    initial_patch_size: tuple[int, int, int]
    dummy_2d: bool
    rotation_for_DA: tuple[float, float]
    scale_range: tuple[float, float]
    mirror_axes: tuple[int, ...]
    spatial_transform_random_crop: bool
    spatial_transform_center_dist_from_border: int
    spatial_padding_value_seg: int
    foreground_oversampling_behavior: str
    deep_supervision_target_transform_ordering: str
    intensity_transform_ordering: tuple[str, ...]
    z_axis_semantics: str
    care_padding_restore_policy: str

    def sha256(self) -> str:
        data = json.dumps(asdict(self), sort_keys=True).encode("utf-8")
        return hashlib.sha256(data).hexdigest()


class _TrainerProbe(nnUNetTrainer):
    def __init__(self) -> None:
        pass

    def print_to_log_file(self, *args: Any, **kwargs: Any) -> None:
        return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_stock_transform_and_metadata(plans_path: Path, *, configuration: str = "3d_fullres") -> tuple[Any, PlansManager, Any, tuple[float, float], bool, np.ndarray, tuple[int, ...]]:
    plans = load_json(str(plans_path))
    plans_manager = PlansManager(plans)
    configuration_manager = plans_manager.get_configuration(configuration)
    probe = _TrainerProbe()
    probe.configuration_manager = configuration_manager
    rotation_for_DA, do_dummy_2d_data_aug, initial_patch_size, mirror_axes = probe.configure_rotation_dummyDA_mirroring_and_inital_patch_size()
    transform = nnUNetTrainer.get_training_transforms(
        np.asarray(configuration_manager.patch_size),
        rotation_for_DA,
        None,
        mirror_axes,
        do_dummy_2d_data_aug,
        configuration_manager.use_mask_for_norm,
        False,
        None,
        None,
        -1,
    )
    return transform, plans_manager, configuration_manager, rotation_for_DA, bool(do_dummy_2d_data_aug), np.asarray(initial_patch_size), tuple(int(v) for v in mirror_axes)


def build_stock_training_transform_preserve_ignore(plans_path: Path, *, configuration: str = "3d_fullres") -> Any:
    """Return the real stock nnU-Net training transform, except CARE keeps seg==-1 as ignore.

    nnU-Net appends RemoveLabelTransform(-1, 0) for its standard CE target. CARE-ASE
    needs padding to remain ignore through all auxiliary targets, so the transform chain
    is otherwise stock but without that terminal label-removal transform.
    """

    transform, *_ = _build_stock_transform_and_metadata(plans_path, configuration=configuration)
    if not isinstance(transform, ComposeTransforms):
        return transform
    kept = [
        item
        for item in transform.transforms
        if item.__class__.__name__ not in {"RemoveLabelTransform", "RemoveLabelTansform"}
    ]
    return ComposeTransforms(kept)


def build_stock_augmentation_contract(plans_path: Path, *, configuration: str = "3d_fullres") -> CAREASEStockAugmentationContract:
    transform, _plans_manager, configuration_manager, rotation_for_DA, do_dummy_2d_data_aug, initial_patch_size, mirror_axes = (
        _build_stock_transform_and_metadata(plans_path, configuration=configuration)
    )
    source_path = Path(inspect.getsourcefile(nnUNetTrainer) or "")
    return CAREASEStockAugmentationContract(
        plans_path=str(plans_path),
        configuration=str(configuration),
        trainer_class="nnunetv2.training.nnUNetTrainer.nnUNetTrainer.nnUNetTrainer",
        trainer_source_path=str(source_path),
        trainer_source_sha256=_sha256_file(source_path),
        final_patch_size=tuple(int(v) for v in configuration_manager.patch_size),
        initial_patch_size=tuple(int(v) for v in np.asarray(initial_patch_size).tolist()),
        dummy_2d=bool(do_dummy_2d_data_aug),
        rotation_for_DA=tuple(float(v) for v in rotation_for_DA),
        scale_range=(0.7, 1.4),
        mirror_axes=tuple(int(v) for v in mirror_axes),
        spatial_transform_random_crop=False,
        spatial_transform_center_dist_from_border=0,
        spatial_padding_value_seg=-1,
        foreground_oversampling_behavior="CARE-ASE sampler supplies focused coordinate; stock spatial transform uses random_crop=False around initial patch",
        deep_supervision_target_transform_ordering="stock DownsampleSegForDSTransform is last when deep_supervision_scales are provided",
        intensity_transform_ordering=(
            "GaussianNoise",
            "GaussianBlur",
            "MultiplicativeBrightness",
            "Contrast",
            "SimulateLowResolution",
            "GammaInvert",
            "Gamma",
            "Mirror",
        ),
        z_axis_semantics="dummy_2d converts 3D to 2D for spatial transform; z index is not mixed by spatial rotation/scaling for Dataset501 final patch",
        care_padding_restore_policy="stock transform uses padding_value_seg=-1 for spatial padding; CARE-ASE target builder preserves seg==-1 as ignore even though stock validation transform may remove labels",
    )


def apply_stock_training_transform_preserve_ignore(
    image_patch: np.ndarray,
    seg_patch: np.ndarray,
    *,
    transform: Any,
    availability: tuple[int, ...] | list[int] | np.ndarray,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    image, seg, _regression, _extra = apply_stock_training_transform_with_targets(
        image_patch,
        seg_patch,
        transform=transform,
        availability=availability,
        seed=seed,
    )
    return image, seg


def apply_stock_training_transform_with_targets(
    image_patch: np.ndarray,
    seg_patch: np.ndarray,
    *,
    transform: Any,
    availability: tuple[int, ...] | list[int] | np.ndarray,
    regression_target_patch: np.ndarray | None = None,
    segmentation_extra_patch: np.ndarray | None = None,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray | None]:
    if image_patch.ndim != 4:
        raise ValueError(f"image_patch must be CxZxHxW, got shape {image_patch.shape}")
    if seg_patch.ndim != 3:
        raise ValueError(f"seg_patch must be ZxHxW, got shape {seg_patch.shape}")
    seg_channels = [seg_patch[None]]
    if segmentation_extra_patch is not None:
        extra = np.asarray(segmentation_extra_patch)
        if extra.ndim != 4:
            raise ValueError(f"segmentation_extra_patch must be CxZxHxW, got shape {extra.shape}")
        seg_channels.append(extra)
    data = {
        "image": torch.from_numpy(np.ascontiguousarray(image_patch)).float(),
        "segmentation": torch.from_numpy(np.ascontiguousarray(np.concatenate(seg_channels, axis=0))).long(),
    }
    if regression_target_patch is not None:
        regression = np.asarray(regression_target_patch, dtype=np.float32)
        if regression.ndim != 4:
            raise ValueError(f"regression_target_patch must be CxZxHxW, got shape {regression.shape}")
        data["regression_target"] = torch.from_numpy(np.ascontiguousarray(regression)).float()
    if seed is None:
        out = transform(**data)
    else:
        py_state = random.getstate()
        np_state = np.random.get_state()
        torch_state = torch.random.get_rng_state()
        cuda_state = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
        try:
            seed_int = int(seed) % (2**32)
            random.seed(seed_int)
            np.random.seed(seed_int)
            torch.manual_seed(seed_int)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed_int)
            out = transform(**data)
        finally:
            random.setstate(py_state)
            np.random.set_state(np_state)
            torch.random.set_rng_state(torch_state)
            if cuda_state is not None:
                torch.cuda.set_rng_state_all(cuda_state)
    image = out["image"].detach().cpu().numpy().astype(np.float32, copy=False)
    segmentation = out["segmentation"].detach().cpu().numpy().astype(np.int64, copy=False)
    seg = segmentation[0]
    extra_out = segmentation[1:] if segmentation.shape[0] > 1 else None
    regression_out = None
    if out.get("regression_target") is not None:
        regression_out = out["regression_target"].detach().cpu().numpy().astype(np.float32, copy=False)
    avail = np.asarray(availability, dtype=np.float32).reshape(-1)
    for channel, present in enumerate(avail[: image.shape[0]]):
        if present <= 0:
            image[channel] = 0.0
    return (
        np.ascontiguousarray(image),
        np.ascontiguousarray(seg),
        None if regression_out is None else np.ascontiguousarray(regression_out),
        None if extra_out is None else np.ascontiguousarray(extra_out),
    )
