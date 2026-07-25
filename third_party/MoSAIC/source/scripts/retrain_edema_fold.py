#!/usr/bin/env python3
"""Retrain EdemaNet for a single fold (or full data). Designed for parallel launch."""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent


def validate_edema(model, val_records, cache_dir, coarse_pred_dir, device, dim=192):
    from myops.data.edema_dataset import EdemaSliceDataset
    model.eval()
    dataset = EdemaSliceDataset(val_records, cache_dir, coarse_pred_dir, "val", dim=dim)
    case_results = {}
    with torch.no_grad():
        for i in range(len(dataset)):
            sample = dataset[i]
            lge = sample["lge"][None].to(device)
            c0 = sample["c0"][None].to(device)
            t2 = sample["t2"][None].to(device)
            mask = sample["cardiac_mask"][None].to(device)
            preds = [model(lge, c0, t2, mask)]
            preds.append(torch.flip(model(torch.flip(lge, [-1]), torch.flip(c0, [-1]),
                         torch.flip(t2, [-1]), torch.flip(mask, [-1])), [-1]))
            preds.append(torch.flip(model(torch.flip(lge, [-2]), torch.flip(c0, [-2]),
                         torch.flip(t2, [-2]), torch.flip(mask, [-2])), [-2]))
            avg_pred = torch.stack([p[0] if isinstance(p, tuple) else p for p in preds]).mean(0)
            pred_class = torch.argmax(avg_pred, dim=1).cpu().numpy()[0]
            gt_label = sample["label"].numpy()
            cid = sample["case_id"]
            if cid not in case_results:
                case_results[cid] = {"pred_e": [], "gt_e": []}
            case_results[cid]["pred_e"].append(pred_class == 2)
            case_results[cid]["gt_e"].append(gt_label == 2)
    dices = []
    for cid, res in case_results.items():
        p = np.concatenate(res["pred_e"])
        g = np.concatenate(res["gt_e"])
        i = int((p & g).sum())
        t = int(p.sum()) + int(g.sum())
        dices.append(float(2 * i / (t + 1e-8)) if t > 0 else (1.0 if i == 0 else 0.0))
    return float(np.mean(dices)) if dices else 0.0


def train_edema(fold, device_id):
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from myops.data.labels import TRACK_MYOPS, EDEMA_CENTERS
    from myops.data.splits import split_records_by_fold, filter_records
    from myops.utils.io import read_jsonl
    from myops.models.edema_net import EdemaNet
    from myops.data.edema_dataset import EdemaSliceDataset
    from myops.engine.edema_losses import EdemaLoss

    os.environ["CUDA_VISIBLE_DEVICES"] = str(device_id)
    device = torch.device("cuda")

    manifest = str(ROOT / "cache" / "manifest.jsonl")
    cache_dir = str(ROOT / "cache")
    all_records = filter_records(read_jsonl(manifest), TRACK_MYOPS)

    if fold >= 0:
        fold_dir = ROOT / "grid_output" / "5fold" / f"fold{fold}"
        train_records, val_records = split_records_by_fold(all_records, fold)
    else:
        fold_dir = ROOT / "full_train" / "myops" / "fold-1"
        train_records = all_records
        val_records = []

    coarse_pred_dir = str(fold_dir / "coarse_predictions")
    output_dir = fold_dir / "edema"
    output_dir.mkdir(parents=True, exist_ok=True)

    if (output_dir / "best.pt").exists():
        ckpt = torch.load(str(output_dir / "best.pt"), map_location="cpu", weights_only=False)
        if ckpt.get("epoch", 0) >= 190:
            print(f"Fold {fold}: already trained (epoch {ckpt['epoch']}), skipping")
            return

    train_edema = [r for r in train_records if r["center"] in EDEMA_CENTERS]
    val_edema = [r for r in val_records if r["center"] in EDEMA_CENTERS] if val_records else []
    has_val = len(val_edema) > 0
    print(f"Fold {fold}: {len(train_edema)} train, {len(val_edema)} val (edema centers)")

    model = EdemaNet(use_c0=True, deep_supervision=True).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
    loss_fn = EdemaLoss()

    train_dataset = EdemaSliceDataset(train_edema, cache_dir, coarse_pred_dir, "train", dim=192)
    sampler = WeightedRandomSampler(train_dataset.weights, len(train_dataset.weights), replacement=True)
    train_loader = DataLoader(train_dataset, batch_size=16, sampler=sampler,
                              num_workers=0, pin_memory=True, drop_last=True)

    best_edema_dice = -1.0
    best_epoch = 0
    epochs = 200

    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for batch in train_loader:
            lge = batch["lge"].to(device)
            c0 = batch["c0"].to(device)
            t2 = batch["t2"].to(device)
            mask = batch["cardiac_mask"].to(device)
            target = batch["label_onehot"].to(device)
            optimizer.zero_grad()
            output = model(lge, c0, t2, mask)
            if isinstance(output, tuple):
                pred, ds_outputs = output
                loss = loss_fn(pred, target)
                for w, ds_pred in zip([0.3, 0.15], ds_outputs):
                    loss = loss + w * loss_fn(ds_pred, target)
            else:
                loss = loss_fn(output, target)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))

        scheduler.step()
        mean_loss = float(np.mean(losses))

        val_str = ""
        if has_val and (epoch % 5 == 0 or epoch == epochs):
            edema_dice = validate_edema(model, val_edema, cache_dir, coarse_pred_dir, device)
            val_str = f"  val_edema={edema_dice:.4f}"
            if edema_dice > best_edema_dice:
                best_edema_dice = edema_dice
                best_epoch = epoch
                torch.save({"model_state": model.state_dict(), "epoch": epoch,
                             "edema_dice": edema_dice}, output_dir / "best.pt")
            torch.save({"model_state": model.state_dict(), "epoch": epoch,
                         "edema_dice": edema_dice}, output_dir / "last.pt")

        if not has_val:
            if mean_loss < best_edema_dice or best_edema_dice < 0:
                best_edema_dice = mean_loss
                best_epoch = epoch
                torch.save({"model_state": model.state_dict(), "epoch": epoch},
                           output_dir / "best.pt")
            torch.save({"model_state": model.state_dict(), "epoch": epoch},
                       output_dir / "last.pt")

        lr = optimizer.param_groups[0]["lr"]
        if epoch % 10 == 0 or epoch == epochs:
            print(f"  [fold{fold}] Epoch {epoch}/{epochs}  loss={mean_loss:.4f}  lr={lr:.6f}{val_str}")

    print(f"  [fold{fold}] Done. Best edema_dice={best_edema_dice:.4f} at epoch {best_epoch}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()
    train_edema(args.fold, args.gpu)
