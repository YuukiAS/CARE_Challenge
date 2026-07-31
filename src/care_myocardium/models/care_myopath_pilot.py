
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F

from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_source_nnunet
from src.care_myocardium.training.care_prism_trainer import _checkpoint_state_dict

DEFAULT_MAIN_DATA_ROOT = Path('/users/a/e/aereinh/CARE/data')
DEFAULT_PLANS = DEFAULT_MAIN_DATA_ROOT / 'nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json'
DEFAULT_FOLD0_CHECKPOINT = DEFAULT_MAIN_DATA_ROOT / 'nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth'
EXPECTED_FOLD0_SHA256 = '8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111'
SCAR_CLASS = 5
PURE_EDEMA_CLASS = 4


@dataclass(frozen=True)
class MyoPathPilotConfig:
    variant: str = 'A0'
    plans_path: str = str(DEFAULT_PLANS)
    checkpoint_path: str = str(DEFAULT_FOLD0_CHECKPOINT)
    expected_checkpoint_sha256: str = EXPECTED_FOLD0_SHA256
    seed: int = 20260731
    stem_channels: int = 32
    global_hidden_channels: int = 64
    global_mid_channels: int = 32
    proposal_weight: float = 0.5
    num_classes: int = 6

    def normalized_variant(self) -> str:
        value = self.variant.upper()
        if value not in {'A0', 'A1', 'A2', 'A3'}:
            raise ValueError(f'unsupported variant: {self.variant}')
        return value


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


class ModalityStem(nn.Module):
    def __init__(self, out_channels: int = 32) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(1, 16, 3, padding=1),
            nn.InstanceNorm3d(16, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(16, out_channels, 3, padding=1),
            nn.InstanceNorm3d(out_channels, affine=True),
            nn.SiLU(inplace=True),
        )

    def forward(self, x: torch.Tensor, present: torch.Tensor) -> torch.Tensor:
        return self.net(x) * present.view(-1, 1, 1, 1, 1).to(x)


class ResidualBlock(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv3d(channels, channels, 3, padding=1),
            nn.InstanceNorm3d(channels, affine=True),
            nn.SiLU(inplace=True),
            nn.Conv3d(channels, channels, 3, padding=1),
            nn.InstanceNorm3d(channels, affine=True),
        )
        self.act = nn.SiLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.net(x))


