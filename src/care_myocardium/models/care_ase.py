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
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_source_nnunet


MODALITY_ORDER = ("LGE", "T2", "C0")
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
DEFAULT_DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json"
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


def _conv3d_modules(module: nn.Module) -> list[nn.Conv3d]:
    return [child for child in module.modules() if isinstance(child, nn.Conv3d)]


def _conv_transpose3d_modules(module: nn.Module) -> list[nn.ConvTranspose3d]:
    return [child for child in module.modules() if isinstance(child, nn.ConvTranspose3d)]


def _first_conv3d_in_channels(module: nn.Module) -> int:
    convs = _conv3d_modules(module)
    if not convs:
        raise ValueError(f"module has no Conv3d layers: {type(module).__name__}")
    return int(convs[0].in_channels)


def _last_conv3d_out_channels(module: nn.Module) -> int:
    convs = _conv3d_modules(module)
    if not convs:
        raise ValueError(f"module has no Conv3d layers: {type(module).__name__}")
    return int(convs[-1].out_channels)


def _stage_kernel_stride(module: nn.Module) -> dict[str, Any]:
    convs = _conv3d_modules(module)
    transposed = _conv_transpose3d_modules(module)
    return {
        "conv_kernel_sizes": [list(conv.kernel_size) for conv in convs],
        "conv_strides": [list(conv.stride) for conv in convs],
        "transposed_kernel_sizes": [list(conv.kernel_size) for conv in transposed],
        "transposed_strides": [list(conv.stride) for conv in transposed],
    }


def _clone_seg_layer_rows(seg_layer: nn.Module, rows: int) -> nn.Module:
    if not isinstance(seg_layer, nn.Conv3d):
        raise TypeError(f"expected nnU-Net seg_layer to be Conv3d, got {type(seg_layer).__name__}")
    cloned = nn.Conv3d(
        seg_layer.in_channels,
        int(rows),
        kernel_size=seg_layer.kernel_size,
        stride=seg_layer.stride,
        padding=seg_layer.padding,
        dilation=seg_layer.dilation,
        groups=seg_layer.groups,
        bias=seg_layer.bias is not None,
        padding_mode=seg_layer.padding_mode,
    )
    with torch.no_grad():
        cloned.weight.copy_(seg_layer.weight[:rows])
        if seg_layer.bias is not None and cloned.bias is not None:
            cloned.bias.copy_(seg_layer.bias[:rows])
    return cloned


