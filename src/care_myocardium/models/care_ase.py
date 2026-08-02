"""CARE-ASE final model architecture.

The model keeps the Dataset501 stock nnU-Net encoder, bottleneck, and low/mid
decoder path, then splits only the highest two decoder resolutions for scar and
pure-edema branches. At initialization, pathology branch logits are bitwise
stock clones apart from normal floating point execution order; all evidence
injections enter through zero-initialized projections.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_source_nnunet


MODALITY_ORDER = ("LGE", "T2", "C0")
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
DEFAULT_STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checkpoint_state_dict(payload: Any) -> dict[str, torch.Tensor]:
    if isinstance(payload, dict):
        for key in ("network_weights", "state_dict", "model_state_dict", "model_state"):
            value = payload.get(key)
            if isinstance(value, dict):
                return {str(k).removeprefix("module."): v for k, v in value.items() if torch.is_tensor(v)}
        return {str(k).removeprefix("module."): v for k, v in payload.items() if torch.is_tensor(v)}
    raise TypeError("checkpoint payload does not contain a tensor state dict")


def _byte_coverage(source: dict[str, torch.Tensor], target: dict[str, torch.Tensor]) -> float:
    matched = 0
    total = 0
    for key, value in target.items():
        total += int(value.numel() * value.element_size())
        src = source.get(key)
        if torch.is_tensor(src) and tuple(src.shape) == tuple(value.shape):
            matched += int(value.numel() * value.element_size())
    return float(matched / max(total, 1))


@dataclass(frozen=True)
class CAREASEConfig:
    fold: int
    plans_path: str
    checkpoint_path: str
    configuration: str = "3d_fullres"
    split_before_highest_decoder_resolutions: int = 2
    gradient_accumulation: int = 4
    gradient_clip_global_norm: float = 12.0
    stage_a_steps: int = 2000
    stage_b_steps: int = 8000
    stage_c_steps: int = 4000
    max_optimizer_steps: int = 14000
    scar_area_reference: float | None = None
    edema_area_reference: float | None = None
    area_reference_source: str = "unset"

    @property
    def nnunet_config(self) -> CAREPRISMConfig:
        return CAREPRISMConfig.from_nnunet_plans(Path(self.plans_path), configuration=self.configuration)

    @classmethod
    def for_fold(
        cls,
        fold: int,
        *,
        plans_path: Path | str = DEFAULT_PLANS,
        checkpoint_path: Path | str | None = None,
        configuration: str = "3d_fullres",
    ) -> "CAREASEConfig":
        ckpt = Path(checkpoint_path) if checkpoint_path is not None else DEFAULT_STOCK_ROOT / f"fold_{int(fold)}" / "checkpoint_final.pth"
        return cls(fold=int(fold), plans_path=str(Path(plans_path)), checkpoint_path=str(ckpt), configuration=configuration)


class ZeroInitEvidenceProjection(nn.Module):
    """Projects declared evidence tensors into a cloned decoder stage."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.proj = nn.Conv3d(in_channels, out_channels, 1)
        nn.init.zeros_(self.proj.weight)
        nn.init.zeros_(self.proj.bias)

    def forward(self, tensor: torch.Tensor, spatial_shape: tuple[int, int, int]) -> torch.Tensor:
        resized = F.interpolate(tensor, size=spatial_shape, mode="trilinear", align_corners=False)
        return self.proj(resized)


