from __future__ import annotations

import itertools

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


def _compute_partial_repr(input_points: torch.Tensor, control_points: torch.Tensor) -> torch.Tensor:
    N = input_points.size(0)
    M = control_points.size(0)
    pairwise_diff = input_points.view(N, 1, 2) - control_points.view(1, M, 2)
    pairwise_dist = (pairwise_diff * pairwise_diff).sum(dim=2)
    repr_matrix = 0.5 * pairwise_dist * torch.log(pairwise_dist + 1e-10)
    repr_matrix[repr_matrix != repr_matrix] = 0
    return repr_matrix


class TPSGridGen(nn.Module):
    def __init__(self, target_height: int, target_width: int, target_control_points: torch.Tensor) -> None:
        super().__init__()
        assert target_control_points.ndimension() == 2
        assert target_control_points.size(1) == 2
        N = target_control_points.size(0)
        self.num_points = N
        target_control_points = target_control_points.float()

        forward_kernel = torch.zeros(N + 3, N + 3)
        target_control_partial_repr = _compute_partial_repr(target_control_points, target_control_points)
        forward_kernel[:N, :N].copy_(target_control_partial_repr)
        forward_kernel[:N, -3].fill_(1)
        forward_kernel[-3, :N].fill_(1)
        forward_kernel[:N, -2:].copy_(target_control_points)
        forward_kernel[-2:, :N].copy_(target_control_points.transpose(0, 1))
        inverse_kernel = torch.inverse(forward_kernel)

        HW = target_height * target_width
        target_coordinate = torch.Tensor(list(itertools.product(range(target_height), range(target_width))))
        Y, X = target_coordinate.split(1, dim=1)
        Y = Y * 2 / (target_height - 1) - 1
        X = X * 2 / (target_width - 1) - 1
        target_coordinate = torch.cat([X, Y], dim=1)
        target_coordinate_partial_repr = _compute_partial_repr(target_coordinate, target_control_points)
        target_coordinate_repr = torch.cat(
            [target_coordinate_partial_repr, torch.ones(HW, 1), target_coordinate], dim=1,
        )

        self.register_buffer("inverse_kernel", inverse_kernel)
        self.register_buffer("padding_matrix", torch.zeros(3, 2))
        self.register_buffer("target_coordinate_repr", target_coordinate_repr)
        self.target_height = target_height
        self.target_width = target_width

    def forward(self, source_control_points: torch.Tensor) -> torch.Tensor:
        batch_size = source_control_points.size(0)
        Y = torch.cat([source_control_points, self.padding_matrix.expand(batch_size, 3, 2)], dim=1)
        mapping_matrix = torch.matmul(self.inverse_kernel, Y)
        source_coordinate = torch.matmul(self.target_coordinate_repr, mapping_matrix)
        return source_coordinate


class TPSHead(nn.Module):
    def __init__(
        self, in_channels: int, grid_size: int, span_range: float, image_size: int,
    ) -> None:
        super().__init__()
        self.grid_size = grid_size
        self.num_points = grid_size * grid_size

        r = span_range
        target_control_points = torch.Tensor(list(itertools.product(
            np.arange(-r, r + 1e-5, 2.0 * r / (grid_size - 1)),
            np.arange(-r, r + 1e-5, 2.0 * r / (grid_size - 1)),
        )))
        Y, X = target_control_points.split(1, dim=1)
        self.register_buffer("target_control_points", torch.cat([X, Y], dim=1))

        self.localization = nn.Sequential(
            nn.Conv2d(in_channels, in_channels // 2, kernel_size=3, padding=1),
            nn.InstanceNorm2d(in_channels // 2),
            nn.LeakyReLU(inplace=True),
            nn.AdaptiveAvgPool2d(4),
            nn.Conv2d(in_channels // 2, in_channels // 4, kernel_size=3, padding=1),
            nn.InstanceNorm2d(in_channels // 4),
            nn.LeakyReLU(inplace=True),
        )
        self.fc = nn.Linear(in_channels // 4 * 4 * 4, self.num_points * 2)
        nn.init.zeros_(self.fc.weight)
        self.fc.bias.data.copy_(self.target_control_points.reshape(-1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        xs = self.localization(x)
        xs = xs.view(x.size(0), -1)
        points = self.fc(xs)
        return points.view(-1, self.num_points, 2)


class TPSWarper(nn.Module):
    def __init__(self, grid_size: int, span_range: float, image_size: int, num_levels: int = 4) -> None:
        super().__init__()
        r = span_range
        target_control_points = torch.Tensor(list(itertools.product(
            np.arange(-r, r + 1e-5, 2.0 * r / (grid_size - 1)),
            np.arange(-r, r + 1e-5, 2.0 * r / (grid_size - 1)),
        )))
        Y, X = target_control_points.split(1, dim=1)
        target_control_points = torch.cat([X, Y], dim=1)

        self.tps_generators = nn.ModuleDict()
        for level in range(num_levels):
            h = image_size // (2 ** level)
            w = image_size // (2 ** level)
            self.tps_generators[f"{h}x{w}"] = TPSGridGen(h, w, target_control_points)

    def forward(self, feat: torch.Tensor, source_control_points: torch.Tensor) -> torch.Tensor:
        h, w = feat.shape[-2:]
        key = f"{h}x{w}"
        if key not in self.tps_generators:
            return feat
        source_coordinate = self.tps_generators[key](source_control_points)
        grid = source_coordinate.view(feat.size(0), h, w, 2)
        return F.grid_sample(feat, grid, mode="bilinear", padding_mode="border", align_corners=True)