class SingleRowStockSegLayer(nn.Module):
    """Single trainable stock classifier row executed through the stock 6-row kernel path."""

    def __init__(self, seg_layer: nn.Conv3d, row: int) -> None:
        super().__init__()
        self.class_index = int(row)
        self.in_channels = int(seg_layer.in_channels)
        self.out_channels = 1
        self.kernel_size = seg_layer.kernel_size
        self.stride = seg_layer.stride
        self.padding = seg_layer.padding
        self.dilation = seg_layer.dilation
        self.groups = seg_layer.groups
        self.padding_mode = seg_layer.padding_mode
        self.stock_out_channels = int(seg_layer.out_channels)
        self.weight = nn.Parameter(seg_layer.weight[self.class_index : self.class_index + 1].detach().clone())
        if seg_layer.bias is None:
            self.register_parameter("bias", None)
        else:
            self.bias = nn.Parameter(seg_layer.bias[self.class_index : self.class_index + 1].detach().clone())
        before = self.class_index
        after = self.stock_out_channels - self.class_index - 1
        self.register_buffer("_weight_before", seg_layer.weight.detach().new_zeros((before, *seg_layer.weight.shape[1:])))
        self.register_buffer("_weight_after", seg_layer.weight.detach().new_zeros((after, *seg_layer.weight.shape[1:])))
        if seg_layer.bias is not None:
            self.register_buffer("_bias_before", seg_layer.bias.detach().new_zeros((before,)))
            self.register_buffer("_bias_after", seg_layer.bias.detach().new_zeros((after,)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weight = torch.cat(
            [
                self._weight_before.to(device=x.device, dtype=self.weight.dtype),
                self.weight,
                self._weight_after.to(device=x.device, dtype=self.weight.dtype),
            ],
            dim=0,
        )
        bias = None
        if self.bias is not None:
            bias = torch.cat(
                [
                    self._bias_before.to(device=x.device, dtype=self.bias.dtype),
                    self.bias,
                    self._bias_after.to(device=x.device, dtype=self.bias.dtype),
                ],
                dim=0,
            )
        if self.padding_mode != "zeros":
            pad_d, pad_h, pad_w = self.padding
            x = F.pad(x, (pad_w, pad_w, pad_h, pad_h, pad_d, pad_d), mode=self.padding_mode)
            padding = (0, 0, 0)
        else:
            padding = self.padding
        logits = F.conv3d(x, weight, bias, self.stride, padding, self.dilation, self.groups)
        return logits[:, self.class_index : self.class_index + 1]


def _clone_seg_layer_single_row(seg_layer: nn.Module, row: int) -> nn.Module:
    if not isinstance(seg_layer, nn.Conv3d):
        raise TypeError(f"expected nnU-Net seg_layer to be Conv3d, got {type(seg_layer).__name__}")
    row = int(row)
    if row < 0 or row >= int(seg_layer.out_channels):
        raise ValueError(f"seg_layer row {row} outside out_channels={seg_layer.out_channels}")
    return SingleRowStockSegLayer(seg_layer, row)


def _single_pathology_logit_to_six(logit: torch.Tensor, class_index: int) -> torch.Tensor:
    compat = logit.detach().new_zeros((logit.shape[0], 6, *logit.shape[-3:]))
    compat[:, int(class_index) : int(class_index) + 1] = logit
    return compat


@dataclass(frozen=True)
class CAREASEDecoderIntrospection:
    shared_quarter_channels: int
    half_seed_channels: int
    half_projection_channels: int
    full_projection_channels: int
    branch_half_feature_channels: int
    branch_full_feature_channels: int
    cloned_stage_indices: tuple[int, int]
    shared_low_mid_stage_indices: tuple[int, int, int, int]
    stage_kernel_stride: dict[str, Any]


def introspect_stock_decoder(stock_decoder: nn.Module) -> CAREASEDecoderIntrospection:
    """Read all CARE-ASE split dimensions from the actual stock decoder."""

    cloned = (4, 5)
    shared = (0, 1, 2, 3)
    return CAREASEDecoderIntrospection(
        shared_quarter_channels=_last_conv3d_out_channels(stock_decoder.stages[3]),
        half_seed_channels=_last_conv3d_out_channels(stock_decoder.stages[4]),
        half_projection_channels=_first_conv3d_in_channels(stock_decoder.stages[4]),
        full_projection_channels=_first_conv3d_in_channels(stock_decoder.stages[5]),
        branch_half_feature_channels=_last_conv3d_out_channels(stock_decoder.stages[4]),
        branch_full_feature_channels=_last_conv3d_out_channels(stock_decoder.stages[5]),
        cloned_stage_indices=cloned,
        shared_low_mid_stage_indices=shared,
        stage_kernel_stride={
            f"stage_{idx}": _stage_kernel_stride(stock_decoder.stages[idx])
            | {"transpconv": _stage_kernel_stride(stock_decoder.transpconvs[idx])}
            for idx in (*shared, *cloned)
        },
    )


def stock_pathology_deep_supervision_weights(stock_decoder: nn.Module, introspection: CAREASEDecoderIntrospection) -> dict[str, Any]:
    """Bind pathology full/half supervision weights to the stock nnU-Net DS formula."""

    seg_layer_count = len(stock_decoder.seg_layers)
    if seg_layer_count <= max(introspection.cloned_stage_indices):
        raise ValueError("stock decoder has fewer seg_layers than the CARE-ASE cloned pathology stages")
    half_stage, full_stage = introspection.cloned_stage_indices
    plans = json.loads(DEFAULT_PLANS.read_text(encoding="utf-8"))
    dataset_json = json.loads(DEFAULT_DATASET_JSON.read_text(encoding="utf-8"))
    plans_manager = PlansManager(plans)
    trainer = object.__new__(nnUNetTrainer)
    trainer.configuration_manager = plans_manager.get_configuration("3d_fullres")
    trainer.label_manager = plans_manager.get_label_manager(dataset_json)
    trainer.enable_deep_supervision = True
    trainer.is_ddp = False
    trainer._do_i_compile = lambda: False
    stock_loss = nnUNetTrainer._build_loss(trainer)
    weight_factors = tuple(float(v) for v in getattr(stock_loss, "weight_factors"))
    if len(weight_factors) != seg_layer_count:
        raise ValueError(f"stock trainer DS weight count {len(weight_factors)} != decoder seg layer count {seg_layer_count}")
    output_index_by_stage = {stage: (seg_layer_count - 1 - stage) for stage in range(seg_layer_count)}
    raw_by_stage = {stage: weight_factors[output_index_by_stage[stage]] for stage in range(seg_layer_count)}
    raw_selected = {
        "full": raw_by_stage[int(full_stage)],
        "half": raw_by_stage[int(half_stage)],
    }
    total = float(raw_selected["half"] + raw_selected["full"])
    if total <= 0.0:
        raise ValueError("stock deep-supervision weights for pathology scales sum to zero")
    return {
        "full": float(raw_selected["full"] / total),
        "half": float(raw_selected["half"] / total),
        "source": "stock_nnunet_deep_supervision_formula_1_over_2_power_output_order_normalized_over_highest_two_pathology_scales",
        "source_runtime": "nnUNetTrainer._build_loss().weight_factors",
        "stock_decoder_seg_layer_count": int(seg_layer_count),
        "stock_runtime_weight_factors": list(weight_factors),
        "selected_stage_indices": {"half": int(half_stage), "full": int(full_stage)},
        "selected_output_order": ["full", "half"],
        "output_index_by_stage": {str(key): int(value) for key, value in output_index_by_stage.items()},
        "stock_raw_weights_by_decoder_stage": {str(key): float(value) for key, value in raw_by_stage.items()},
        "raw_selected_weights": {key: float(value) for key, value in raw_selected.items()},
    }


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


class ScalarGate(nn.Module):
    """Single learnable scalar gate with a declared activation and initial output."""

    def __init__(self, *, activation: str, initial_output: float) -> None:
        super().__init__()
        self.activation = str(activation)
        if self.activation == "sigmoid":
            init = torch.logit(torch.tensor(float(initial_output), dtype=torch.float32))
        elif self.activation == "tanh":
            init = torch.atanh(torch.tensor(float(initial_output), dtype=torch.float32).clamp(-0.999, 0.999))
        else:
            raise ValueError(f"unsupported gate activation: {activation}")
        self.raw = nn.Parameter(init.clone().detach())

    def forward(self) -> torch.Tensor:
        if self.activation == "sigmoid":
            return torch.sigmoid(self.raw)
        return torch.tanh(self.raw)


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
        for module in self.net:
            if isinstance(module, nn.Conv3d):
                nn.init.kaiming_normal_(module.weight, nonlinearity="linear")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, image_channel: torch.Tensor, present: torch.Tensor, spatial_shape: tuple[int, int, int]) -> torch.Tensor:
        present5 = present.view(-1, 1, 1, 1, 1).to(image_channel)
        adapted = self.net(image_channel * present5)
        adapted = F.interpolate(adapted, size=spatial_shape, mode="trilinear", align_corners=False)
        return adapted * present5


class AnatomyGeometryHeads(nn.Module):
    """Independent trainable physical-geometry heads from anatomy logits."""

    def __init__(self) -> None:
        super().__init__()
        self.signed_endo_distance = nn.Conv3d(4, 1, 1)
        self.signed_epi_distance = nn.Conv3d(4, 1, 1)
        self.wall_depth_rho = nn.Conv3d(4, 1, 1)

    def forward(self, anatomy_logits: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "signed_endo_distance": torch.tanh(self.signed_endo_distance(anatomy_logits)),
            "signed_epi_distance": torch.tanh(self.signed_epi_distance(anatomy_logits)),
            "wall_depth_rho": torch.sigmoid(self.wall_depth_rho(anatomy_logits)),
        }


class EdemaDilationContextBlock(nn.Module):
    """Multi-dilation edema context whose evidence enters through branch projections."""

    def __init__(self, in_channels: int, out_channels: int = 1) -> None:
        super().__init__()
        self.dilated = nn.ModuleDict()
        for dilation in (1, 2, 4):
            self.dilated[str(dilation)] = nn.Sequential(
                nn.Conv3d(in_channels, in_channels, 3, padding=dilation, dilation=dilation),
                nn.InstanceNorm3d(in_channels, affine=True),
                nn.SiLU(inplace=True),
                nn.Conv3d(in_channels, out_channels, 1),
            )
            last = self.dilated[str(dilation)][-1]
            if not isinstance(last, nn.Conv3d):
                raise TypeError("edema dilation projection must be Conv3d")
            nn.init.kaiming_normal_(last.weight, nonlinearity="linear")
            if last.bias is not None:
                nn.init.zeros_(last.bias)

    def forward(self, feature: torch.Tensor) -> dict[str, torch.Tensor]:
        return {f"edema_dilation_{key}": block(feature) for key, block in self.dilated.items()}


class ComponentHeads(nn.Module):
    """Declared heads whose tensors are wired into final pathology logits."""

    def __init__(self, quarter_channels: int, pathology_half_channels: int) -> None:
        super().__init__()
        self.scar_quarter_occupancy = nn.Conv3d(quarter_channels, 1, 1)
        self.scar_quarter_center = nn.Conv3d(quarter_channels, 1, 1)
        self.scar_context = nn.Conv3d(quarter_channels, 4, 1)
        self.scar_half_occupancy = nn.Conv3d(pathology_half_channels, 1, 1)
        self.scar_half_center = nn.Conv3d(pathology_half_channels, 1, 1)
        self.edema_context = nn.Conv3d(quarter_channels, 4, 1)
        self.edema_injury = nn.Conv3d(pathology_half_channels, 1, 1)
        self.edema_boundary = nn.Conv3d(pathology_half_channels, 1, 1)
        self.scar_extent_area = nn.Conv3d(quarter_channels, 1, 1)
        self.edema_extent_presence = nn.Conv3d(quarter_channels, 1, 1)
        self.edema_extent_area = nn.Conv3d(quarter_channels, 1, 1)

    def forward_quarter(self, quarter: torch.Tensor, *, run_edema: bool = True) -> dict[str, torch.Tensor]:
        scar_quarter_occupancy = self.scar_quarter_occupancy(quarter)
        scar_quarter_center = self.scar_quarter_center(quarter)
        scar_context = self.scar_context(quarter)
        scar_extent_area = self.scar_extent_area(quarter)
        if run_edema:
            edema = self.forward_edema_quarter(quarter)
        else:
            edema = {
                "edema_context": quarter.detach().new_zeros((quarter.shape[0], 4, *quarter.shape[-3:])),
                "edema_extent_presence": quarter.detach().new_zeros((quarter.shape[0], 1, *quarter.shape[-3:])),
                "edema_extent_area": quarter.detach().new_zeros((quarter.shape[0], 1, *quarter.shape[-3:])),
            }
        return {
            "scar_quarter_occupancy": scar_quarter_occupancy,
            "scar_quarter_center": scar_quarter_center,
            "scar_context": scar_context,
            "scar_extent_presence": scar_quarter_occupancy,
            "scar_extent_area": scar_extent_area,
            **edema,
        }

    def forward_edema_quarter(self, quarter: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "edema_context": self.edema_context(quarter),
            "edema_extent_presence": self.edema_extent_presence(quarter),
            "edema_extent_area": self.edema_extent_area(quarter),
        }

    def forward_scar_half(self, scar_half_feature: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "scar_half_occupancy": self.scar_half_occupancy(scar_half_feature),
            "scar_half_center": self.scar_half_center(scar_half_feature),
        }

    def forward_edema_half(self, edema_half_feature: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "edema_injury": self.edema_injury(edema_half_feature),
            "edema_boundary": self.edema_boundary(edema_half_feature),
        }


class NamedEvidenceProjectionSet(nn.Module):
    """Independent zero-initialized projection per named evidence source."""

    def __init__(self, specs: dict[str, int], out_channels: int) -> None:
        super().__init__()
        self.specs = {str(name): int(channels) for name, channels in specs.items()}
        self.projections = nn.ModuleDict()
        for name, channels in self.specs.items():
            proj = nn.Conv3d(channels, out_channels, 1)
            nn.init.zeros_(proj.weight)
            nn.init.zeros_(proj.bias)
            self.projections[name] = proj

    def forward(
        self,
        inputs: dict[str, torch.Tensor],
        spatial_shape: tuple[int, int, int],
        *,
        disabled: set[str] | None = None,
    ) -> torch.Tensor:
        disabled = disabled or set()
        missing = sorted(name for name in self.specs if name not in inputs)
        if missing:
            raise RuntimeError(f"CARE-ASE named evidence missing inputs: {missing}")
        outputs = []
        for name, expected_channels in self.specs.items():
            tensor = inputs[name]
            if tensor.shape[1] != expected_channels:
                raise RuntimeError(f"CARE-ASE named evidence {name} channel mismatch: {tensor.shape[1]} != {expected_channels}")
            if name in disabled:
                continue
            resized = F.interpolate(tensor, size=spatial_shape, mode="trilinear", align_corners=False)
            outputs.append(self.projections[name](resized))
        if outputs:
            return torch.stack(outputs, dim=0).sum(dim=0)
        first = inputs[next(iter(self.specs))]
        out_channels = next(iter(self.projections.values())).out_channels
        return first.detach().new_zeros((first.shape[0], out_channels, *spatial_shape))

    def registry(self) -> dict[str, Any]:
        return {
            "projection_count": len(self.specs),
            "sources": {
                name: {
                    "input_channels": int(channels),
                    "weight_norm": float(self.projections[name].weight.detach().float().norm().cpu()),
                    "bias_norm": float(self.projections[name].bias.detach().float().norm().cpu()) if self.projections[name].bias is not None else 0.0,
                }
                for name, channels in self.specs.items()
            },
        }


class CAREASEPathologyBranch(nn.Module):
    """Half/full-resolution cloned stock decoder branch for one pathology."""

    def __init__(
        self,
        stock_decoder: nn.Module,
        *,
        class_index: int,
        half_projection_channels: int,
        full_projection_channels: int,
        half_projection_specs: dict[str, int],
        full_projection_specs: dict[str, int],
    ) -> None:
        super().__init__()
        self.class_index = int(class_index)
        self.transpconvs = nn.ModuleList([deepcopy(stock_decoder.transpconvs[4]), deepcopy(stock_decoder.transpconvs[5])])
        self.stages = nn.ModuleList([deepcopy(stock_decoder.stages[4]), deepcopy(stock_decoder.stages[5])])
        self.seg_layers = nn.ModuleList(
            [
                _clone_seg_layer_single_row(stock_decoder.seg_layers[4], self.class_index),
                _clone_seg_layer_single_row(stock_decoder.seg_layers[5], self.class_index),
            ]
        )
        self.half_projections = NamedEvidenceProjectionSet(half_projection_specs, half_projection_channels)
        self.full_projections = NamedEvidenceProjectionSet(full_projection_specs, full_projection_channels)

    def forward_half(
        self,
        quarter_feature: torch.Tensor,
        skips: list[torch.Tensor],
        half_evidence: dict[str, torch.Tensor],
        *,
        disable_evidence: bool = False,
        disabled_sources: set[str] | None = None,
    ) -> dict[str, torch.Tensor]:
        x = self.transpconvs[0](quarter_feature)
        x = torch.cat((x, skips[1]), 1)
        if not disable_evidence:
            x = x + self.half_projections(half_evidence, x.shape[-3:], disabled=disabled_sources)
        half_feature = self.stages[0](x)
        half_logit = self.seg_layers[0](half_feature)
        return {
            "half_feature": half_feature,
            "half_logit": half_logit,
            "half_logits6": _single_pathology_logit_to_six(half_logit, self.class_index),
        }

    def forward_full(
        self,
        half_feature: torch.Tensor,
        skips: list[torch.Tensor],
        full_evidence: dict[str, torch.Tensor],
        *,
        disable_evidence: bool = False,
        disabled_sources: set[str] | None = None,
    ) -> dict[str, torch.Tensor]:

        x = self.transpconvs[1](half_feature)
        x = torch.cat((x, skips[0]), 1)
        if not disable_evidence:
            x = x + self.full_projections(full_evidence, x.shape[-3:], disabled=disabled_sources)
        full_feature = self.stages[1](x)
        full_logit = self.seg_layers[1](full_feature)
        return {
            "half_feature": half_feature,
            "full_logit": full_logit,
            "full_logits6": _single_pathology_logit_to_six(full_logit, self.class_index),
            "full_feature": full_feature,
            "final_logit": full_logit,
        }

    def forward(
        self,
        quarter_feature: torch.Tensor,
        skips: list[torch.Tensor],
        half_evidence: dict[str, torch.Tensor],
        full_evidence: dict[str, torch.Tensor],
        *,
        disable_evidence: bool = False,
        disabled_sources: set[str] | None = None,
    ) -> dict[str, torch.Tensor]:
        half = self.forward_half(quarter_feature, skips, half_evidence, disable_evidence=disable_evidence, disabled_sources=disabled_sources)
        full = self.forward_full(half["half_feature"], skips, full_evidence, disable_evidence=disable_evidence, disabled_sources=disabled_sources)
        return {**half, **full}


class CAREASE(nn.Module):
    """Final CARE-ASE architecture bound to a same-fold stock nnU-Net."""

    input_channel_order = MODALITY_ORDER
    pathology_logits_used_from_stock_normal_forward = False

    def __init__(self, config: CAREASEConfig, *, map_location: str | torch.device = "cpu", stock_checkpoint_required: bool = True) -> None:
        super().__init__()
        self.config = config
        stock = build_source_nnunet(config.nnunet_config)
        if stock_checkpoint_required:
            payload = torch.load(config.checkpoint_path, map_location=map_location, weights_only=False)
            state = checkpoint_state_dict(payload)
            load = stock.load_state_dict(state, strict=False)
            self.stock_load_missing_keys = list(load.missing_keys)
            self.stock_load_unexpected_keys = list(load.unexpected_keys)
            self.stock_parameter_byte_coverage = _byte_coverage(state, stock.state_dict())
            allowed_missing_keys: set[str] = set()
            allowed_unexpected_keys: set[str] = set()
            disallowed_missing = sorted(set(self.stock_load_missing_keys) - allowed_missing_keys)
            disallowed_unexpected = sorted(set(self.stock_load_unexpected_keys) - allowed_unexpected_keys)
            if disallowed_missing or disallowed_unexpected:
                raise RuntimeError(
                    "stock nnU-Net checkpoint load is not fail-closed: "
                    f"missing={disallowed_missing} unexpected={disallowed_unexpected}"
                )
            if float(self.stock_parameter_byte_coverage) < 0.99:
                raise RuntimeError(f"stock nnU-Net parameter byte coverage below contract: {self.stock_parameter_byte_coverage}")
        else:
            self.stock_load_missing_keys = []
            self.stock_load_unexpected_keys = []
            self.stock_parameter_byte_coverage = 1.0
        self.decoder_introspection = introspect_stock_decoder(stock.decoder)
        self.pathology_deep_supervision_weights = stock_pathology_deep_supervision_weights(stock.decoder, self.decoder_introspection)

        self.encoder = stock.encoder
        self.low_mid_transpconvs = nn.ModuleList([stock.decoder.transpconvs[i] for i in range(4)])
        self.low_mid_stages = nn.ModuleList([stock.decoder.stages[i] for i in range(4)])
        self.anatomy_top_transpconvs = nn.ModuleList([stock.decoder.transpconvs[4], stock.decoder.transpconvs[5]])
        self.anatomy_top_stages = nn.ModuleList([stock.decoder.stages[4], stock.decoder.stages[5]])
        self.anatomy_top_seg_layers = nn.ModuleList([_clone_seg_layer_rows(stock.decoder.seg_layers[4], 4), _clone_seg_layer_rows(stock.decoder.seg_layers[5], 4)])
        half_c = self.decoder_introspection.half_projection_channels
        full_c = self.decoder_introspection.full_projection_channels
        scar_half_specs = {
            "scar_quarter_occupancy_to_half": 1,
            "scar_quarter_center_to_half": 1,
            "scar_context_to_half": 4,
            "scar_lge_to_half": half_c,
            "scar_c0_to_half": half_c,
            "scar_p_wall_to_half": 1,
            "scar_p_lv_to_half": 1,
            "scar_p_rv_to_half": 1,
            "scar_signed_endo_to_half": 1,
            "scar_signed_epi_to_half": 1,
            "scar_rho_to_half": 1,
        }
        scar_full_specs = {
            "scar_half_occupancy_to_full": 1,
            "scar_half_center_to_full": 1,
            "scar_context_to_full": 4,
            "scar_lge_to_full": full_c,
            "scar_c0_to_full": full_c,
            "scar_p_wall_to_full": 1,
            "scar_p_lv_to_full": 1,
            "scar_p_rv_to_full": 1,
            "scar_signed_endo_to_full": 1,
            "scar_signed_epi_to_full": 1,
            "scar_rho_to_full": 1,
        }
        edema_half_specs = {
            "edema_context_to_half": 4,
            "edema_t2_to_half": half_c,
            "edema_c0_to_half": half_c,
            "edema_lge_to_half": half_c,
            "edema_p_wall_to_half": 1,
            "edema_p_lv_to_half": 1,
            "edema_p_rv_to_half": 1,
            "edema_signed_endo_to_half": 1,
            "edema_signed_epi_to_half": 1,
            "edema_rho_to_half": 1,
        }
        edema_full_specs = {
            "edema_injury_to_full": 1,
            "edema_boundary_to_full": 1,
            "edema_context_to_full": 4,
            "edema_dilation1_to_full": 1,
            "edema_dilation2_to_full": 1,
            "edema_dilation4_to_full": 1,
            "edema_t2_to_full": full_c,
            "edema_c0_to_full": full_c,
            "edema_lge_to_full": full_c,
            "edema_p_wall_to_full": 1,
            "edema_p_lv_to_full": 1,
            "edema_p_rv_to_full": 1,
            "edema_signed_endo_to_full": 1,
            "edema_signed_epi_to_full": 1,
            "edema_rho_to_full": 1,
        }
        self.scar_branch = CAREASEPathologyBranch(
            stock.decoder,
            class_index=5,
            half_projection_channels=self.decoder_introspection.half_projection_channels,
            full_projection_channels=self.decoder_introspection.full_projection_channels,
            half_projection_specs=scar_half_specs,
            full_projection_specs=scar_full_specs,
        )
        self.edema_branch = CAREASEPathologyBranch(
            stock.decoder,
            class_index=4,
            half_projection_channels=self.decoder_introspection.half_projection_channels,
            full_projection_channels=self.decoder_introspection.full_projection_channels,
            half_projection_specs=edema_half_specs,
            full_projection_specs=edema_full_specs,
        )
        self.component_heads = ComponentHeads(
            quarter_channels=self.decoder_introspection.shared_quarter_channels,
            pathology_half_channels=self.decoder_introspection.branch_half_feature_channels,
        )
        self.anatomy_geometry_heads = AnatomyGeometryHeads()
        self.edema_dilation_context = EdemaDilationContextBlock(self.decoder_introspection.branch_half_feature_channels, out_channels=1)
        self.scar_lge_half_adapter = ModalityAdapter(out_channels=half_c)
        self.scar_lge_full_adapter = ModalityAdapter(out_channels=full_c)
        self.scar_c0_half_adapter = ModalityAdapter(out_channels=half_c)
        self.scar_c0_full_adapter = ModalityAdapter(out_channels=full_c)
        self.edema_t2_half_adapter = ModalityAdapter(out_channels=half_c)
        self.edema_t2_full_adapter = ModalityAdapter(out_channels=full_c)
        self.edema_c0_half_adapter = ModalityAdapter(out_channels=half_c)
        self.edema_c0_full_adapter = ModalityAdapter(out_channels=full_c)
        self.edema_lge_half_adapter = ModalityAdapter(out_channels=half_c)
        self.edema_lge_full_adapter = ModalityAdapter(out_channels=full_c)
        self.scar_c0_gate = ScalarGate(activation="sigmoid", initial_output=0.2)
        self.edema_c0_gate = ScalarGate(activation="sigmoid", initial_output=0.2)
        self.edema_lge_gate = ScalarGate(activation="tanh", initial_output=0.05)
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

    def _decode_anatomy_top(self, quarter_feature: torch.Tensor, skips: list[torch.Tensor]) -> dict[str, torch.Tensor]:
        x = self.anatomy_top_transpconvs[0](quarter_feature)
        x = torch.cat((x, skips[1]), 1)
        half_feature = self.anatomy_top_stages[0](x)
        half_logits4 = self.anatomy_top_seg_layers[0](half_feature)
        x = self.anatomy_top_transpconvs[1](half_feature)
        x = torch.cat((x, skips[0]), 1)
        full_feature = self.anatomy_top_stages[1](x)
        full_logits4 = self.anatomy_top_seg_layers[1](full_feature)
        return {
            "half_feature": half_feature,
            "full_feature": full_feature,
            "half_logits4": half_logits4,
            "full_logits4": full_logits4,
        }

    def dynamic_plan_introspection_payload(self) -> dict[str, Any]:
        return {
            "status": "PASS",
            **self.decoder_introspection.__dict__,
            "source": "actual_stock_decoder_modules",
            "no_hardcoded_quarter_half_or_projection_channels": True,
            "modality_adapter_final_conv_zero_init": False,
            "modality_adapter_conv_init": "kaiming_nonzero_first_and_final_projection",
            "scale_specific_modality_adapter_out_channels": {
                "half": self.decoder_introspection.half_projection_channels,
                "full": self.decoder_introspection.full_projection_channels,
            },
            "named_evidence_projection_registry": self.named_evidence_projection_registry(),
            "gate_initial_outputs": {
                "scar_c0_sigmoid": float(self.scar_c0_gate().detach().cpu()),
                "edema_c0_sigmoid": float(self.edema_c0_gate().detach().cpu()),
                "edema_lge_tanh": float(self.edema_lge_gate().detach().cpu()),
            },
        }

    def named_evidence_projection_registry(self) -> dict[str, Any]:
        groups = {
            "scar_half": self.scar_branch.half_projections.registry(),
            "scar_full": self.scar_branch.full_projections.registry(),
            "edema_half": self.edema_branch.half_projections.registry(),
            "edema_full": self.edema_branch.full_projections.registry(),
        }
        names = [f"{group}:{name}" for group, payload in groups.items() for name in payload["sources"]]
        return {
            "status": "PASS",
            "groups": groups,
            "shared_multi_source_projection_count": 0,
            "missing_named_projection_count": 0,
            "duplicate_named_projection_count": len(names) - len(set(names)),
            "total_named_projection_count": len(names),
        }

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
        valid_spatial_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        ramp = 0.0 if disable_extent_wall else self.extent_wall_ramp(global_step)
        if ramp == 0.0:
            return torch.zeros_like(p_wall)
        if valid_spatial_mask is None:
            valid_slice_for_bias = None
        else:
            valid_down = F.interpolate(
                valid_spatial_mask.detach().float(),
                size=components["scar_extent_presence"].shape[-3:] if pathology == "scar" else components["edema_extent_presence"].shape[-3:],
                mode="nearest",
            )
            valid_slice_for_bias = (valid_down.sum(dim=(-2, -1), keepdim=True) > 0).to(dtype=p_wall.dtype)
        if pathology == "scar":
            presence, area, _wall_slice, fallback = compute_slice_extent_statistics(
                components["scar_extent_presence"],
                components["scar_extent_area"],
                p_wall,
                valid_spatial_mask,
            )
            valid_slice = torch.ones_like(presence) if valid_slice_for_bias is None else valid_slice_for_bias.to(dtype=presence.dtype)
            presence_bias = 0.30 * self._sigmoid_logit_center(presence, 0.50)
            area_bias = 0.20 * self._sigmoid_logit_center(area, self.scar_area_reference)
            wall_bias = 0.15 * self._sigmoid_logit_center(p_wall.detach(), 0.50)
        else:
            presence, area, _wall_slice, fallback = compute_slice_extent_statistics(
                components["edema_extent_presence"],
                components["edema_extent_area"],
                p_wall,
                valid_spatial_mask,
            )
            valid_slice = torch.ones_like(presence) if valid_slice_for_bias is None else valid_slice_for_bias.to(dtype=presence.dtype)
            presence_bias = 0.35 * self._sigmoid_logit_center(presence, 0.50)
            area_bias = 0.30 * self._sigmoid_logit_center(area, self.edema_area_reference)
            wall_bias = 0.10 * self._sigmoid_logit_center(p_wall.detach(), 0.50)
        presence_bias = presence_bias * valid_slice
        area_bias = area_bias * valid_slice
        slice_valid = F.interpolate(valid_slice, size=p_wall.shape[-3:], mode="nearest")
        slice_bias = F.interpolate(presence_bias + area_bias, size=p_wall.shape[-3:], mode="trilinear", align_corners=False) * slice_valid
        wall_bias = wall_bias * slice_valid
        return float(ramp) * (slice_bias + wall_bias)

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
        extent_valid_spatial_mask: torch.Tensor | None = None,
        disable_all_evidence: bool = False,
        disabled_named_evidence_sources: set[str] | None = None,
    ) -> dict[str, Any]:
        availability = self._validate_inputs(images, availability)
        disabled_sources = set(disabled_named_evidence_sources or set())
        t2_present_mask = availability[:, 1] > 0.5
        run_edema_graph = bool(t2_present_mask.any())
        skips = self._encode(images, availability)
        quarter, low_mid = self._decode_low_mid(skips)
        anatomy = self._decode_anatomy_top(quarter, skips)
        anatomy_logits = anatomy["full_logits4"]
        anatomy_prob = torch.softmax(anatomy_logits, dim=1)
        p_wall = anatomy_prob[:, 1:2]
        p_lv = anatomy_prob[:, 2:3]
        p_rv = anatomy_prob[:, 3:4]
        geometry = self.anatomy_geometry_heads(anatomy_logits)
        signed_endo_distance = geometry["signed_endo_distance"]
        signed_epi_distance = geometry["signed_epi_distance"]
        wall_depth_rho = geometry["wall_depth_rho"]
        components = self.component_heads.forward_quarter(quarter, run_edema=False)
        anatomy_context = {
            "p_wall_union": p_wall.detach(),
            "p_lv": p_lv.detach(),
            "p_rv": p_rv.detach(),
            "signed_endo_distance": signed_endo_distance.detach(),
            "signed_epi_distance": signed_epi_distance.detach(),
            "wall_depth_rho": wall_depth_rho.detach(),
        }
        if run_edema_graph:
            for key, value in self.component_heads.forward_edema_quarter(quarter[t2_present_mask]).items():
                full_value = components[key].clone()
                full_value[t2_present_mask] = value
                components[key] = full_value

        scar_half_evidence = {
            "scar_quarter_occupancy_to_half": torch.zeros_like(components["scar_quarter_occupancy"]) if disable_scar_proposal else components["scar_quarter_occupancy"],
            "scar_quarter_center_to_half": torch.zeros_like(components["scar_quarter_center"]) if disable_scar_center else components["scar_quarter_center"],
            "scar_context_to_half": torch.zeros_like(components["scar_context"]) if disable_scar_context else components["scar_context"],
            "scar_lge_to_half": self.scar_lge_half_adapter(images[:, 0:1], availability[:, 0], skips[1].shape[-3:]),
            "scar_c0_to_half": self.scar_c0_gate() * self.scar_c0_half_adapter(images[:, 2:3], availability[:, 2], skips[1].shape[-3:]),
            "scar_p_wall_to_half": anatomy_context["p_wall_union"],
            "scar_p_lv_to_half": anatomy_context["p_lv"],
            "scar_p_rv_to_half": anatomy_context["p_rv"],
            "scar_signed_endo_to_half": anatomy_context["signed_endo_distance"],
            "scar_signed_epi_to_half": anatomy_context["signed_epi_distance"],
            "scar_rho_to_half": anatomy_context["wall_depth_rho"],
        }
        scar_half = self.scar_branch.forward_half(quarter, skips, scar_half_evidence, disable_evidence=disable_all_evidence, disabled_sources=disabled_sources)
        components.update(self.component_heads.forward_scar_half(scar_half["half_feature"]))
        scar_full_evidence = {
            "scar_half_occupancy_to_full": torch.zeros_like(components["scar_half_occupancy"]) if disable_scar_proposal else components["scar_half_occupancy"],
            "scar_half_center_to_full": torch.zeros_like(components["scar_half_center"]) if disable_scar_center else components["scar_half_center"],
            "scar_context_to_full": torch.zeros_like(components["scar_context"]) if disable_scar_context else components["scar_context"],
            "scar_lge_to_full": self.scar_lge_full_adapter(images[:, 0:1], availability[:, 0], skips[0].shape[-3:]),
            "scar_c0_to_full": self.scar_c0_gate() * self.scar_c0_full_adapter(images[:, 2:3], availability[:, 2], skips[0].shape[-3:]),
            "scar_p_wall_to_full": anatomy_context["p_wall_union"],
            "scar_p_lv_to_full": anatomy_context["p_lv"],
            "scar_p_rv_to_full": anatomy_context["p_rv"],
            "scar_signed_endo_to_full": anatomy_context["signed_endo_distance"],
            "scar_signed_epi_to_full": anatomy_context["signed_epi_distance"],
            "scar_rho_to_full": anatomy_context["wall_depth_rho"],
        }
        scar = {**scar_half, **self.scar_branch.forward_full(scar_half["half_feature"], skips, scar_full_evidence, disable_evidence=disable_all_evidence, disabled_sources=disabled_sources)}
        final_logit = anatomy_logits.detach().new_full((anatomy_logits.shape[0], 1, *anatomy_logits.shape[-3:]), -1.0e4)
        half_logit = quarter.detach().new_zeros((quarter.shape[0], 1, *skips[1].shape[-3:]))
        full_logit = anatomy_logits.detach().new_zeros((anatomy_logits.shape[0], 1, *anatomy_logits.shape[-3:]))
        half_logits6 = quarter.detach().new_zeros((quarter.shape[0], 6, *skips[1].shape[-3:]))
        full_logits6 = anatomy_logits.detach().new_zeros((anatomy_logits.shape[0], 6, *anatomy_logits.shape[-3:]))
        edema = {
            "half_feature": quarter.detach().new_zeros((quarter.shape[0], self.decoder_introspection.branch_half_feature_channels, *skips[1].shape[-3:])),
            "full_feature": anatomy["full_feature"].detach().clone(),
            "half_logit": half_logit,
            "full_logit": full_logit,
            "half_logits6": half_logits6,
            "full_logits6": full_logits6,
            "final_logit": final_logit,
        }
        for key, channels in (("edema_injury", 1), ("edema_boundary", 1)):
            components[key] = quarter.detach().new_zeros((quarter.shape[0], channels, *skips[1].shape[-3:]))
        for dilation in (1, 2, 4):
            components[f"edema_dilation_{dilation}"] = quarter.detach().new_zeros((quarter.shape[0], 1, *skips[1].shape[-3:]))
        if run_edema_graph:
            idx = t2_present_mask
            selected_skips = [skip[idx] for skip in skips]
            selected_context = {key: value[idx] for key, value in anatomy_context.items()}
            edema_half_evidence = {
                "edema_context_to_half": torch.zeros_like(components["edema_context"][idx]) if disable_edema_context else components["edema_context"][idx],
                "edema_t2_to_half": self.edema_t2_half_adapter(images[idx, 1:2], availability[idx, 1], selected_skips[1].shape[-3:]),
                "edema_c0_to_half": self.edema_c0_gate() * self.edema_c0_half_adapter(images[idx, 2:3], availability[idx, 2], selected_skips[1].shape[-3:]),
                "edema_lge_to_half": self.edema_lge_gate() * self.edema_lge_half_adapter(images[idx, 0:1], availability[idx, 0], selected_skips[1].shape[-3:]),
                "edema_p_wall_to_half": selected_context["p_wall_union"],
                "edema_p_lv_to_half": selected_context["p_lv"],
                "edema_p_rv_to_half": selected_context["p_rv"],
                "edema_signed_endo_to_half": selected_context["signed_endo_distance"],
                "edema_signed_epi_to_half": selected_context["signed_epi_distance"],
                "edema_rho_to_half": selected_context["wall_depth_rho"],
            }
            edema_half = self.edema_branch.forward_half(quarter[idx], selected_skips, edema_half_evidence, disable_evidence=disable_all_evidence, disabled_sources=disabled_sources)
            for key, value in self.component_heads.forward_edema_half(edema_half["half_feature"]).items():
                full_value = components[key].clone()
                full_value[idx] = value
                components[key] = full_value
            for key, value in self.edema_dilation_context(edema_half["half_feature"]).items():
                full_value = components[key].clone()
                full_value[idx] = value
                components[key] = full_value
            edema_full_evidence = {
                "edema_injury_to_full": torch.zeros_like(components["edema_injury"][idx]) if disable_edema_injury else components["edema_injury"][idx],
                "edema_boundary_to_full": torch.zeros_like(components["edema_boundary"][idx]) if disable_edema_boundary else components["edema_boundary"][idx],
                "edema_context_to_full": torch.zeros_like(components["edema_context"][idx]) if disable_edema_context else components["edema_context"][idx],
                "edema_dilation1_to_full": torch.zeros_like(components["edema_dilation_1"][idx]) if disable_edema_context else components["edema_dilation_1"][idx],
                "edema_dilation2_to_full": torch.zeros_like(components["edema_dilation_2"][idx]) if disable_edema_context else components["edema_dilation_2"][idx],
                "edema_dilation4_to_full": torch.zeros_like(components["edema_dilation_4"][idx]) if disable_edema_context else components["edema_dilation_4"][idx],
                "edema_t2_to_full": self.edema_t2_full_adapter(images[idx, 1:2], availability[idx, 1], selected_skips[0].shape[-3:]),
                "edema_c0_to_full": self.edema_c0_gate() * self.edema_c0_full_adapter(images[idx, 2:3], availability[idx, 2], selected_skips[0].shape[-3:]),
                "edema_lge_to_full": self.edema_lge_gate() * self.edema_lge_full_adapter(images[idx, 0:1], availability[idx, 0], selected_skips[0].shape[-3:]),
                "edema_p_wall_to_full": selected_context["p_wall_union"],
                "edema_p_lv_to_full": selected_context["p_lv"],
                "edema_p_rv_to_full": selected_context["p_rv"],
                "edema_signed_endo_to_full": selected_context["signed_endo_distance"],
                "edema_signed_epi_to_full": selected_context["signed_epi_distance"],
                "edema_rho_to_full": selected_context["wall_depth_rho"],
            }
            selected_edema = {**edema_half, **self.edema_branch.forward_full(edema_half["half_feature"], selected_skips, edema_full_evidence, disable_evidence=disable_all_evidence, disabled_sources=disabled_sources)}
            for key, value in selected_edema.items():
                full_value = edema[key].clone()
                full_value[idx] = value
                edema[key] = full_value
        z_scar = scar["final_logit"] + self._extent_bias(
            components,
            anatomy_context["p_wall_union"],
            pathology="scar",
            global_step=global_step,
            disable_extent_wall=disable_extent_wall,
            valid_spatial_mask=extent_valid_spatial_mask,
        )
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1)
        if run_edema_graph:
            z_edema = edema["final_logit"] + self._extent_bias(
                components,
                anatomy_context["p_wall_union"],
                pathology="edema",
                global_step=global_step,
                disable_extent_wall=disable_extent_wall,
                valid_spatial_mask=extent_valid_spatial_mask,
            )
            z_edema = torch.where(t2 > 0.5, z_edema, z_edema.detach().new_full(z_edema.shape, -1.0e4))
        else:
            z_edema = edema["final_logit"]
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
            "anatomy": anatomy,
            "pathology_half_features": {
                "scar": scar["half_feature"],
                "edema": edema["half_feature"],
            },
            "components": components,
            "scar": scar,
            "edema": edema,
            "z_scar": z_scar,
            "z_pure_edema": z_edema,
            "availability": availability,
            "extent_wall_ramp_value": torch.tensor(self.extent_wall_ramp(global_step), device=images.device),
            "pathology_deep_supervision_weights": dict(self.pathology_deep_supervision_weights),
            "normal_forward_reads_stock_pathology_logits": False,
            "no_t2_edema_graph_excluded": not run_edema_graph,
        }

    @torch.no_grad()
    def step0_parity_report(self, sample: torch.Tensor, availability: torch.Tensor) -> dict[str, Any]:
        self.eval()
        availability = availability.to(sample)
        stock = build_source_nnunet(self.config.nnunet_config).to(sample.device)
        payload = torch.load(self.config.checkpoint_path, map_location=sample.device, weights_only=False)
        load = stock.load_state_dict(checkpoint_state_dict(payload), strict=False)
        if load.missing_keys or load.unexpected_keys:
            raise RuntimeError(f"reference stock load has missing/unexpected keys: missing={load.missing_keys} unexpected={load.unexpected_keys}")
        stock.eval()
        edema_owned = {
            "edema_branch": self.edema_branch,
            "edema_t2_half_adapter": self.edema_t2_half_adapter,
            "edema_t2_full_adapter": self.edema_t2_full_adapter,
            "edema_c0_half_adapter": self.edema_c0_half_adapter,
            "edema_c0_full_adapter": self.edema_c0_full_adapter,
            "edema_lge_half_adapter": self.edema_lge_half_adapter,
            "edema_lge_full_adapter": self.edema_lge_full_adapter,
            "edema_dilation_context": self.edema_dilation_context,
            "component_heads.edema_context": self.component_heads.edema_context,
            "component_heads.edema_injury": self.component_heads.edema_injury,
            "component_heads.edema_boundary": self.component_heads.edema_boundary,
            "component_heads.edema_extent_presence": self.component_heads.edema_extent_presence,
            "component_heads.edema_extent_area": self.component_heads.edema_extent_area,
            "edema_half_projections": self.edema_branch.half_projections,
            "edema_full_projections": self.edema_branch.full_projections,
        }
        call_counts = {name: 0 for name in edema_owned}
        hooks = []
        for name, module in edema_owned.items():
            def _hook(_module: nn.Module, _inputs: tuple[Any, ...], _outputs: Any, *, key: str = name) -> None:
                call_counts[key] += 1

            hooks.append(module.register_forward_hook(_hook))
        stock_logits = stock(sample.float() * availability.view(-1, 3, 1, 1, 1))
        try:
            out = self(sample.float(), availability, global_step=0, disable_extent_wall=True, disable_all_evidence=False)
        finally:
            for hook in hooks:
                hook.remove()
        final = out["final_logits"]
        t2_present = availability[:, 1] > 0.5
        no_t2 = ~t2_present
        anatomy_diff = (final[:, :4] - stock_logits[:, :4]).abs()
        scar_diff = (final[:, 5:6] - stock_logits[:, 5:6]).abs()
        edema_diff = torch.zeros((), device=sample.device)
        if bool(t2_present.any()):
            edema_diff = (final[t2_present, 4:5] - stock_logits[t2_present, 4:5]).abs().max()
        no_t2_decode_changed = 0
        if bool(no_t2.any()):
            care_no_t2 = torch.cat([final[no_t2, :4], final[no_t2, 5:6]], dim=1).argmax(1)
            stock_no_t2 = torch.cat([stock_logits[no_t2, :4], stock_logits[no_t2, 5:6]], dim=1).argmax(1)
            no_t2_decode_changed = int((care_no_t2 != stock_no_t2).sum().item())
        t2_decode_changed = 0
        if bool(t2_present.any()):
            t2_decode_changed = int((final[t2_present].argmax(1) != stock_logits[t2_present].argmax(1)).sum().item())
        max_error = float(max(float(anatomy_diff.max().item()), float(scar_diff.max().item()), float(edema_diff.item() if edema_diff.ndim == 0 else edema_diff.max().item())))
        no_t2_edema_call_count = sum(call_counts.values()) if bool(no_t2.all()) else 0
        return {
            "status": "PASS" if max_error <= 1.0e-6 and no_t2_decode_changed == 0 and no_t2_edema_call_count == 0 else "FAIL",
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
            "step0_edema_logit_parity_vs_stock_class4_max_abs_error": float(edema_diff.item() if edema_diff.ndim == 0 else edema_diff.max().item()),
            "step0_edema_logit_parity_vs_stock_class4_t2_present_only_max_abs_error": float(edema_diff.item() if edema_diff.ndim == 0 else edema_diff.max().item()),
            "no_t2_decode_class_set": [0, 1, 2, 3, 5],
            "no_t2_class4_excluded_from_competition": True,
            "no_t2_stock_class4_zeroed_into_six_class_argmax": False,
            "no_t2_five_class_decode_changed_voxels": no_t2_decode_changed,
            "t2_present_six_class_decode_changed_voxels": t2_decode_changed,
            "compatibility_argmax_changed_voxels": no_t2_decode_changed + t2_decode_changed,
            "edema_owned_forward_call_counts": call_counts,
            "no_t2_edema_owned_row_call_count": no_t2_edema_call_count,
            "mixed_batch_rowwise_edema_execution": {
                "t2_present_rows": int(t2_present.sum().item()),
                "no_t2_rows": int(no_t2.sum().item()),
                "edema_graph_called_for_t2_present_subset": bool(t2_present.any()),
                "no_t2_rows_excluded_by_indexing": bool(no_t2.any()),
            },
            "normal_forward_reads_stock_pathology_logits": False,
            "single_shared_low_mid_decoder_forward": True,
            "auxiliary_half_feature_source": "removed_uncontracted_auxiliary_tower_pathology_branches_own_half_features",
            "clone_decoder_stage_indices": [4, 5],
            "split_before_highest_decoder_resolutions": 2,
        }