class ModalityAdapter(nn.Module):
    """Small declared modality adapter with hard-zero missing input behavior."""

    def __init__(self, out_channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(1, 16, 3, padding=1),
            nn.InstanceNorm3d(16, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(16, out_channels, 1),
        )

    def forward(self, image_channel: torch.Tensor, present: torch.Tensor, spatial_shape: tuple[int, int, int]) -> torch.Tensor:
        present5 = present.view(-1, 1, 1, 1, 1).to(image_channel)
        adapted = self.net(image_channel * present5)
        adapted = F.interpolate(adapted, size=spatial_shape, mode="trilinear", align_corners=False)
        return adapted * present5


class ComponentHeads(nn.Module):
    """Declared heads whose tensors are wired into final pathology logits."""

    def __init__(self, quarter_channels: int, half_channels: int) -> None:
        super().__init__()
        self.scar_quarter_occupancy = nn.Conv3d(quarter_channels, 1, 1)
        self.scar_half_occupancy = nn.Conv3d(half_channels, 1, 1)
        self.scar_quarter_center = nn.Conv3d(quarter_channels, 1, 1)
        self.scar_half_center = nn.Conv3d(half_channels, 1, 1)
        self.scar_context = nn.Conv3d(half_channels, 4, 1)
        self.edema_injury = nn.Conv3d(half_channels, 1, 1)
        self.edema_boundary = nn.Conv3d(half_channels, 1, 1)
        self.edema_context = nn.Conv3d(half_channels, 4, 1)
        self.scar_extent_presence = nn.Conv3d(quarter_channels, 1, 1)
        self.scar_extent_area = nn.Conv3d(quarter_channels, 1, 1)
        self.edema_extent_presence = nn.Conv3d(quarter_channels, 1, 1)
        self.edema_extent_area = nn.Conv3d(quarter_channels, 1, 1)

    def forward(self, quarter: torch.Tensor, half_seed: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "scar_quarter_occupancy": self.scar_quarter_occupancy(quarter),
            "scar_half_occupancy": self.scar_half_occupancy(half_seed),
            "scar_quarter_center": self.scar_quarter_center(quarter),
            "scar_half_center": self.scar_half_center(half_seed),
            "scar_context": self.scar_context(half_seed),
            "edema_injury": self.edema_injury(half_seed),
            "edema_boundary": self.edema_boundary(half_seed),
            "edema_context": self.edema_context(half_seed),
            "scar_extent_presence": self.scar_extent_presence(quarter),
            "scar_extent_area": self.scar_extent_area(quarter),
            "edema_extent_presence": self.edema_extent_presence(quarter),
            "edema_extent_area": self.edema_extent_area(quarter),
        }


class CAREASEPathologyBranch(nn.Module):
    """Half/full-resolution cloned stock decoder branch for one pathology."""

    def __init__(self, stock_decoder: nn.Module, *, class_index: int, half_in_channels: int = 128, full_in_channels: int = 64) -> None:
        super().__init__()
        self.class_index = int(class_index)
        self.transpconvs = nn.ModuleList([deepcopy(stock_decoder.transpconvs[4]), deepcopy(stock_decoder.transpconvs[5])])
        self.stages = nn.ModuleList([deepcopy(stock_decoder.stages[4]), deepcopy(stock_decoder.stages[5])])
        self.seg_layers = nn.ModuleList([deepcopy(stock_decoder.seg_layers[4]), deepcopy(stock_decoder.seg_layers[5])])
        self.half_projection = ZeroInitEvidenceProjection(8, half_in_channels)
        self.full_projection = ZeroInitEvidenceProjection(8, full_in_channels)

    def forward(
        self,
        quarter_feature: torch.Tensor,
        skips: list[torch.Tensor],
        half_evidence: torch.Tensor,
        full_evidence: torch.Tensor,
        *,
        disable_evidence: bool = False,
    ) -> dict[str, torch.Tensor]:
        x = self.transpconvs[0](quarter_feature)
        x = torch.cat((x, skips[1]), 1)
        if not disable_evidence:
            x = x + self.half_projection(half_evidence, x.shape[-3:])
        half_feature = self.stages[0](x)
        half_logits6 = self.seg_layers[0](half_feature)

        x = self.transpconvs[1](half_feature)
        x = torch.cat((x, skips[0]), 1)
        if not disable_evidence:
            x = x + self.full_projection(full_evidence, x.shape[-3:])
        full_feature = self.stages[1](x)
        full_logits6 = self.seg_layers[1](full_feature)
        return {
            "half_feature": half_feature,
            "full_feature": full_feature,
            "half_logits6": half_logits6,
            "full_logits6": full_logits6,
            "final_logit": full_logits6[:, self.class_index : self.class_index + 1],
        }


class CAREASE(nn.Module):
    """Final CARE-ASE architecture bound to a same-fold stock nnU-Net."""

    input_channel_order = MODALITY_ORDER
    pathology_logits_used_from_stock_normal_forward = False

    def __init__(self, config: CAREASEConfig, *, map_location: str | torch.device = "cpu") -> None:
        super().__init__()
        self.config = config
        stock = build_source_nnunet(config.nnunet_config)
        payload = torch.load(config.checkpoint_path, map_location=map_location, weights_only=False)
        state = checkpoint_state_dict(payload)
        load = stock.load_state_dict(state, strict=False)
        self.stock_load_missing_keys = list(load.missing_keys)
        self.stock_load_unexpected_keys = list(load.unexpected_keys)
        self.stock_parameter_byte_coverage = _byte_coverage(state, stock.state_dict())

        self.encoder = stock.encoder
        self.anatomy_decoder = stock.decoder
        self.low_mid_transpconvs = nn.ModuleList([stock.decoder.transpconvs[i] for i in range(4)])
        self.low_mid_stages = nn.ModuleList([stock.decoder.stages[i] for i in range(4)])
        self.scar_branch = CAREASEPathologyBranch(stock.decoder, class_index=5)
        self.edema_branch = CAREASEPathologyBranch(stock.decoder, class_index=4)
        self.component_heads = ComponentHeads(quarter_channels=128, half_channels=64)
        self.scar_lge_adapter = ModalityAdapter(out_channels=8)
        self.scar_c0_adapter = ModalityAdapter(out_channels=8)
        self.edema_t2_adapter = ModalityAdapter(out_channels=8)
        self.edema_c0_adapter = ModalityAdapter(out_channels=8)
        scar_ref = 0.0 if config.scar_area_reference is None else float(config.scar_area_reference)
        edema_ref = 0.0 if config.edema_area_reference is None else float(config.edema_area_reference)
        self.register_buffer("scar_area_reference", torch.tensor(scar_ref, dtype=torch.float32))
        self.register_buffer("edema_area_reference", torch.tensor(edema_ref, dtype=torch.float32))
        self.area_reference_source = str(config.area_reference_source)

    @property
    def final_output_classes(self) -> tuple[int, ...]:
        return (0, 1, 2, 3, 4, 5)

    def _validate_inputs(self, images: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError("CARE-ASE images must be [B,3,D,H,W] ordered as [LGE,T2,C0]")
        availability = availability.to(device=images.device, dtype=images.dtype)
        if availability.ndim != 2 or availability.shape[1] != 3:
            raise ValueError("availability must be [B,3] ordered as [LGE,T2,C0]")
        return availability

    def _encode(self, images: torch.Tensor, availability: torch.Tensor) -> list[torch.Tensor]:
        masked = images * availability.view(-1, 3, 1, 1, 1)
        return list(self.encoder(masked))

    def _decode_low_mid(self, skips: list[torch.Tensor]) -> tuple[torch.Tensor, list[torch.Tensor]]:
        x = skips[-1]
        low_mid = []
        for stage_index in range(4):
            x = self.low_mid_transpconvs[stage_index](x)
            x = torch.cat((x, skips[-(stage_index + 2)]), 1)
            x = self.low_mid_stages[stage_index](x)
            low_mid.append(x)
        return x, low_mid

    @staticmethod
    def _sigmoid_logit_center(probability: torch.Tensor, reference: torch.Tensor | float) -> torch.Tensor:
        prob = probability.clamp(0.01, 0.99)
        ref = torch.as_tensor(reference, dtype=prob.dtype, device=prob.device).clamp(0.01, 0.99)
        return torch.logit(prob) - torch.logit(ref)

    def set_area_references(self, *, scar: float, edema: float, source: str) -> None:
        if source != "actual_train_only":
            raise ValueError("CARE-ASE R2 area references must be computed from actual-train cases only")
        self.scar_area_reference.fill_(float(scar))
        self.edema_area_reference.fill_(float(edema))
        self.area_reference_source = source

    @staticmethod
    def extent_wall_ramp(global_step: int) -> float:
        step = int(global_step)
        if step <= 500:
            return 0.0
        if step >= 2000:
            return 1.0
        return float((step - 500) / 1500.0)

    def _extent_bias(
        self,
        components: dict[str, torch.Tensor],
        p_wall: torch.Tensor,
        *,
        pathology: str,
        global_step: int,
        disable_extent_wall: bool = False,
    ) -> torch.Tensor:
        ramp = 0.0 if disable_extent_wall else self.extent_wall_ramp(global_step)
        if ramp == 0.0:
            return torch.zeros_like(p_wall)
        if pathology == "scar":
            presence = torch.sigmoid(components["scar_extent_presence"]).mean(dim=(-2, -1), keepdim=True)
            area = torch.sigmoid(components["scar_extent_area"]).mean(dim=(-2, -1), keepdim=True)
            presence_bias = 0.30 * self._sigmoid_logit_center(presence, 0.50)
            area_bias = 0.20 * self._sigmoid_logit_center(area, self.scar_area_reference)
            wall_bias = 0.15 * self._sigmoid_logit_center(p_wall, 0.50)
        else:
            presence = torch.sigmoid(components["edema_extent_presence"]).mean(dim=(-2, -1), keepdim=True)
            area = torch.sigmoid(components["edema_extent_area"]).mean(dim=(-2, -1), keepdim=True)
            presence_bias = 0.35 * self._sigmoid_logit_center(presence, 0.50)
            area_bias = 0.30 * self._sigmoid_logit_center(area, self.edema_area_reference)
            wall_bias = 0.10 * self._sigmoid_logit_center(p_wall, 0.50)
        return float(ramp) * F.interpolate(presence_bias + area_bias, size=p_wall.shape[-3:], mode="trilinear", align_corners=False) + float(ramp) * wall_bias

    def forward(
        self,
        images: torch.Tensor,
        availability: torch.Tensor,
        *,
        global_step: int = 0,
        disable_scar_proposal: bool = False,
        disable_scar_center: bool = False,
        disable_scar_context: bool = False,
        disable_edema_injury: bool = False,
        disable_edema_boundary: bool = False,
        disable_edema_context: bool = False,
        disable_extent_wall: bool = False,
        disable_all_evidence: bool = False,
    ) -> dict[str, Any]:
        availability = self._validate_inputs(images, availability)
        skips = self._encode(images, availability)
        stock_anatomy_logits6 = self.anatomy_decoder(skips)
        anatomy_logits = stock_anatomy_logits6[:, :4]
        anatomy_prob = torch.softmax(stock_anatomy_logits6[:, :4], dim=1)
        p_wall = anatomy_prob[:, 1:2]
        p_lv = anatomy_prob[:, 2:3]
        p_rv = anatomy_prob[:, 3:4]
        signed_endo_distance = torch.tanh(p_lv - p_wall)
        signed_epi_distance = torch.tanh(anatomy_prob[:, 0:1] - p_wall)
        wall_depth_rho = p_lv / (p_lv + p_rv + 1.0e-6)
        quarter, low_mid = self._decode_low_mid(skips)
        half_seed = F.interpolate(quarter[:, :64], size=skips[1].shape[-3:], mode="trilinear", align_corners=False)
        components = self.component_heads(quarter, half_seed)

        scar_half_items: list[torch.Tensor] = [
            torch.zeros_like(components["scar_half_occupancy"]) if disable_scar_proposal else components["scar_half_occupancy"],
            torch.zeros_like(components["scar_half_center"]) if disable_scar_center else components["scar_half_center"],
            torch.zeros_like(components["scar_context"]) if disable_scar_context else components["scar_context"],
            self.scar_lge_adapter(images[:, 0:1], availability[:, 0], skips[1].shape[-3:]).mean(dim=1, keepdim=True),
            0.2 * self.scar_c0_adapter(images[:, 2:3], availability[:, 2], skips[1].shape[-3:]).mean(dim=1, keepdim=True),
        ]
        scar_full_items: list[torch.Tensor] = [
            torch.zeros_like(components["scar_quarter_occupancy"]) if disable_scar_proposal else components["scar_quarter_occupancy"],
            torch.zeros_like(components["scar_quarter_center"]) if disable_scar_center else components["scar_quarter_center"],
            torch.zeros_like(components["scar_context"]) if disable_scar_context else components["scar_context"],
            self.scar_lge_adapter(images[:, 0:1], availability[:, 0], skips[0].shape[-3:]).mean(dim=1, keepdim=True),
            0.2 * self.scar_c0_adapter(images[:, 2:3], availability[:, 2], skips[0].shape[-3:]).mean(dim=1, keepdim=True),
        ]
        edema_half_items: list[torch.Tensor] = [
            torch.zeros_like(components["edema_injury"]) if disable_edema_injury else components["edema_injury"],
            torch.zeros_like(components["edema_boundary"]) if disable_edema_boundary else components["edema_boundary"],
            torch.zeros_like(components["edema_context"]) if disable_edema_context else components["edema_context"],
            self.edema_t2_adapter(images[:, 1:2], availability[:, 1], skips[1].shape[-3:]).mean(dim=1, keepdim=True),
            0.2 * self.edema_c0_adapter(images[:, 2:3], availability[:, 2], skips[1].shape[-3:]).mean(dim=1, keepdim=True),
        ]
        edema_full_items: list[torch.Tensor] = [
            torch.zeros_like(components["edema_injury"]) if disable_edema_injury else components["edema_injury"],
            torch.zeros_like(components["edema_boundary"]) if disable_edema_boundary else components["edema_boundary"],
            torch.zeros_like(components["edema_context"]) if disable_edema_context else components["edema_context"],
            self.edema_t2_adapter(images[:, 1:2], availability[:, 1], skips[0].shape[-3:]).mean(dim=1, keepdim=True),
            0.2 * self.edema_c0_adapter(images[:, 2:3], availability[:, 2], skips[0].shape[-3:]).mean(dim=1, keepdim=True),
        ]

        scar_half_evidence = _concat_to_eight(scar_half_items, skips[1].shape[-3:])
        scar_full_evidence = _concat_to_eight(scar_full_items, skips[0].shape[-3:])
        edema_half_evidence = _concat_to_eight(edema_half_items, skips[1].shape[-3:])
        edema_full_evidence = _concat_to_eight(edema_full_items, skips[0].shape[-3:])

        scar = self.scar_branch(quarter, skips, scar_half_evidence, scar_full_evidence, disable_evidence=disable_all_evidence)
        edema = self.edema_branch(quarter, skips, edema_half_evidence, edema_full_evidence, disable_evidence=disable_all_evidence)
        z_scar = scar["final_logit"] + self._extent_bias(components, p_wall, pathology="scar", global_step=global_step, disable_extent_wall=disable_extent_wall)
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1)
        z_edema = (edema["final_logit"] + self._extent_bias(components, p_wall, pathology="edema", global_step=global_step, disable_extent_wall=disable_extent_wall)) * t2
        final_logits = torch.cat([anatomy_logits, z_edema, z_scar], dim=1)
        return {
            "final_logits": final_logits,
            "anatomy_logits_0_3": anatomy_logits,
            "p_wall_union": p_wall,
            "p_lv": p_lv,
            "p_rv": p_rv,
            "signed_endo_distance": signed_endo_distance,
            "signed_epi_distance": signed_epi_distance,
            "wall_depth_rho": wall_depth_rho,
            "skips": skips,
            "low_mid_decoder_features": low_mid,
            "shared_quarter_feature": quarter,
            "components": components,
            "scar": scar,
            "edema": edema,
            "z_scar": z_scar,
            "z_pure_edema": z_edema,
            "availability": availability,
            "extent_wall_ramp_value": torch.tensor(self.extent_wall_ramp(global_step), device=images.device),
            "normal_forward_reads_stock_pathology_logits": False,
        }

    @torch.no_grad()
    def step0_parity_report(self, sample: torch.Tensor, availability: torch.Tensor) -> dict[str, Any]:
        self.eval()
        availability = availability.to(sample)
        stock = build_source_nnunet(self.config.nnunet_config).to(sample.device)
        payload = torch.load(self.config.checkpoint_path, map_location=sample.device, weights_only=False)
        load = stock.load_state_dict(checkpoint_state_dict(payload), strict=False)
        stock.eval()
        stock_logits = stock(sample.float() * availability.view(-1, 3, 1, 1, 1))
        out = self(sample.float(), availability, global_step=0, disable_extent_wall=True, disable_all_evidence=False)
        final = out["final_logits"]
        scar_diff = (final[:, 5:6] - stock_logits[:, 5:6]).abs()
        edema_diff = (final[:, 4:5] - stock_logits[:, 4:5] * availability[:, 1:2].view(-1, 1, 1, 1, 1)).abs()
        anatomy_diff = (final[:, :4] - stock_logits[:, :4]).abs()
        changed = int((final.argmax(1) != stock_logits.argmax(1)).sum().item())
        return {
            "status": "PASS" if float(max(scar_diff.max(), edema_diff.max(), anatomy_diff.max()).item()) <= 1.0e-6 else "FAIL",
            "fold": int(self.config.fold),
            "checkpoint_path": str(self.config.checkpoint_path),
            "checkpoint_sha256": sha256_file(Path(self.config.checkpoint_path)),
            "stock_parameter_byte_coverage": float(self.stock_parameter_byte_coverage),
            "stock_load_missing_keys": self.stock_load_missing_keys,
            "stock_load_unexpected_keys": self.stock_load_unexpected_keys,
            "reference_load_missing_keys": list(load.missing_keys),
            "reference_load_unexpected_keys": list(load.unexpected_keys),
            "anatomy_step0_parity_max_abs_error": float(anatomy_diff.max().item()),
            "step0_scar_logit_parity_vs_stock_class5_max_abs_error": float(scar_diff.max().item()),
            "step0_edema_logit_parity_vs_stock_class4_max_abs_error": float(edema_diff.max().item()),
            "compatibility_argmax_changed_voxels": changed,
            "normal_forward_reads_stock_pathology_logits": False,
            "clone_decoder_stage_indices": [4, 5],
            "split_before_highest_decoder_resolutions": 2,
        }


def _concat_to_eight(items: Iterable[torch.Tensor], spatial_shape: tuple[int, int, int]) -> torch.Tensor:
    resized = [F.interpolate(item, size=spatial_shape, mode="trilinear", align_corners=False) for item in items]
    merged = torch.cat(resized, dim=1)
    if merged.shape[1] == 8:
        return merged
    if merged.shape[1] > 8:
        return merged[:, :8]
    pad = merged.new_zeros((merged.shape[0], 8 - merged.shape[1], *merged.shape[-3:]))
    return torch.cat([merged, pad], dim=1)


def build_care_ase_for_fold(fold: int, *, map_location: str | torch.device = "cpu") -> CAREASE:
    return CAREASE(CAREASEConfig.for_fold(fold), map_location=map_location)


def build_care_ase_for_fold_with_area_references(
    fold: int,
    *,
    scar_area_reference: float,
    edema_area_reference: float,
    map_location: str | torch.device = "cpu",
) -> CAREASE:
    base = CAREASEConfig.for_fold(fold)
    config = CAREASEConfig(
        fold=base.fold,
        plans_path=base.plans_path,
        checkpoint_path=base.checkpoint_path,
        configuration=base.configuration,
        split_before_highest_decoder_resolutions=base.split_before_highest_decoder_resolutions,
        gradient_accumulation=base.gradient_accumulation,
        gradient_clip_global_norm=base.gradient_clip_global_norm,
        stage_a_steps=base.stage_a_steps,
        stage_b_steps=base.stage_b_steps,
        stage_c_steps=base.stage_c_steps,
        max_optimizer_steps=base.max_optimizer_steps,
        scar_area_reference=float(scar_area_reference),
        edema_area_reference=float(edema_area_reference),
        area_reference_source="actual_train_only",
    )
    return CAREASE(config, map_location=map_location)


def care_ase_contract_summary(model: CAREASE) -> dict[str, Any]:
    named_params = dict(model.named_parameters())
    zero_projection_max_abs = {
        name: float(param.detach().abs().max().cpu())
        for name, param in named_params.items()
        if ("half_projection.proj" in name or "full_projection.proj" in name)
    }
    return {
        "model_class": type(model).__name__,
        "input_channel_order": list(model.input_channel_order),
        "stock_parameter_byte_coverage": model.stock_parameter_byte_coverage,
        "stock_load_missing_keys": model.stock_load_missing_keys,
        "stock_load_unexpected_keys": model.stock_load_unexpected_keys,
        "shared_encoder": "all_stages",
        "shared_decoder_below_split_stage_indices": [0, 1, 2, 3],
        "scar_cloned_decoder_stage_indices": [4, 5],
        "edema_cloned_decoder_stage_indices": [4, 5],
        "normal_forward_must_not_read_stock_pathology_logits": True,
        "normal_forward_reads_stock_pathology_logits": False,
        "zero_init_projection_parameter_max_abs": zero_projection_max_abs,
        "stage_steps": {
            "A": model.config.stage_a_steps,
            "B": model.config.stage_b_steps,
            "C": model.config.stage_c_steps,
            "total": model.config.max_optimizer_steps,
        },
        "area_reference_source": model.area_reference_source,
        "scar_area_reference": float(model.scar_area_reference.detach().cpu()),
        "edema_area_reference": float(model.edema_area_reference.detach().cpu()),
        "declared_component_entries": [
            "scar_coarse_proposal",
            "scar_component_center",
            "scar_context_negative_space",
            "edema_injury_support",
            "edema_boundary",
            "edema_context_negative_space",
            "slice_extent_and_soft_wall",
        ],
        "anatomy_outputs": [
            "anatomy_logits_0_3",
            "p_wall_union",
            "p_lv",
            "p_rv",
            "signed_endo_distance",
            "signed_epi_distance",
            "wall_depth_rho",
        ],
        "pathology_outputs": [
            "full_resolution_z_scar",
            "half_and_quarter_occupancy_logits",
            "half_and_quarter_component_center_heatmaps",
            "slice_presence_logits",
            "slice_area_fraction",
            "four_class_context_logits",
            "full_resolution_z_pure_edema",
            "injury_support_logit_labels_4_or_5",
            "signed_pure_edema_boundary",
        ],
    }
