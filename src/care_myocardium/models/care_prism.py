"""CARE-PRISM v2 architecture primitives.

The shared encoder is built from the real nnU-Net ``ResidualEncoderUNet`` plan
kwargs and receives exactly ``[LGE, T2, C0]``. Availability is consumed only by
private modality paths, routers, and loss masks.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F

from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet


MODALITY_ORDER = ("LGE", "T2", "C0")
PATHOLOGY_ORDER = ("scar", "edema")
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESENC_PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json"


@dataclass(frozen=True)
class CAREPRISMConfig:
    input_channels: int = 3
    num_classes: int = 6
    n_stages: int = 7
    features_per_stage: tuple[int, ...] = (32, 64, 128, 256, 320, 320, 320)
    kernel_sizes: tuple[tuple[int, ...], ...] = (
        (1, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
        (3, 3, 3),
    )
    strides: tuple[tuple[int, ...], ...] = (
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
    conv_bias: bool = True
    shared_weight_floor: float = 0.20
    private_stem_channels: int = 16
    prototype_enabled: bool = False
    slice_correspondence_enabled: bool = False

    @classmethod
    def from_resenc_plans(cls, plans_path: Path | str = DEFAULT_RESENC_PLANS, configuration: str = "3d_fullres") -> "CAREPRISMConfig":
        plans_path = Path(plans_path)
        plans = json.loads(plans_path.read_text(encoding="utf-8"))
        arch = plans["configurations"][configuration]["architecture"]
        if "ResidualEncoderUNet" not in str(arch.get("network_class_name", "")):
            raise ValueError(f"{plans_path} does not describe ResidualEncoderUNet")
        kwargs = arch["arch_kwargs"]
        return cls(
            n_stages=int(kwargs["n_stages"]),
            features_per_stage=tuple(int(v) for v in kwargs["features_per_stage"]),
            kernel_sizes=tuple(tuple(int(x) for x in v) for v in kwargs["kernel_sizes"]),
            strides=tuple(tuple(int(x) for x in v) for v in kwargs["strides"]),
            n_blocks_per_stage=tuple(int(v) for v in kwargs["n_blocks_per_stage"]),
            n_conv_per_stage_decoder=tuple(int(v) for v in kwargs["n_conv_per_stage_decoder"]),
            conv_bias=bool(kwargs.get("conv_bias", True)),
        )

    def nnunet_arch_kwargs(self) -> dict[str, Any]:
        return {
            "input_channels": self.input_channels,
            "n_stages": self.n_stages,
            "features_per_stage": list(self.features_per_stage),
            "conv_op": nn.Conv3d,
            "kernel_sizes": [list(v) for v in self.kernel_sizes],
            "strides": [list(v) for v in self.strides],
            "n_blocks_per_stage": list(self.n_blocks_per_stage),
            "num_classes": self.num_classes,
            "n_conv_per_stage_decoder": list(self.n_conv_per_stage_decoder),
            "conv_bias": self.conv_bias,
            "norm_op": nn.InstanceNorm3d,
            "norm_op_kwargs": {"eps": 1e-5, "affine": True},
            "dropout_op": None,
            "dropout_op_kwargs": None,
            "nonlin": nn.LeakyReLU,
            "nonlin_kwargs": {"inplace": True},
            "deep_supervision": False,
        }


def _norm(channels: int) -> nn.Module:
    return nn.InstanceNorm3d(channels, affine=True)


def _kernel(level: int, config: CAREPRISMConfig) -> tuple[int, int, int]:
    raw = config.kernel_sizes[min(level, len(config.kernel_sizes) - 1)]
    if len(raw) == 2:
        return (1, int(raw[0]), int(raw[1]))
    return tuple(int(v) for v in raw)  # type: ignore[return-value]


def _padding(kernel: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(k // 2 for k in kernel)


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, *, level: int, config: CAREPRISMConfig, dilation: int = 1) -> None:
        super().__init__()
        kernel = _kernel(level, config)
        dilation_tuple = (1, dilation, dilation) if kernel[0] == 1 else (dilation, dilation, dilation)
        padding = tuple((k // 2) * d for k, d in zip(kernel, dilation_tuple))
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel, padding=padding, dilation=dilation_tuple, bias=False),
            _norm(out_channels),
            nn.LeakyReLU(inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel, padding=padding, dilation=dilation_tuple, bias=False),
            _norm(out_channels),
            nn.LeakyReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class PrivatePyramid(nn.Module):
    """Lightweight modality-private pyramid, not a second full backbone."""

    def __init__(self, config: CAREPRISMConfig) -> None:
        super().__init__()
        widths = list(config.features_per_stage[:4])
        self.stem = nn.Sequential(
            nn.Conv3d(1, config.private_stem_channels, _kernel(0, config), padding=_padding(_kernel(0, config)), bias=False),
            _norm(config.private_stem_channels),
            nn.LeakyReLU(inplace=True),
            ConvBlock(config.private_stem_channels, config.private_stem_channels, level=0, config=config),
        )
        stages: list[nn.Module] = []
        in_ch = config.private_stem_channels
        for level, out_ch in enumerate(widths):
            stride = tuple(int(v) for v in config.strides[level])
            stages.append(
                nn.Sequential(
                    nn.Conv3d(in_ch, out_ch, _kernel(level, config), stride=stride, padding=_padding(_kernel(level, config)), bias=False),
                    _norm(out_ch),
                    nn.LeakyReLU(inplace=True),
                    ConvBlock(out_ch, out_ch, level=level, config=config),
                )
            )
            in_ch = out_ch
        self.stages = nn.ModuleList(stages)

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> list[torch.Tensor]:
        y = self.stem(x * present)
        out: list[torch.Tensor] = []
        for stage in self.stages:
            y = stage(y)
            out.append(y)
        return out


class SoftRetrievalRouter(nn.Module):
    def __init__(self, channels: int, *, prefer_modality: int, shared_floor: float) -> None:
        super().__init__()
        self.shared_floor = float(shared_floor)
        hidden = max(16, channels // 4)
        self.mlp = nn.Sequential(
            nn.Linear(channels * 4 + 3, hidden),
            nn.LeakyReLU(inplace=True),
            nn.Linear(hidden, 4),
        )
        with torch.no_grad():
            last = self.mlp[-1]
            assert isinstance(last, nn.Linear)
            last.bias.zero_()
            last.bias[0] = 0.2
            last.bias[1 + int(prefer_modality)] = 1.2

    def forward(
        self,
        shared: torch.Tensor,
        private: tuple[torch.Tensor, torch.Tensor, torch.Tensor],
        availability: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        pooled = [shared.mean(dim=(2, 3, 4)), *(p.mean(dim=(2, 3, 4)) for p in private)]
        logits = self.mlp(torch.cat([*pooled, availability.to(shared)], dim=1))
        available4 = torch.cat([torch.ones_like(availability[:, :1]), availability.to(shared)], dim=1)
        logits = logits.masked_fill(available4 <= 0, -1.0e4)
        raw = torch.softmax(logits, dim=1) * available4
        raw = raw / raw.sum(dim=1, keepdim=True).clamp_min(1.0e-6)
        weights = raw.clone()
        weights[:, 0] = self.shared_floor + (1.0 - self.shared_floor) * raw[:, 0]
        weights[:, 1:] = (1.0 - self.shared_floor) * raw[:, 1:]
        routed = weights[:, 0].view(-1, 1, 1, 1, 1) * shared
        for idx, feat in enumerate(private):
            routed = routed + weights[:, idx + 1].view(-1, 1, 1, 1, 1) * feat
        return routed, weights


class AnatomyDecoder(nn.Module):
    def __init__(self, config: CAREPRISMConfig) -> None:
        super().__init__()
        widths = list(config.features_per_stage[:4])
        self.scale_projections = nn.ModuleList(nn.Conv3d(ch, ch, 1) for ch in widths)
        self.head = nn.Conv3d(widths[0], 3, 1)

    def forward(self, scales: list[torch.Tensor]) -> dict[str, Any]:
        anatomy_scales = [proj(feat) for proj, feat in zip(self.scale_projections, scales[:4])]
        logits = self.head(anatomy_scales[0])
        return {"logits": logits, "scales": anatomy_scales}


class AnatomyToPathologyExchange(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.proj = nn.Conv3d(channels, channels, 1)
        self.gate = nn.Parameter(torch.zeros(1))
        nn.init.zeros_(self.proj.weight)
        nn.init.zeros_(self.proj.bias)

    def forward(self, pathology: torch.Tensor, anatomy: torch.Tensor, *, enabled: bool = True) -> torch.Tensor:
        if not enabled:
            return pathology
        return pathology + self.gate * self.proj(anatomy.detach())


class PrototypeResidual(nn.Module):
    """Optional proposal residual. Disabled by default and zero-initialized."""

    def __init__(self, channels: int, momentum: float = 0.95) -> None:
        super().__init__()
        self.momentum = float(momentum)
        self.gate = nn.Parameter(torch.zeros(1))
        self.register_buffer("positive", torch.zeros(channels))
        self.register_buffer("count", torch.zeros(1))
        self.proj = nn.Conv3d(1, 1, 1)
        nn.init.zeros_(self.proj.weight)
        nn.init.zeros_(self.proj.bias)

    def forward(self, features: torch.Tensor, *, enabled: bool) -> torch.Tensor:
        if not enabled or float(self.count.detach().cpu()[0]) <= 0.0:
            return features.new_zeros((features.shape[0], 1, *features.shape[-3:]))
        proto = F.normalize(self.positive.to(features), dim=0)
        sim = (F.normalize(features, dim=1) * proto.view(1, -1, 1, 1, 1)).sum(dim=1, keepdim=True)
        return self.gate * self.proj(sim)

    @torch.no_grad()
    def update_after_step(self, features: torch.Tensor, mask: torch.Tensor) -> None:
        if mask.sum() <= 0:
            return
        pooled = (features.detach() * mask).sum(dim=(0, 2, 3, 4)) / mask.sum().clamp_min(1.0)
        if self.count.item() == 0:
            self.positive.copy_(pooled)
        else:
            self.positive.mul_(self.momentum).add_(pooled * (1.0 - self.momentum))
        self.count.add_(1)

    def state_payload(self) -> dict[str, Any]:
        return {"momentum": self.momentum, "positive": self.positive.detach().cpu(), "count": self.count.detach().cpu()}


class PathologyRefiner(nn.Module):
    def __init__(self, channels: int, anatomy_channels: int, *, scar_like: bool, config: CAREPRISMConfig) -> None:
        super().__init__()
        self.positive_head = nn.Conv3d(channels, 1, 1)
        self.negative_head = nn.Conv3d(channels, 4, 1)
        self.proposal_head = nn.Conv3d(channels + 1 + 4, 1, 1)
        self.prototype = PrototypeResidual(channels)
        layers: list[nn.Module] = [
            ConvBlock(channels + anatomy_channels + 1 + 1 + 4, channels, level=0, config=config),
        ]
        if not scar_like:
            layers.extend([ConvBlock(channels, channels, level=0, config=config, dilation=2), ConvBlock(channels, channels, level=0, config=config, dilation=3)])
        self.refiner = nn.Sequential(*layers)
        self.final_head = nn.Conv3d(channels, 1, 1)
        self.burden_head = nn.Sequential(nn.AdaptiveAvgPool3d(1), nn.Flatten(), nn.Linear(channels, 4))
        self.ratio_head = nn.Sequential(nn.AdaptiveAvgPool3d(1), nn.Flatten(), nn.Linear(channels, 1))

    def forward(
        self,
        routed0: torch.Tensor,
        anatomy0: torch.Tensor,
        anatomy_band: torch.Tensor,
        *,
        prototype_enabled: bool,
        disable_proposal: bool = False,
        disable_negative: bool = False,
    ) -> dict[str, torch.Tensor]:
        positive = self.positive_head(routed0)
        negative = self.negative_head(routed0)
        if disable_negative:
            negative = torch.zeros_like(negative)
        proto = self.prototype(routed0, enabled=prototype_enabled)
        proposal_input = torch.cat([routed0, positive + proto, negative], dim=1)
        proposal_logit = self.proposal_head(proposal_input)
        if disable_proposal:
            proposal_attention = torch.ones_like(proposal_logit)
        else:
            proposal_attention = 0.25 + 0.75 * torch.sigmoid(proposal_logit)
        refiner_input = torch.cat([routed0, anatomy0.detach(), anatomy_band.detach(), proposal_attention, negative], dim=1)
        refined = self.refiner(refiner_input)
        final = self.final_head(refined)
        return {
            "positive_logit": positive,
            "negative_logits": negative,
            "prototype_residual": proto,
            "proposal_logit": proposal_logit,
            "proposal_attention": proposal_attention,
            "final_logit": final,
            "features": refined,
            "burden_logits": self.burden_head(routed0),
            "log_ratio": self.ratio_head(routed0),
        }


class CAREPRISM(nn.Module):
    input_channel_order = MODALITY_ORDER

    def __init__(self, config: CAREPRISMConfig | None = None) -> None:
        super().__init__()
        self.config = config or CAREPRISMConfig.from_resenc_plans()
        source = ResidualEncoderUNet(**self.config.nnunet_arch_kwargs())
        self.shared_encoder = source.encoder
        self.private_pyramids = nn.ModuleList(PrivatePyramid(self.config) for _ in MODALITY_ORDER)
        widths = list(self.config.features_per_stage[:4])
        self.scar_routers = nn.ModuleList(SoftRetrievalRouter(ch, prefer_modality=0, shared_floor=self.config.shared_weight_floor) for ch in widths)
        self.edema_routers = nn.ModuleList(SoftRetrievalRouter(ch, prefer_modality=1, shared_floor=self.config.shared_weight_floor) for ch in widths)
        self.anatomy_decoder = AnatomyDecoder(self.config)
        self.scar_exchange = nn.ModuleList(AnatomyToPathologyExchange(ch) for ch in widths)
        self.edema_exchange = nn.ModuleList(AnatomyToPathologyExchange(ch) for ch in widths)
        self.scar_refiner = PathologyRefiner(widths[0], widths[0], scar_like=True, config=self.config)
        self.edema_refiner = PathologyRefiner(widths[0], widths[0], scar_like=False, config=self.config)

    @property
    def full_backbone_count(self) -> int:
        return 1

    def forward(
        self,
        images: torch.Tensor,
        availability: torch.Tensor,
        *,
        disable_router: bool = False,
        disable_anatomy_exchange: bool = False,
        disable_proposal: bool = False,
        disable_negative: bool = False,
        prototype_enabled: bool | None = None,
        slice_correspondence_enabled: bool | None = None,
    ) -> dict[str, Any]:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError("CARE-PRISM shared encoder input must be [B,3,D,H,W] in LGE,T2,C0 order")
        availability = availability.to(device=images.device, dtype=images.dtype)
        if availability.ndim != 2 or availability.shape[1] != 3:
            raise ValueError("availability must be [B,3] in LGE,T2,C0 order")
        masked = images * availability.view(-1, 3, 1, 1, 1)
        shared_scales = list(self.shared_encoder(masked))
        private = [p(masked[:, i : i + 1], availability[:, i : i + 1].view(-1, 1, 1, 1, 1)) for i, p in enumerate(self.private_pyramids)]
        private_by_level = [tuple(p[level] for p in private) for level in range(4)]
        scar_routed: list[torch.Tensor] = []
        edema_routed: list[torch.Tensor] = []
        scar_weights: list[torch.Tensor] = []
        edema_weights: list[torch.Tensor] = []
        for level in range(4):
            if disable_router:
                w = images.new_tensor([[1.0, 0.0, 0.0, 0.0]]).expand(images.shape[0], -1)
                scar = shared_scales[level]
                edema = shared_scales[level]
                scar_w = w
                edema_w = w
            else:
                scar, scar_w = self.scar_routers[level](shared_scales[level], private_by_level[level], availability)
                edema, edema_w = self.edema_routers[level](shared_scales[level], private_by_level[level], availability)
            scar_routed.append(scar)
            edema_routed.append(edema)
            scar_weights.append(scar_w)
            edema_weights.append(edema_w)
        anatomy = self.anatomy_decoder(shared_scales)
        scar_exchanged = [
            exchange(feat, anatomy["scales"][level], enabled=not disable_anatomy_exchange)
            for level, (exchange, feat) in enumerate(zip(self.scar_exchange, scar_routed))
        ]
        edema_exchanged = [
            exchange(feat, anatomy["scales"][level], enabled=not disable_anatomy_exchange)
            for level, (exchange, feat) in enumerate(zip(self.edema_exchange, edema_routed))
        ]
        union_probability = torch.sigmoid(anatomy["logits"][:, 0:1]).detach()
        anatomy_band = 0.25 + 0.75 * F.max_pool3d(union_probability, kernel_size=3, stride=1, padding=1)
        use_proto = self.config.prototype_enabled if prototype_enabled is None else bool(prototype_enabled)
        _ = self.config.slice_correspondence_enabled if slice_correspondence_enabled is None else bool(slice_correspondence_enabled)
        scar = self.scar_refiner(
            scar_exchanged[0],
            anatomy["scales"][0],
            anatomy_band,
            prototype_enabled=use_proto,
            disable_proposal=disable_proposal,
            disable_negative=disable_negative,
        )
        edema_raw = self.edema_refiner(
            edema_exchanged[0],
            anatomy["scales"][0],
            anatomy_band,
            prototype_enabled=use_proto,
            disable_proposal=disable_proposal,
            disable_negative=disable_negative,
        )
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1)
        edema = {k: (v * t2 if torch.is_tensor(v) and v.ndim == 5 else v * availability[:, 1:2] if torch.is_tensor(v) and v.ndim == 2 else v) for k, v in edema_raw.items()}
        scar_prob = torch.sigmoid(scar["final_logit"])
        edema_prob = torch.sigmoid(edema_raw["final_logit"]) * t2
        return {
            "shared_encoder_input": masked,
            "shared_scales": shared_scales,
            "private_scales": private,
            "anatomy_logits": anatomy["logits"],
            "anatomy_scales": anatomy["scales"],
            "anatomy_band": anatomy_band,
            "scar": scar,
            "edema": edema,
            "scar_direct_logit": scar["final_logit"],
            "edema_zone_direct_logit": edema["final_logit"],
            "scar_probability": scar_prob,
            "edema_probability": edema_prob,
            "edema_mask": (edema_prob > 0.5).to(dtype=images.dtype) * t2,
            "scar_router_weights": scar_weights,
            "edema_router_weights": edema_weights,
            "prototype_enabled": use_proto,
            "slice_correspondence_enabled": bool(slice_correspondence_enabled or False),
        }


def build_care_prism(config: CAREPRISMConfig | None = None) -> CAREPRISM:
    return CAREPRISM(config)


def build_source_resenc(config: CAREPRISMConfig) -> ResidualEncoderUNet:
    return ResidualEncoderUNet(**config.nnunet_arch_kwargs())


def trainable_parameter_count(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def resolve_symbol(dotted: str) -> Any:
    module, name = dotted.rsplit(".", 1)
    return getattr(importlib.import_module(module), name)
