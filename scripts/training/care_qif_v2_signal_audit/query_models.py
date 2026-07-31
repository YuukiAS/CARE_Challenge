#!/usr/bin/env python3
"""CARE-QIF v2 scar dense/query model definitions."""

from __future__ import annotations

import math
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F


class DeterministicIntensityChannels(nn.Module):
    """Pass-through holder for deterministic LGE rank/contrast channels."""

    def forward(self, channels: torch.Tensor) -> torch.Tensor:
        if channels.ndim != 5 or channels.shape[1] < 2:
            raise ValueError("deterministic channels must be [B,C,Z,Y,X] with rank and contrast")
        return channels.float()


class ResidualBlock3d(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(channels, channels, 3, padding=1),
            nn.GroupNorm(8, channels),
            nn.SiLU(inplace=True),
            nn.Conv3d(channels, channels, 3, padding=1),
            nn.GroupNorm(8, channels),
        )
        self.act = nn.SiLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.net(x))


class ConvNeXtBlock3d(nn.Module):
    def __init__(self, channels: int = 64) -> None:
        super().__init__()
        self.dw = nn.Conv3d(channels, channels, 3, padding=1, groups=channels)
        self.norm = nn.GroupNorm(8, channels)
        self.pw1 = nn.Conv3d(channels, channels * 3, 1)
        self.pw2 = nn.Conv3d(channels * 3, channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.dw(x)
        y = self.norm(y)
        y = F.silu(self.pw1(y))
        y = self.pw2(y)
        return x + y


class CommonScarFeatureStem(nn.Module):
    """Common F0/F1/context/intensity stem shared by dense and query arms."""

    def __init__(self, f0_channels: int, f1_channels: int, deterministic_channels: int = 2) -> None:
        super().__init__()
        self.f0_proj = nn.Conv3d(f0_channels, 64, 1)
        self.f1_proj = nn.Conv3d(f1_channels, 32, 1)
        in_channels = 64 + 32 + 2 + deterministic_channels
        self.fuse = nn.Sequential(
            nn.Conv3d(in_channels, 64, 3, padding=1),
            nn.GroupNorm(8, 64),
            nn.SiLU(inplace=True),
            ResidualBlock3d(64),
            ResidualBlock3d(64),
        )

    def forward(self, f0: torch.Tensor, f1: torch.Tensor, p_myo: torch.Tensor, p_lv: torch.Tensor, intensity_channels: torch.Tensor) -> torch.Tensor:
        spatial = tuple(int(v) for v in f0.shape[-3:])
        f0p = self.f0_proj(f0.float())
        f1p = F.interpolate(self.f1_proj(f1.float()), size=spatial, mode="trilinear", align_corners=False)
        ctx = torch.cat([p_myo.float(), p_lv.float(), intensity_channels.float()], dim=1)
        if tuple(ctx.shape[-3:]) != spatial:
            ctx = F.interpolate(ctx, size=spatial, mode="trilinear", align_corners=False)
        return self.fuse(torch.cat([f0p, f1p, ctx], dim=1))


class DenseParameterMatchedControl(nn.Module):
    """Dense scar control with the exact common input contract."""

    def __init__(self, f0_channels: int, f1_channels: int) -> None:
        super().__init__()
        self.common_stem = CommonScarFeatureStem(f0_channels, f1_channels)
        self.blocks = nn.Sequential(*(ConvNeXtBlock3d(64) for _ in range(4)))
        self.dense_head = nn.Conv3d(64, 1, 1)
        self.stock_scar_logit_used = False

    def forward(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        feat = self.common_stem(batch["f0"], batch["f1"], batch["p_myo"], batch["p_lv"], batch["intensity_channels"])
        dense_logit = self.dense_head(self.blocks(feat))
        return {"dense_logit": dense_logit, "final_logit": dense_logit, "final_prob": torch.sigmoid(dense_logit), "mask_feature": feat}


class ScarComponentQueryHead(nn.Module):
    """Q=32 lesion/no-object query head with final-label contribution."""

    def __init__(self, f0_channels: int, f1_channels: int, query_count: int = 32, d_model: int = 128) -> None:
        super().__init__()
        self.query_count = int(query_count)
        self.common_stem = CommonScarFeatureStem(f0_channels, f1_channels)
        self.dense_blocks = nn.Sequential(*(ConvNeXtBlock3d(64) for _ in range(4)))
        self.dense_head = nn.Conv3d(64, 1, 1)
        self.token_proj = nn.Conv3d(f1_channels, d_model, 1)
        layer = nn.TransformerDecoderLayer(d_model=d_model, nhead=8, dim_feedforward=512, dropout=0.1, batch_first=True)
        self.decoder = nn.TransformerDecoder(layer, num_layers=2)
        self.queries = nn.Embedding(self.query_count, d_model)
        self.class_head = nn.Linear(d_model, 2)
        self.center_head = nn.Sequential(nn.Linear(d_model, d_model), nn.SiLU(), nn.Linear(d_model, 3), nn.Sigmoid())
        self.mask_embedding = nn.Linear(d_model, 64)
        self.stock_scar_logit_used = False

    def forward(self, batch: dict[str, torch.Tensor], *, disable_queries: bool = False) -> dict[str, torch.Tensor]:
        common = self.common_stem(batch["f0"], batch["f1"], batch["p_myo"], batch["p_lv"], batch["intensity_channels"])
        dense_logit = self.dense_head(self.dense_blocks(common))
        tokens = self.token_proj(batch["f1"].float())
        pooled = F.adaptive_avg_pool3d(tokens, output_size=(min(int(tokens.shape[-3]), 8), 16, 16))
        memory = pooled.flatten(2).transpose(1, 2)
        q = self.queries.weight.unsqueeze(0).expand(tokens.shape[0], -1, -1)
        decoded = self.decoder(q, memory)
        class_logits = self.class_head(decoded)
        centers = self.center_head(decoded)
        mask_embed = self.mask_embedding(decoded)
        mask_logits = torch.einsum("bqc,bcdhw->bqdhw", mask_embed, common) / math.sqrt(64.0)
        if disable_queries:
            final_prob = torch.sigmoid(dense_logit)
        else:
            obj_logit = class_logits[..., 1] - class_logits[..., 0]
            obj_prob = torch.sigmoid(obj_logit).view(tokens.shape[0], self.query_count, 1, 1, 1)
            query_prob = torch.sigmoid(mask_logits) * obj_prob
            none_query = torch.prod(1.0 - query_prob.clamp(0, 1), dim=1, keepdim=True)
            final_prob = 1.0 - (1.0 - torch.sigmoid(dense_logit)) * none_query
        final_logit = torch.logit(final_prob.clamp(1.0e-5, 1.0 - 1.0e-5))
        return {
            "dense_logit": dense_logit,
            "final_logit": final_logit,
            "final_prob": final_prob,
            "class_logits": class_logits,
            "query_centers": centers,
            "query_mask_logits": mask_logits,
            "mask_feature": common,
        }


def build_model(arm: str, f0_channels: int, f1_channels: int) -> nn.Module:
    if arm.upper() == "DENSE":
        return DenseParameterMatchedControl(f0_channels, f1_channels)
    if arm.upper() == "QUERY":
        return ScarComponentQueryHead(f0_channels, f1_channels, query_count=32, d_model=128)
    raise ValueError(f"unknown arm {arm}")


def parameter_count(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters()))
