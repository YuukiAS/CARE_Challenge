from __future__ import annotations

from torch import nn

from myops.models.coarse_net import CoarseNet
from myops.models.fine_path_net import FinePathNet
from myops.models.cine_hybrid_net import CineHybridNet


def build_model(
    stage: str,
    track: str,
    arch: str,
    in_channels: int,
    out_channels: int,
    base_channels: int,
    deep_supervision: bool,
    **kwargs,
) -> nn.Module:
    # "2d_earlyfusion" is the fine-stage ablation baseline: one shared encoder over
    # channel-stacked sequences instead of modality-decoupled encoders + alignment.
    if stage == "coarse" or arch in ("2d_coarse", "2d_earlyfusion"):
        return CoarseNet(
            in_channels=in_channels,
            out_channels=out_channels,
            base_channels=base_channels,
            deep_supervision=deep_supervision,
        )
    if arch == "2d_multi":
        return FinePathNet(
            out_channels=out_channels,
            base_channels=base_channels,
            deep_supervision=deep_supervision,
            grid_size=int(kwargs.get("grid_size", 4)),
            span_range=float(kwargs.get("span_range", 0.98)),
            image_size=int(kwargs.get("image_size", 192)),
            use_tps=bool(kwargs.get("use_tps", True)),
            use_spg=bool(kwargs.get("use_spg", True)),
            use_consistency=bool(kwargs.get("use_consistency", True)),
            use_t2_aux=bool(kwargs.get("use_t2_aux", False)),
        )
    if arch == "cine_hybrid":
        return CineHybridNet(
            out_channels=out_channels,
            base_channels=base_channels,
            num_frames=int(kwargs.get("num_frames", kwargs.get("max_cine_frames", 20))),
            max_displacement=float(kwargs.get("max_displacement", 0.25)),
            pathology_input=str(kwargs.get("pathology_input", "flow")),
        )
    raise ValueError(f"Unknown arch: {arch}")