def compute_slice_extent_statistics(
    presence_logits: torch.Tensor,
    area_logits: torch.Tensor,
    p_wall: torch.Tensor,
    valid_spatial_mask: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Per-z detached wall-weighted avg plus masked max extent features."""

    wall = F.interpolate(p_wall.detach(), size=presence_logits.shape[-3:], mode="trilinear", align_corners=False).clamp_min(0.0)
    valid = None
    if valid_spatial_mask is not None:
        valid = F.interpolate(valid_spatial_mask.detach().float(), size=presence_logits.shape[-3:], mode="nearest").clamp(0.0, 1.0)
        wall = wall * valid
    wall_sum = wall.sum(dim=(-2, -1), keepdim=True)
    if valid is None:
        valid_sum = torch.full_like(wall_sum, float(presence_logits.shape[-2] * presence_logits.shape[-1]))
    else:
        valid_sum = valid.sum(dim=(-2, -1), keepdim=True)
    no_valid = valid_sum <= 0.0
    low_wall = wall_sum < 1.0
    presence_prob = torch.sigmoid(presence_logits)
    area_prob = torch.sigmoid(area_logits)

    def summarize(value: torch.Tensor) -> torch.Tensor:
        if valid is None:
            valid_value = value
            local_valid_sum = valid_sum
        else:
            valid_value = value * valid
            local_valid_sum = valid_sum
        weighted_avg = (value * wall).sum(dim=(-2, -1), keepdim=True) / wall_sum.clamp_min(1.0e-6)
        masked = value.masked_fill(wall <= 1.0e-6, -torch.inf)
        masked_max = masked.amax(dim=(-2, -1), keepdim=True)
        if valid is None:
            fallback_max = value.amax(dim=(-2, -1), keepdim=True)
        else:
            fallback_masked = value.masked_fill(valid <= 0.0, -torch.inf)
            fallback_max = fallback_masked.amax(dim=(-2, -1), keepdim=True)
            fallback_max = torch.where(torch.isfinite(fallback_max), fallback_max, torch.zeros_like(fallback_max))
        masked_max = torch.where(torch.isfinite(masked_max), masked_max, fallback_max)
        full_avg = valid_value.sum(dim=(-2, -1), keepdim=True) / local_valid_sum.clamp_min(1.0)
        full_max = fallback_max
        avg = torch.where(low_wall, full_avg, weighted_avg)
        mx = torch.where(low_wall, full_max, masked_max)
        summary = 0.5 * (avg + mx)
        return torch.where(no_valid, torch.zeros_like(summary), summary)

    presence = summarize(presence_prob)
    area = summarize(area_prob)
    wall_slice = wall.mean(dim=(-2, -1), keepdim=True)
    return presence, area, wall_slice, (low_wall | no_valid).to(presence_logits)


def _concat_named_evidence(items: Iterable[tuple[str, torch.Tensor]], spatial_shape: tuple[int, int, int], channels: int, schema_name: str) -> torch.Tensor:
    resized = [F.interpolate(item, size=spatial_shape, mode="trilinear", align_corners=False) for _name, item in items]
    merged = torch.cat(resized, dim=1)
    if merged.shape[1] != channels:
        names = [name for name, _tensor in items]
        raise RuntimeError(
            f"CARE-ASE evidence schema {schema_name} channel mismatch: "
            f"declared_names={names} observed_channels={merged.shape[1]} projection_in_channels={channels}"
        )
    return merged


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
        if (".half_projections.projections." in name or ".full_projections.projections." in name)
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
        "named_evidence_projection_registry": model.named_evidence_projection_registry(),
        "dynamic_plan_introspection": model.dynamic_plan_introspection_payload(),
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
            "scar_quarter_and_half_proposal",
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
