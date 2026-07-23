"""CARE Batch9 reliable-label multimodal direct segmentation model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from torch import nn
from torch.nn import functional as F

from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet


@dataclass(frozen=True)
class ResEncMConfig:
    feature_channels: int = 32
    stem_channels: int = 8
    no_t2_edema_logit: float = -20.0
    deep_supervision: bool = False
    n_stages: int = 7
    features_per_stage: tuple[int, ...] = (32, 64, 128, 256, 320, 320, 320)
    kernel_sizes: tuple[tuple[int, int, int], ...] = (
        (1, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
    )
    strides: tuple[tuple[int, int, int], ...] = (
        (1, 1, 1),
        (1, 2, 2),
        (2, 2, 2),
        (2, 2, 2),
        (1, 2, 2),
        (1, 2, 2),
        (1, 2, 2),
    )
    n_blocks_per_stage: tuple[int, ...] = (1, 3, 4, 6, 6, 6, 6)
    n_conv_per_stage_decoder: tuple[int, ...] = (1, 1, 1, 1, 1, 1)


class _ModalityStem(nn.Module):
    def __init__(self, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(1, out_channels, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm3d(out_channels, affine=True),
            nn.GELU(),
        )

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> torch.Tensor:
        y = self.net(x)
        return y * present


class CAREMMReliableDistillResEnc(nn.Module):
    """Direct MyoPS segmenter with modality stems and final-logit pathology heads.

    Input channel order is fixed to [LGE, T2, C0]. The center id is deliberately
    absent from the forward signature.
    """

    input_channel_order = ("LGE", "T2", "C0")
    forbidden_legacy_components = (
        "SRRProposeRefineMyoPS",
        "ProposalDictionary",
        "M10TwoPassSpatialDictionary",
        "M10CrossFittedPrototypeMemory",
        "CropSoftROIRefinementHead",
        "DifferentiableSoftROIRefinementHead",
        "PathologySourceArbiter",
        "BranchArbitrationGate",
        "BaselinePreservingResidualGate",
    )

    def __init__(self, config: ResEncMConfig | None = None) -> None:
        super().__init__()
        self.config = config or ResEncMConfig()
        c = self.config
        self.stems = nn.ModuleList([_ModalityStem(c.stem_channels) for _ in range(3)])
        self.feature_backbone = ResidualEncoderUNet(
            input_channels=3 * c.stem_channels + 3,
            n_stages=c.n_stages,
            features_per_stage=list(c.features_per_stage),
            conv_op=nn.Conv3d,
            kernel_sizes=[list(v) for v in c.kernel_sizes],
            strides=[list(v) for v in c.strides],
            n_blocks_per_stage=list(c.n_blocks_per_stage),
            num_classes=c.feature_channels,
            n_conv_per_stage_decoder=list(c.n_conv_per_stage_decoder),
            conv_bias=True,
            norm_op=nn.InstanceNorm3d,
            norm_op_kwargs={"eps": 1e-5, "affine": True},
            dropout_op=None,
            dropout_op_kwargs=None,
            nonlin=nn.LeakyReLU,
            nonlin_kwargs={"inplace": True},
            deep_supervision=bool(c.deep_supervision),
        )
        self.anatomy_head = nn.Conv3d(c.feature_channels, 4, kernel_size=1)
        self.scar_head = nn.Conv3d(c.feature_channels, 1, kernel_size=1)
        self.edema_head = nn.Conv3d(c.feature_channels, 1, kernel_size=1)

    @property
    def parameter_count(self) -> int:
        return int(sum(p.numel() for p in self.parameters()))

    def forward(
        self,
        x: torch.Tensor,
        availability: torch.Tensor,
        *,
        force_no_t2_edema_logit: bool = True,
        return_features: bool = True,
    ) -> dict[str, torch.Tensor]:
        if x.ndim != 5 or x.shape[1] != 3:
            raise ValueError(f"expected input shape [B,3,D,H,W], got {tuple(x.shape)}")
        availability = _availability_5d(availability, x)
        stem_features = [
            stem(x[:, i : i + 1], availability[:, i : i + 1])
            for i, stem in enumerate(self.stems)
        ]
        avail_channels = availability.expand(-1, -1, *x.shape[2:]).to(dtype=x.dtype)
        fused = torch.cat([*stem_features, avail_channels], dim=1)
        features = self.feature_backbone(fused)
        deep_features = list(features) if isinstance(features, (list, tuple)) else []
        features = deep_features[0] if deep_features else features
        anatomy_logits = self.anatomy_head(features)
        scar_residual = self.scar_head(features)
        edema_residual = self.edema_head(features)
        six_class_logits = compose_six_class_logits(
            anatomy_logits,
            scar_residual,
            edema_residual,
            availability=availability,
            no_t2_edema_logit=self.config.no_t2_edema_logit,
            force_no_t2_edema_logit=force_no_t2_edema_logit,
        )
        out = {
            "anatomy_logits": anatomy_logits,
            "scar_residual": scar_residual,
            "edema_residual": edema_residual,
            "six_class_logits": six_class_logits,
            "stem_lge": stem_features[0],
            "stem_t2": stem_features[1],
            "stem_c0": stem_features[2],
            "availability": availability,
        }
        if return_features:
            out["features"] = features
        if deep_features:
            out["deep_supervision"] = [
                {
                    "anatomy_logits": self.anatomy_head(feat),
                    "scar_residual": self.scar_head(feat),
                    "edema_residual": self.edema_head(feat),
                    "features": feat,
                    "six_class_logits": compose_six_class_logits(
                        self.anatomy_head(feat),
                        self.scar_head(feat),
                        self.edema_head(feat),
                        availability=availability,
                        no_t2_edema_logit=self.config.no_t2_edema_logit,
                        force_no_t2_edema_logit=force_no_t2_edema_logit,
                    ),
                }
                for feat in deep_features[1:]
            ]
        return out

    def contract(self) -> dict[str, Any]:
        c = self.config
        return {
            "model_class": self.__class__.__name__,
            "input_channel_order": list(self.input_channel_order),
            "modality_stem_channels_each": c.stem_channels,
            "fused_input_channels": 3 * c.stem_channels + 3,
            "backbone_symbol": "dynamic_network_architectures.architectures.unet.ResidualEncoderUNet",
            "plans_equivalent": "nnUNetResEncUNetMPlans",
            "features_per_stage": list(c.features_per_stage),
            "kernel_sizes": [list(v) for v in c.kernel_sizes],
            "strides": [list(v) for v in c.strides],
            "n_blocks_per_stage": list(c.n_blocks_per_stage),
            "n_conv_per_stage_decoder": list(c.n_conv_per_stage_decoder),
            "feature_channels": c.feature_channels,
            "deep_supervision": c.deep_supervision,
            "parameter_count": self.parameter_count,
            "center_in_forward_signature": False,
            "forbidden_legacy_components": list(self.forbidden_legacy_components),
        }


def _availability_5d(availability: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    if availability.ndim == 2:
        availability = availability[:, :, None, None, None]
    if availability.ndim != 5 or availability.shape[1] != 3:
        raise ValueError(f"expected availability [B,3] or [B,3,1,1,1], got {tuple(availability.shape)}")
    return availability.to(device=x.device, dtype=x.dtype)


def compose_six_class_logits(
    anatomy_logits: torch.Tensor,
    scar_residual: torch.Tensor,
    edema_residual: torch.Tensor,
    *,
    availability: torch.Tensor | None = None,
    no_t2_edema_logit: float = -20.0,
    force_no_t2_edema_logit: bool = True,
) -> torch.Tensor:
    if anatomy_logits.shape[1] != 4:
        raise ValueError("anatomy logits must have four channels")
    z_bg = anatomy_logits[:, 0:1]
    z_myo = anatomy_logits[:, 1:2]
    z_lv = anatomy_logits[:, 2:3]
    z_rv = anatomy_logits[:, 3:4]
    z_edema = z_myo + edema_residual
    z_scar = z_myo + scar_residual
    logits = torch.cat([z_bg, z_myo, z_lv, z_rv, z_edema, z_scar], dim=1)
    if force_no_t2_edema_logit and availability is not None:
        availability = _availability_5d(availability, anatomy_logits)
        t2_present = availability[:, 1:2]
        replacement = torch.full_like(logits[:, 4:5], float(no_t2_edema_logit))
        logits = torch.cat(
            [logits[:, :4], torch.where(t2_present > 0.5, logits[:, 4:5], replacement), logits[:, 5:6]],
            dim=1,
        )
    return logits


def final_margin_logits(six_class_logits: torch.Tensor) -> dict[str, torch.Tensor]:
    scar_negative = torch.logsumexp(six_class_logits[:, 0:5], dim=1, keepdim=True)
    edema_negative = torch.logsumexp(
        torch.cat([six_class_logits[:, 0:4], six_class_logits[:, 5:6]], dim=1),
        dim=1,
        keepdim=True,
    )
    return {
        "scar": six_class_logits[:, 5:6] - scar_negative,
        "edema": six_class_logits[:, 4:5] - edema_negative,
    }




def decode_six_class_logits(
    six_class_logits: torch.Tensor,
    availability: torch.Tensor | None = None,
    *,
    no_t2_edema_hard_mask: bool = True,
) -> torch.Tensor:
    logits = six_class_logits
    if no_t2_edema_hard_mask and availability is not None:
        availability = _availability_5d(availability, six_class_logits)
        no_t2 = availability[:, 1:2] <= 0.5
        if bool(no_t2.any()):
            logits = logits.clone()
            logits[:, 4:5] = torch.where(
                no_t2,
                torch.full_like(logits[:, 4:5], -torch.finfo(logits.dtype).max),
                logits[:, 4:5],
            )
    return logits.argmax(1)


def pad_to_stride(x: torch.Tensor, divisibility: tuple[int, int, int] = (4, 64, 64)) -> tuple[torch.Tensor, tuple[int, int, int]]:
    pads: list[int] = []
    added: list[int] = []
    for size, div in zip(reversed(x.shape[-3:]), reversed(divisibility)):
        extra = (div - size % div) % div
        pads.extend([0, extra])
        added.append(extra)
    if any(added):
        x = F.pad(x, pads)
    return x, tuple(reversed(added))


def crop_from_pad(x: torch.Tensor, added: tuple[int, int, int]) -> torch.Tensor:
    d, h, w = x.shape[-3:]
    ad, ah, aw = added
    return x[..., : d - ad if ad else d, : h - ah if ah else h, : w - aw if aw else w]