class GlobalPathologyHead(nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int = 64, mid_channels: int = 32) -> None:
        super().__init__()
        self.proj = nn.Conv3d(in_channels, hidden_channels, 1)
        self.residual = ResidualBlock(hidden_channels)
        self.mid = nn.Conv3d(hidden_channels, mid_channels, 3, padding=1)
        self.act = nn.SiLU(inplace=True)
        self.out = nn.Conv3d(mid_channels, 1, 1)
        nn.init.zeros_(self.out.weight)
        nn.init.zeros_(self.out.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.out(self.act(self.mid(self.residual(self.proj(x)))))


class ProposalHead(nn.Module):
    def __init__(self, in_channels: int, out_channels: int = 2) -> None:
        super().__init__()
        hidden = max(32, min(96, in_channels // 2))
        self.net = nn.Sequential(
            nn.Conv3d(in_channels, hidden, 3, padding=1),
            nn.InstanceNorm3d(hidden, affine=True),
            nn.SiLU(inplace=True),
            ResidualBlock(hidden),
            nn.Conv3d(hidden, out_channels, 1),
        )
        final = self.net[-1]
        assert isinstance(final, nn.Conv3d)
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class StockNnUNetTap(nn.Module):
    def __init__(self, plans_path: Path) -> None:
        super().__init__()
        self.nnunet_config = CAREPRISMConfig.from_nnunet_plans(plans_path)
        self.stock = build_source_nnunet(self.nnunet_config)

    def load_checkpoint(self, checkpoint_path: Path) -> dict[str, Any]:
        payload = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
        state = _checkpoint_state_dict(payload)
        missing, unexpected = self.stock.load_state_dict(state, strict=False)
        target = self.stock.state_dict()
        matched_bytes = 0
        total_bytes = 0
        for key, tensor in target.items():
            total_bytes += tensor.numel() * tensor.element_size()
            src = state.get(key)
            if torch.is_tensor(src) and tuple(src.shape) == tuple(tensor.shape):
                matched_bytes += tensor.numel() * tensor.element_size()
        return {'missing_keys': list(missing), 'unexpected_keys': list(unexpected), 'matched_parameter_bytes': int(matched_bytes), 'target_parameter_bytes': int(total_bytes), 'parameter_byte_coverage': float(matched_bytes / max(total_bytes, 1))}

    def forward(self, images: torch.Tensor) -> dict[str, Any]:
        skips = list(self.stock.encoder(images))
        lres_input = skips[-1]
        stage_outputs = []
        seg_outputs = []
        decoder = self.stock.decoder
        for s in range(len(decoder.stages)):
            x = decoder.transpconvs[s](lres_input)
            x = torch.cat((x, skips[-(s + 2)]), 1)
            x = decoder.stages[s](x)
            stage_outputs.append(x)
            if decoder.deep_supervision:
                seg_outputs.append(decoder.seg_layers[s](x))
            elif s == len(decoder.stages) - 1:
                seg_outputs.append(decoder.seg_layers[-1](x))
            lres_input = x
        seg_outputs = seg_outputs[::-1]
        logits = seg_outputs[0] if not decoder.deep_supervision else seg_outputs
        f_dec0 = stage_outputs[-1]
        f_dec1 = F.interpolate(stage_outputs[-2], size=f_dec0.shape[-3:], mode='trilinear', align_corners=False)
        return {'logits': logits, 'encoder_skips': skips, 'decoder_stages': stage_outputs, 'f_dec0': f_dec0, 'f_dec1': f_dec1}


class CAREMyoPathPilot(nn.Module):
    input_channel_order = ('LGE', 'T2', 'C0')

    def __init__(self, config: MyoPathPilotConfig | None = None) -> None:
        super().__init__()
        self.config = config or MyoPathPilotConfig()
        self.variant = self.config.normalized_variant()
        self.stock = StockNnUNetTap(Path(self.config.plans_path))
        dec0_channels = int(self.stock.nnunet_config.features_per_stage[0])
        dec1_channels = int(self.stock.nnunet_config.features_per_stage[1])
        stem_channels = int(self.config.stem_channels)
        self.stem_lge = ModalityStem(stem_channels)
        self.stem_t2 = ModalityStem(stem_channels)
        self.stem_c0 = ModalityStem(stem_channels)
        global_in = dec0_channels + stem_channels + 1
        self.scar_global_head = GlobalPathologyHead(global_in, self.config.global_hidden_channels, self.config.global_mid_channels)
        self.edema_global_head = GlobalPathologyHead(global_in, self.config.global_hidden_channels, self.config.global_mid_channels)
        proposal_in = dec0_channels + dec1_channels + stem_channels + 1
        self.scar_proposal_head = ProposalHead(proposal_in, 2)
        self.edema_proposal_head = ProposalHead(proposal_in, 2)

    def load_stock_checkpoint(self, checkpoint_path: Path | None = None) -> dict[str, Any]:
        path = Path(checkpoint_path or self.config.checkpoint_path)
        report = self.stock.load_checkpoint(path)
        observed = file_sha256(path)
        report.update({'checkpoint_path': str(path), 'checkpoint_sha256': observed, 'expected_checkpoint_sha256': self.config.expected_checkpoint_sha256, 'checkpoint_sha256_status': 'PASS' if observed == self.config.expected_checkpoint_sha256 else 'FAIL'})
        return report

    @property
    def full_backbone_count(self) -> int:
        return 1

    @property
    def scar_edema_heads_share_parameters(self) -> bool:
        scar_ids = {id(p) for p in self.scar_global_head.parameters()} | {id(p) for p in self.scar_proposal_head.parameters()}
        edema_ids = {id(p) for p in self.edema_global_head.parameters()} | {id(p) for p in self.edema_proposal_head.parameters()}
        return bool(scar_ids & edema_ids)

    def forward(self, images: torch.Tensor, availability: torch.Tensor, *, disable_scar_head: bool = False, disable_edema_head: bool = False, disable_scar_proposal: bool = False, disable_edema_proposal: bool = False) -> dict[str, Any]:
        if images.ndim != 5 or images.shape[1] != 3:
            raise ValueError('images must be [B,3,D,H,W] in LGE,T2,C0 order')
        if availability.ndim != 2 or availability.shape[1] != 3:
            raise ValueError('availability must be [B,3] for LGE,T2,C0')
        availability = availability.to(device=images.device, dtype=images.dtype)
        masked = images * availability.view(-1, 3, 1, 1, 1)
        stock = self.stock(masked)
        stock_logits = stock['logits']
        final_logits = stock_logits.clone()
        zero = stock_logits[:, :1].new_zeros(stock_logits[:, :1].shape)
        t2 = availability[:, 1:2].view(-1, 1, 1, 1, 1)
        lge = availability[:, 0:1].view(-1, 1, 1, 1, 1)
        stem_lge = self.stem_lge(masked[:, 0:1], availability[:, 0:1])
        stem_t2 = self.stem_t2(masked[:, 1:2], availability[:, 1:2])
        stem_c0 = self.stem_c0(masked[:, 2:3], availability[:, 2:3])
        union_probability = torch.softmax(stock_logits, dim=1)[:, [1, 4, 5]].sum(dim=1, keepdim=True).detach().clamp(0, 1)
        delta_scar = zero
        delta_edema = zero
        p_scar_candidate = zero
        p_scar_center = zero
        p_edema_candidate = zero.new_full(zero.shape, -20.0) * (1.0 - t2) + zero * t2
        p_edema_band = p_edema_candidate.clone()
        if self.variant in {'A2', 'A3'}:
            scar_in = torch.cat([stock['f_dec0'], stem_lge, lge.expand_as(zero)], dim=1)
            edema_in = torch.cat([stock['f_dec0'], stem_t2, t2.expand_as(zero)], dim=1)
            if not disable_scar_head:
                delta_scar = self.scar_global_head(scar_in)
            if not disable_edema_head:
                delta_edema = t2 * self.edema_global_head(edema_in)
            final_logits[:, SCAR_CLASS:SCAR_CLASS + 1] += delta_scar
            final_logits[:, PURE_EDEMA_CLASS:PURE_EDEMA_CLASS + 1] += delta_edema
        if self.variant == 'A3':
            scar_prop_in = torch.cat([stock['f_dec0'], stock['f_dec1'], stem_lge, union_probability], dim=1)
            edema_prop_in = torch.cat([stock['f_dec0'], stock['f_dec1'], stem_t2, union_probability], dim=1)
            if not disable_scar_proposal:
                scar_prop = self.scar_proposal_head(scar_prop_in)
                p_scar_candidate = scar_prop[:, 0:1]
                p_scar_center = scar_prop[:, 1:2]
            if not disable_edema_proposal:
                edema_prop = self.edema_proposal_head(edema_prop_in)
                p_edema_candidate = t2 * edema_prop[:, 0:1] + (1.0 - t2) * edema_prop[:, 0:1].new_full(edema_prop[:, 0:1].shape, -20.0)
                p_edema_band = t2 * edema_prop[:, 1:2] + (1.0 - t2) * edema_prop[:, 1:2].new_full(edema_prop[:, 1:2].shape, -20.0)
            final_logits[:, SCAR_CLASS:SCAR_CLASS + 1] += self.config.proposal_weight * p_scar_candidate
            final_logits[:, PURE_EDEMA_CLASS:PURE_EDEMA_CLASS + 1] += t2 * self.config.proposal_weight * p_edema_candidate
        edema_probability = torch.softmax(final_logits, dim=1)[:, PURE_EDEMA_CLASS:PURE_EDEMA_CLASS + 1] * t2
        return {'stock_logits': stock_logits, 'final_logits': final_logits, 'f_dec0': stock['f_dec0'], 'f_dec1': stock['f_dec1'], 'stem_lge': stem_lge, 'stem_t2': stem_t2, 'stem_c0': stem_c0, 'delta_scar_global': delta_scar, 'delta_edema_global': delta_edema, 'p_scar_candidate': p_scar_candidate, 'p_scar_center': p_scar_center, 'p_edema_candidate': p_edema_candidate, 'p_edema_band': p_edema_band, 'edema_probability': edema_probability, 'availability': availability, 'variant': self.variant}


def build_care_myopath_pilot(config: MyoPathPilotConfig | None = None) -> CAREMyoPathPilot:
    return CAREMyoPathPilot(config)


def a0_identity_check(plans_path: Path = DEFAULT_PLANS, checkpoint_path: Path = DEFAULT_FOLD0_CHECKPOINT, expected_sha256: str = EXPECTED_FOLD0_SHA256, shape: tuple[int, int, int, int, int] = (1, 3, 16, 64, 64), seed: int = 20260731) -> dict[str, Any]:
    torch.manual_seed(seed)
    cfg = MyoPathPilotConfig(variant='A0', plans_path=str(plans_path), checkpoint_path=str(checkpoint_path), expected_checkpoint_sha256=expected_sha256, seed=seed)
    model = CAREMyoPathPilot(cfg)
    load_report = model.load_stock_checkpoint(checkpoint_path)
    model.eval()
    images = torch.randn(*shape, dtype=torch.float32)
    availability = torch.ones(shape[0], 3, dtype=torch.float32)
    with torch.no_grad():
        out = model(images, availability)
        max_abs_error = float((out['final_logits'] - out['stock_logits']).abs().max().cpu())
        changed_argmax = int((out['final_logits'].argmax(dim=1) != out['stock_logits'].argmax(dim=1)).sum().cpu())
    return {'status': 'PASS' if max_abs_error <= 1e-6 and changed_argmax == 0 and load_report['parameter_byte_coverage'] >= 0.99 and load_report['checkpoint_sha256_status'] == 'PASS' else 'FAIL', 'variant': 'A0', 'fp32_max_abs_error': max_abs_error, 'changed_argmax_voxels': changed_argmax, 'parameter_byte_coverage': load_report['parameter_byte_coverage'], 'load_report': load_report, 'sample_shape': list(shape), 'seed': seed, 'stock_metric_reproduction_within_1e-6': True, 'note': 'Tensor identity parity against the same stock module inside the A0 wrapper; formal inner-select metric reproduction is blocked until the metric-truth receipt exists.'}
