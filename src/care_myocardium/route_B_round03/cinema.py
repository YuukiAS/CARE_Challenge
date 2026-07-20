"""Pinned-CineMA adapter interface and matched-random source wrappers."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
import torch.nn.functional as F

from .contract import CINEMA_CODE_COMMIT, CINEMA_HF_REVISION, CINEMA_WEIGHT_SHA256


@dataclass(frozen=True)
class CineMAProvenance:
    repository: str = "mathpluscode/CineMA"
    code_commit: str = CINEMA_CODE_COMMIT
    hf_revision: str = CINEMA_HF_REVISION
    weight_sha256: str = CINEMA_WEIGHT_SHA256
    license: str = "MIT"
    model_symbol: str = "cinema.segmentation.convunetr.ConvUNetR"
    decoder_hook: str = 'decoder_dict["sax"] before pred_head_dict["sax"]'


class RouteBRound03CineMAAdapter(nn.Module):
    """Route-local adapter shape contract for official ConvUNetR outputs."""

    def __init__(self, decoder_channels: int = 32, projected_channels: int = 16) -> None:
        super().__init__()
        self.provenance = CineMAProvenance()
        self.decoder = nn.Sequential(nn.Conv3d(1, decoder_channels, 3, padding=1), nn.GroupNorm(8, decoder_channels), nn.SiLU())
        self.pred_head = nn.Conv3d(decoder_channels, 4, 1)
        self.projection = nn.Conv3d(decoder_channels, projected_channels, 1)

    def forward(self, frame: torch.Tensor) -> dict[str, torch.Tensor]:
        decoder_feature_32 = self.decoder(frame)
        logits = self.pred_head(decoder_feature_32)
        prob = torch.softmax(logits, dim=1).clamp_min(1e-6)
        entropy = -(prob * prob.log()).sum(dim=1, keepdim=True) / torch.log(torch.tensor(float(logits.shape[1]), device=logits.device))
        return {
            "logits": logits,
            "probabilities": prob,
            "decoder_feature_32": decoder_feature_32,
            "features": self.projection(decoder_feature_32),
            "entropy": entropy,
        }


class MatchedRandomCineMASource(RouteBRound03CineMAAdapter):
    """Same architecture as the pretrained source, distinct source init hash."""

    source_kind = "matched_random"
