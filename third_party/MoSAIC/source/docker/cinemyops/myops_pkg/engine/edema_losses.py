import torch
import torch.nn as nn
import numpy as np


class BinaryDiceLoss(nn.Module):
    def forward(self, predict, target):
        predict = predict.contiguous().view(predict.shape[0], -1)
        target = target.contiguous().view(target.shape[0], -1)
        num = (predict * target).sum(1)
        den = predict.sum(1) + target.sum(1)
        loss = 1 - (2 * num + 1e-10) / (den + 1e-10)
        return loss.mean()


class DiceLoss(nn.Module):
    def forward(self, predict, target):
        dice = BinaryDiceLoss()
        total_loss = 0
        for i in range(target.shape[1]):
            total_loss += dice(predict[:, i], target[:, i])
        return total_loss / target.shape[1]


class WCELoss(nn.Module):
    def weight_function(self, target):
        mask = torch.argmax(target, dim=1)
        voxels_sum = mask.shape[0] * mask.shape[1] * mask.shape[2]
        weights = []
        for i in range(int(mask.max()) + 1):
            voxels_i = (mask == i).sum().float().clamp_min(1)
            w_i = torch.log(voxels_sum / voxels_i)
            weights.append(w_i)
        return torch.stack(weights).to(target.device)

    def forward(self, predict, target):
        ce_loss = torch.mean(-target * torch.log(predict + 1e-10), dim=(0, 2, 3))
        weights = self.weight_function(target)
        n = min(len(weights), len(ce_loss))
        loss = weights[:n] * ce_loss[:n]
        return loss.sum()


class EdemaLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.dice_loss = DiceLoss()
        self.wce_loss = WCELoss()

    def forward(self, predict, target):
        return self.dice_loss(predict, target) + self.wce_loss(predict, target)
