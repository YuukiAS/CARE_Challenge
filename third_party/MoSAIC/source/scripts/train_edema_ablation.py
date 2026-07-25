#!/usr/bin/env python3
"""Train one EdemaNet ablation variant on one fold.

Mirrors 5fold_train_all.train_edema_net exactly, but exposes the two design
choices the paper claims matter:

    --no-c0     drop the bSSFP reference stream (E1)
    --no-zone   regress edema-excluding-scar instead of the edema zone (E2)

The reported main model is the default: use_c0=True, zone=True.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from myops.data.dataset import EdemaSliceDataset
from myops.data.labels import EDEMA_CENTERS, TRACK_MYOPS
from myops.data.splits import filter_records, split_records_by_fold
from myops.engine.edema_losses import EdemaLoss
from myops.models.edema_net import EdemaNet
from myops.utils.io import read_jsonl

ROOT = Path(__file__).resolve().parent.parent
EPOCHS = 200


def validate(model, val_records, cache_dir, coarse_dir, device, dim, zone):
    """Case-level Dice of the positive class, TTA-averaged (as in the main run)."""
    model.eval()
    dataset = EdemaSliceDataset(val_records, cache_dir, coarse_dir, "val", dim=dim, zone=zone)
    per_case: dict[str, dict[str, list]] = {}

    with torch.no_grad():
        for i in range(len(dataset)):
            s = dataset[i]
            lge, c0 = s["lge"][None].to(device), s["c0"][None].to(device)
            t2, mask = s["t2"][None].to(device), s["cardiac_mask"][None].to(device)
            preds = [model(lge, c0, t2, mask)]
            preds.append(torch.flip(model(torch.flip(lge, [-1]), torch.flip(c0, [-1]),
                                          torch.flip(t2, [-1]), torch.flip(mask, [-1])), [-1]))
            preds.append(torch.flip(model(torch.flip(lge, [-2]), torch.flip(c0, [-2]),
                                          torch.flip(t2, [-2]), torch.flip(mask, [-2])), [-2]))
            avg = torch.stack([p[0] if isinstance(p, tuple) else p for p in preds]).mean(0)
            pred_class = torch.argmax(avg, dim=1).cpu().numpy()[0]
            bucket = per_case.setdefault(s["case_id"], {"p": [], "g": []})
            bucket["p"].append(pred_class == 2)
            bucket["g"].append(s["label"].numpy() == 2)

    dices = []
    for res in per_case.values():
        p, g = np.concatenate(res["p"]), np.concatenate(res["g"])
        inter, total = int((p & g).sum()), int(p.sum()) + int(g.sum())
        dices.append(float(2 * inter / (total + 1e-8)) if total > 0 else (1.0 if inter == 0 else 0.0))
    model.train()
    return float(np.mean(dices)) if dices else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--output-dir", type=str, required=True)
    ap.add_argument("--coarse-pred-dir", type=str, required=True)
    ap.add_argument("--cache-dir", type=str, default=str(ROOT / "cache"))
    ap.add_argument("--manifest", type=str, default=str(ROOT / "cache" / "manifest.jsonl"))
    ap.add_argument("--dim", type=int, default=192)
    ap.add_argument("--no-c0", action="store_true", help="E1: drop the bSSFP reference stream")
    ap.add_argument("--no-zone", action="store_true", help="E2: predict edema directly, not the zone")
    args = ap.parse_args()

    use_c0, zone = not args.no_c0, not args.no_zone
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = filter_records(read_jsonl(args.manifest), TRACK_MYOPS)
    train_recs, val_recs = split_records_by_fold(records, args.fold)
    train_recs = [r for r in train_recs if r["center"] in EDEMA_CENTERS]
    val_recs = [r for r in val_recs if r["center"] in EDEMA_CENTERS]
    print(f"  fold {args.fold}: {len(train_recs)} train / {len(val_recs)} val "
          f"(use_c0={use_c0}, zone={zone})")

    model = EdemaNet(use_c0=use_c0, deep_supervision=True).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
    loss_fn = EdemaLoss()

    train_ds = EdemaSliceDataset(train_recs, args.cache_dir, args.coarse_pred_dir,
                                 "train", dim=args.dim, zone=zone)
    sampler = WeightedRandomSampler(train_ds.weights, len(train_ds.weights), replacement=True)
    loader = DataLoader(train_ds, batch_size=16, sampler=sampler, num_workers=0,
                        pin_memory=True, drop_last=True)

    best_dice, best_epoch, history = -1.0, 0, []
    for epoch in range(1, EPOCHS + 1):
        model.train()
        losses = []
        for batch in loader:
            lge, c0 = batch["lge"].to(device), batch["c0"].to(device)
            t2, mask = batch["t2"].to(device), batch["cardiac_mask"].to(device)
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
        if epoch % 5 == 0 or epoch == EPOCHS:
            dice = validate(model, val_recs, args.cache_dir, args.coarse_pred_dir,
                            device, args.dim, zone)
            history.append({"epoch": epoch, "loss": mean_loss, "val_dice": dice})
            if dice > best_dice:
                best_dice, best_epoch = dice, epoch
                torch.save({"model_state": model.state_dict(), "epoch": epoch,
                            "edema_dice": dice, "use_c0": use_c0, "zone": zone},
                           out_dir / "best.pt")
            torch.save({"model_state": model.state_dict(), "epoch": epoch,
                        "edema_dice": dice, "use_c0": use_c0, "zone": zone},
                       out_dir / "last.pt")
            if epoch % 20 == 0 or epoch == EPOCHS:
                print(f"  epoch {epoch}/{EPOCHS}  loss={mean_loss:.4f}  val_dice={dice:.4f}")

    result = {
        "fold": args.fold, "use_c0": use_c0, "zone": zone,
        "best_val_dice": best_dice, "best_epoch": best_epoch, "history": history,
    }
    (out_dir / "experiment_result.json").write_text(json.dumps(result, indent=2))
    print(f"  done: best val dice={best_dice:.4f} @ epoch {best_epoch}")


if __name__ == "__main__":
    main()
