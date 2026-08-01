"""Model components for the 20260801 target-domain gap closure lanes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.myowall_if.stock_adapter import StockNNUNetFeatureAdapter


@dataclass(frozen=True)
class CARETDSContract:
    input_channel_order: tuple[str, str, str] = ("LGE", "T2", "C0")
    scar_label: int = 5
    pure_edema_label: int = 4
    injury_labels: tuple[int, int] = (4, 5)
    uses_stock_pathology_logits_for_final: bool = False
    stock_context_detached: bool = True


def make_pathology_targets(labels: torch.Tensor, *, scar_label: int = 5, pure_edema_label: int = 4) -> dict[str, torch.Tensor]:
    if labels.ndim == 5 and labels.shape[1] == 1:
        labels = labels[:, 0]
    if labels.ndim != 4:
        raise ValueError("labels must be [B,Z,Y,X] or [B,1,Z,Y,X]")
    scar = (labels == scar_label).float().unsqueeze(1)
    pure_edema = ((labels == pure_edema_label) & (labels != scar_label)).float().unsqueeze(1)
    injury = ((labels == pure_edema_label) | (labels == scar_label)).float().unsqueeze(1)
    pooled = F.max_pool3d(injury, kernel_size=3, stride=1, padding=1)
    eroded = -F.max_pool3d(-injury, kernel_size=3, stride=1, padding=1)
    boundary = (pooled - eroded).clamp_(0, 1)
    return {
        "scar": scar,
        "pure_edema": pure_edema,
        "injury": injury,
        "boundary": boundary,
    }


class _LazyHead(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.LazyConv3d(32, kernel_size=3, padding=1),
            nn.InstanceNorm3d(32, affine=True),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(32, 1, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CARETargetDomainSpecialist(nn.Module):
    """CARE-TDS M3 head stack on frozen stock F0 plus detached anatomy context."""

    contract = CARETDSContract()

    def __init__(
        self,
        *,
        fold: int,
        checkpoint_path: str | Path | None = None,
        map_location: str | torch.device = "cpu",
    ) -> None:
        super().__init__()
        self.stock = StockNNUNetFeatureAdapter(fold=fold, checkpoint_path=checkpoint_path, map_location=map_location)
        for param in self.stock.parameters():
            param.requires_grad_(False)
        self.scar_head = _LazyHead()
        self.pure_edema_head = _LazyHead()
        self.injury_head = _LazyHead()
        self.boundary_head = _LazyHead()

    @property
    def uses_stock_pathology_logits_for_final(self) -> bool:
        return False

    def forward(self, images: torch.Tensor) -> dict[str, torch.Tensor]:
        stock = self.stock(images)
        f0 = stock["f0"].detach()
        context = torch.cat([stock["p_wall"].detach(), stock["p_lv"].detach()], dim=1)
        if context.shape[2:] != f0.shape[2:]:
            context = F.interpolate(context, size=f0.shape[2:], mode="trilinear", align_corners=False)
        features = torch.cat([f0, context], dim=1)
        scar = self.scar_head(features)
        pure_edema = self.pure_edema_head(features)
        injury = self.injury_head(features)
        boundary = self.boundary_head(features)
        background = -(torch.maximum(scar, pure_edema) + 0.5 * torch.sigmoid(injury))
        final_logits = torch.cat([background, scar, pure_edema, injury, boundary], dim=1)
        return {
            "scar_logit": scar,
            "pure_edema_logit": pure_edema,
            "injury_logit": injury,
            "boundary_logit": boundary,
            "final_logits": final_logits,
            "stock_logits_reference_only": stock["logits"].detach(),
            "f0": f0,
        }


def care_tds_loss(outputs: dict[str, torch.Tensor], labels: torch.Tensor) -> dict[str, torch.Tensor]:
    targets = make_pathology_targets(labels)
    resized = {}
    for key in ("scar_logit", "pure_edema_logit", "injury_logit", "boundary_logit"):
        value = outputs[key]
        if value.shape[2:] != targets["scar"].shape[2:]:
            value = F.interpolate(value, size=targets["scar"].shape[2:], mode="trilinear", align_corners=False)
        resized[key] = value
    losses = {
        "scar_bce": F.binary_cross_entropy_with_logits(resized["scar_logit"], targets["scar"]),
        "pure_edema_bce": F.binary_cross_entropy_with_logits(resized["pure_edema_logit"], targets["pure_edema"]),
        "injury_bce": F.binary_cross_entropy_with_logits(resized["injury_logit"], targets["injury"]),
        "boundary_bce": F.binary_cross_entropy_with_logits(resized["boundary_logit"], targets["boundary"]),
    }
    containment = F.relu(torch.sigmoid(resized["scar_logit"]) - torch.sigmoid(resized["injury_logit"])).mean()
    edema_containment = F.relu(torch.sigmoid(resized["pure_edema_logit"]) - torch.sigmoid(resized["injury_logit"])).mean()
    losses["scar_injury_containment"] = containment
    losses["pure_edema_injury_containment"] = edema_containment
    losses["total"] = sum(losses.values())
    return losses


def smoke_care_tds(fold: int, *, device: str | torch.device = "cpu") -> dict[str, Any]:
    dev = torch.device(device)
    model = CARETargetDomainSpecialist(fold=fold, map_location=dev).to(dev)
    patch = model.stock.patch_size
    shape = (1, 3, min(16, patch[0]), min(64, patch[1]), min(64, patch[2]))
    torch.manual_seed(20260801 + fold)
    images = torch.randn(*shape, device=dev)
    labels = torch.zeros((1, shape[2], shape[3], shape[4]), dtype=torch.long, device=dev)
    labels[:, :, 8:24, 8:24] = 4
    labels[:, :, 16:32, 16:32] = 5
    outputs = model(images)
    losses = care_tds_loss(outputs, labels)
    losses["total"].backward()
    grad_checks = {
        name: param.grad is not None and torch.isfinite(param.grad).all().item()
        for name, param in model.named_parameters()
        if name.endswith("net.3.weight")
    }
    return {
        "status": "PASS" if all(grad_checks.values()) and not model.uses_stock_pathology_logits_for_final else "FAIL",
        "fold": fold,
        "input_shape": list(images.shape),
        "f0_shape": list(outputs["f0"].shape),
        "final_logits_shape": list(outputs["final_logits"].shape),
        "loss_terms": sorted(losses.keys()),
        "total_loss": float(losses["total"].detach().cpu()),
        "head_grad_checks": grad_checks,
        "uses_stock_pathology_logits_for_final": model.uses_stock_pathology_logits_for_final,
    }
