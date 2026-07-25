from __future__ import annotations

import torch
from torch import nn

from myops.models.encoder import Decoder2D, Encoder2D, ReferenceDecoder2D
from myops.models.msf_decoder import MSFDecoder
from myops.models.spg import SpatialPriorGate
from myops.models.tps import TPSHead, TPSWarper


class FinePathNet(nn.Module):
    """Multi-encoder + MSF + SPG + TPS network for fine-stage pathology segmentation (Stage 2a).

    Input tensor layout [B, 7, H, W]:
        ch 0: LGE, ch 1: C0, ch 2: T2, ch 3-5: presence masks, ch 6: coarse prior.
    """

    def __init__(
        self,
        out_channels: int,
        base_channels: int = 16,
        grid_size: int = 4,
        span_range: float = 0.98,
        image_size: int = 192,
        deep_supervision: bool = True,
        use_tps: bool = True,
        use_spg: bool = True,
        use_consistency: bool = True,
        use_t2_aux: bool = False,
    ) -> None:
        super().__init__()
        self.base_channels = base_channels
        self.use_tps = use_tps
        self.use_spg = use_spg
        self.use_consistency = use_consistency
        self.use_t2_aux = use_t2_aux
        c = base_channels

        self.enc_lge = Encoder2D(1, c)
        self.enc_c0 = Encoder2D(1, c)
        self.enc_t2 = Encoder2D(1, c)

        if use_tps:
            self.tps_c0 = TPSHead(c * 16, grid_size, span_range, image_size)
            self.tps_t2 = TPSHead(c * 16, grid_size, span_range, image_size)
            self.warper = TPSWarper(grid_size, span_range, image_size, num_levels=4)

        self.msf_decoder = MSFDecoder(c, out_channels, deep_supervision=deep_supervision)

        if use_spg:
            self.spg = SpatialPriorGate()

        if use_consistency:
            self.myo_head_lge = Decoder2D(out_channels=1, base_channels=c)
            self.myo_head_c0 = Decoder2D(out_channels=1, base_channels=c)
            self.myo_head_t2 = Decoder2D(out_channels=1, base_channels=c)

        if use_t2_aux:
            self.t2_edema_decoder = ReferenceDecoder2D(out_channels=1, base_channels=c)

    def forward(self, image: torch.Tensor) -> dict[str, torch.Tensor | list[torch.Tensor]]:
        lge = image[:, 0:1]
        c0 = image[:, 1:2]
        t2 = image[:, 2:3]
        presence = image[:, 3:6]
        coarse_prior = image[:, 6:7]

        feats_lge = self.enc_lge(lge)
        feats_c0 = self.enc_c0(c0)
        feats_t2 = self.enc_t2(t2)

        p_c0 = presence[:, 1:2, :1, :1]
        p_t2 = presence[:, 2:3, :1, :1]
        feats_c0 = [f * p_c0 for f in feats_c0]
        feats_t2 = [f * p_t2 for f in feats_t2]

        if self.use_tps:
            theta_c0 = self.tps_c0(torch.cat([feats_c0[-1], feats_lge[-1]], dim=1))
            theta_t2 = self.tps_t2(torch.cat([feats_t2[-1], feats_lge[-1]], dim=1))
            warped_c0 = [self.warper(f, theta_c0) for f in feats_c0]
            warped_t2 = [self.warper(f, theta_t2) for f in feats_t2]
        else:
            warped_c0 = feats_c0
            warped_t2 = feats_t2
            theta_c0 = None
            theta_t2 = None

        bottleneck = torch.cat([feats_lge[-1], warped_c0[-1], warped_t2[-1]], dim=1)

        spg = self.spg if self.use_spg else None
        logits, ds_logits = self.msf_decoder(
            bottleneck,
            feats_lge[:-1],
            warped_c0[:-1],
            warped_t2[:-1],
            spg_gate=spg,
            coarse_prior=coarse_prior,
        )

        outputs: dict[str, torch.Tensor | list[torch.Tensor]] = {"logits": logits}
        if ds_logits:
            outputs["deep_supervision"] = ds_logits

        if self.use_t2_aux:
            t2_main_feats = [
                torch.max(warped_t2[i], feats_lge[i])
                for i in range(len(feats_lge))
            ]
            outputs["t2_edema_logits"] = self.t2_edema_decoder(t2_main_feats, warped_t2)

        if self.training:
            if self.use_consistency:
                outputs["myo_preds"] = {
                    "lge": self.myo_head_lge(feats_lge),
                    "c0": self.myo_head_c0(feats_c0),
                    "t2": self.myo_head_t2(feats_t2),
                }
            if self.use_tps and theta_c0 is not None:
                outputs["theta_c0"] = theta_c0
                outputs["theta_t2"] = theta_t2

        return outputs
