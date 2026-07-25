#!/usr/bin/env python3
"""5-fold cross-validation training for MyoPS + CineMyoPS.

Best configs:
- MyoPS: C10 coarse + F01 scar fine + dedicated EdemaNet
- CineMyoPS: CC12 coarse + CF06 fine V2 (z-spacing aug)

Usage:
    CUDA_VISIBLE_DEVICES=0 python scripts/5fold_train_all.py --data-dir /path/to/Myo_train --tracks myops --gpu 0
    CUDA_VISIBLE_DEVICES=1 python scripts/5fold_train_all.py --data-dir /path/to/Myo_train --tracks cine --gpu 1

    # Full-data training (no val split)
    python scripts/5fold_train_all.py --data-dir /path/to/Myo_train --mode full --tracks myops cine --gpu 0
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
WORKER = ROOT / "scripts" / "train_single_experiment.py"


def run_worker(config_path: str, stage: str, fold: int, data_dir: str,
               output_dir: str, cache_dir: str, track: str,
               manifest: str | None = None, coarse_pred_dir: str | None = None,
               gpu_id: int = 0, skip_preprocess: bool = False,
               z_spacing_aug: bool = False) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, str(WORKER),
        "--config", config_path,
        "--stage", stage,
        "--fold", str(fold),
        "--data-dir", data_dir,
        "--output-dir", output_dir,
        "--cache-dir", cache_dir,
        "--track", track,
    ]
    if skip_preprocess:
        cmd.append("--skip-preprocess")
    if manifest:
        cmd.extend(["--manifest", manifest])
    if coarse_pred_dir:
        cmd.extend(["--coarse-pred-dir", coarse_pred_dir])
    if z_spacing_aug:
        cmd.append("--z-spacing-aug")

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    print(f"\n{'='*60}")
    print(f"  {track} {stage} fold={fold} on GPU {gpu_id}")
    print(f"  output: {output_dir}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, env=env, capture_output=False)
    return result


def build_myops_coarse_config(output_dir: Path) -> str:
    """C10: base + lr=1e-3, cosine scheduler."""
    import yaml
    base_path = ROOT / "configs" / "myops_coarse.yaml"
    with open(base_path) as f:
        cfg = yaml.safe_load(f)
    cfg["training"]["learning_rate"] = 1e-3
    cfg["training"]["scheduler"] = {"type": "cosine", "min_lr": 1e-6}
    config_path = output_dir / "c10_coarse_config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return str(config_path)


def build_myops_fine_config(output_dir: Path) -> str:
    """F01: base myops_fine.yaml, no overrides."""
    return str(ROOT / "configs" / "myops_fine.yaml")


def build_cine_coarse_config(output_dir: Path) -> str:
    """CC12: base + lr=1e-3, cosine, 80 epochs."""
    import yaml
    base_path = ROOT / "configs" / "cine_coarse.yaml"
    with open(base_path) as f:
        cfg = yaml.safe_load(f)
    cfg["training"]["learning_rate"] = 1e-3
    cfg["training"]["max_epochs"] = 80
    cfg["training"]["scheduler"] = {"type": "cosine", "min_lr": 1e-6}
    config_path = output_dir / "cc12_coarse_config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return str(config_path)


def build_cine_fine_config(output_dir: Path) -> str:
    """CF06: base + class_weights=[1,1,5], 150 epochs."""
    import yaml
    base_path = ROOT / "configs" / "cine_fine.yaml"
    with open(base_path) as f:
        cfg = yaml.safe_load(f)
    cfg["loss"]["class_weights"] = [1.0, 1.0, 5.0]
    cfg["training"]["max_epochs"] = 150
    config_path = output_dir / "cf06_fine_config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return str(config_path)


def generate_coarse_predictions(coarse_ckpt: str, all_records: list, cache_root: str,
                                 output_dir: str, track: str, device_id: int = 0):
    import torch

    os.environ["CUDA_VISIBLE_DEVICES"] = str(device_id)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    from myops.config import load_config
    from myops.data.labels import num_classes, modalities_for_track, TRACK_MYOPS, TRACK_CINE
    from myops.data.preprocessing import cache_path
    from myops.inference.predict import predict_case_coarse
    from myops.models import build_model
    from myops.utils.io import torch_load, torch_save

    track_const = TRACK_CINE if track == "cinemyops" else TRACK_MYOPS
    n_mod = len(modalities_for_track(track_const))

    if track == "cinemyops":
        config_path = str(ROOT / "configs" / "cine_coarse.yaml")
    else:
        config_path = str(ROOT / "configs" / "myops_coarse.yaml")
    cfg = load_config(config_path)
    base_ch = int(cfg["model"].get("base_channels", 24))

    model = build_model(
        stage="coarse", track=track_const, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(track_const, "coarse"),
        base_channels=base_ch, deep_supervision=True,
    )
    ckpt = torch.load(coarse_ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    model = model.to(device).eval()

    TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}
    pred_dir = Path(output_dir)
    pred_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for rec in all_records:
        dest = pred_dir / track_const / f'{rec["case_id"]}.pt'
        if dest.exists():
            count += 1
            continue
        payload = torch_load(cache_path(cache_root, track_const, rec["case_id"]))
        with torch.no_grad():
            result = predict_case_coarse(model, payload, track_const, device,
                                          image_size=[192, 192], tta_config=TTA)
        torch_save(result, dest)
        count += 1
        if count % 20 == 0:
            print(f"    Coarse predictions: {count}/{len(all_records)}")

    print(f"    Coarse predictions done: {count}/{len(all_records)}")
    del model
    torch.cuda.empty_cache()


def _validate_edema(model, val_records, cache_dir, coarse_pred_dir, device, dim=192):
    """Validate EdemaNet on val set, return mean edema dice (argmax-based)."""
    import torch
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


def train_edema_net(train_records: list, val_records: list,
                    cache_dir: str, coarse_pred_dir: str,
                    output_dir: Path, device_id: int = 0):
    """Train dedicated EdemaNet on CenterB+C records with validation-based selection."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    os.environ["CUDA_VISIBLE_DEVICES"] = str(device_id)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    from myops.data.labels import EDEMA_CENTERS
    from myops.models.edema_net import EdemaNet
    from myops.data.edema_dataset import EdemaSliceDataset
    from myops.engine.edema_losses import EdemaLoss

    train_edema = [r for r in train_records if r["center"] in EDEMA_CENTERS]
    val_edema = [r for r in val_records if r["center"] in EDEMA_CENTERS] if val_records else []
    has_val = len(val_edema) > 0
    print(f"  EdemaNet: {len(train_edema)} train, {len(val_edema)} val (edema centers)")

    model = EdemaNet(use_c0=True, deep_supervision=True).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
    loss_fn = EdemaLoss()

    train_dataset = EdemaSliceDataset(
        train_edema, cache_dir, coarse_pred_dir, "train", dim=192,
    )
    sampler = WeightedRandomSampler(train_dataset.weights, len(train_dataset.weights), replacement=True)
    train_loader = DataLoader(train_dataset, batch_size=16, sampler=sampler,
                              num_workers=0, pin_memory=True, drop_last=True)

    output_dir.mkdir(parents=True, exist_ok=True)
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
                pred = output
                loss = loss_fn(pred, target)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))

        scheduler.step()
        mean_loss = float(np.mean(losses))

        val_str = ""
        if has_val and (epoch % 5 == 0 or epoch == epochs):
            edema_dice = _validate_edema(
                model, val_edema, cache_dir, coarse_pred_dir, device, dim=192)
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
            print(f"  Epoch {epoch}/{epochs}  loss={mean_loss:.4f}  lr={lr:.6f}{val_str}")

    print(f"  EdemaNet done. Best edema_dice={best_edema_dice:.4f} at epoch {best_epoch}")
    del model
    torch.cuda.empty_cache()
    return output_dir / "best.pt"


def train_fold_myops(fold: int, data_dir: str, cache_dir: str, output_base: str,
                     manifest: str, gpu_id: int = 0):
    """Train all 3 MyoPS models for one fold: coarse + scar fine + EdemaNet."""
    fold_dir = Path(output_base) / (f"fold{fold}" if fold >= 0 else "fold-1")

    # 1. Coarse (C10)
    coarse_dir = fold_dir / "coarse"
    coarse_config = build_myops_coarse_config(fold_dir)
    myops_cached = Path(cache_dir, "myops").exists()
    if not (coarse_dir / "experiment_result.json").exists():
        run_worker(coarse_config, "coarse", fold, data_dir, str(coarse_dir),
                   cache_dir, "myops", manifest, gpu_id=gpu_id,
                   skip_preprocess=myops_cached)

    # 2. Generate coarse predictions for all records
    coarse_ckpt = str(coarse_dir / "best.pt")
    if not Path(coarse_ckpt).exists():
        coarse_ckpt = str(coarse_dir / "last.pt")
    if not Path(coarse_ckpt).exists():
        raise RuntimeError(f"MyoPS coarse training failed: no checkpoint at {coarse_dir}")
    coarse_pred_dir = str(fold_dir / "coarse_predictions")

    from myops.data.labels import TRACK_MYOPS
    from myops.data.splits import filter_records, split_records_by_fold
    from myops.utils.io import read_jsonl
    all_records = filter_records(read_jsonl(manifest), TRACK_MYOPS)
    generate_coarse_predictions(coarse_ckpt, all_records, cache_dir, coarse_pred_dir,
                                "myops", gpu_id)

    # 3. Scar fine (F01)
    fine_dir = fold_dir / "fine"
    fine_config = build_myops_fine_config(fold_dir)
    if not (fine_dir / "experiment_result.json").exists():
        run_worker(fine_config, "fine", fold, data_dir, str(fine_dir),
                   cache_dir, "myops", manifest, coarse_pred_dir, gpu_id,
                   skip_preprocess=True)

    # 4. Dedicated EdemaNet (custom training loop, NOT channel-swapped FinePathNet)
    edema_dir = fold_dir / "edema"
    if not (edema_dir / "last.pt").exists():
        print(f"\n{'='*60}")
        print(f"  myops EdemaNet fold={fold} on GPU {gpu_id}")
        print(f"  output: {edema_dir}")
        print(f"{'='*60}")

        train_records, val_records = split_records_by_fold(all_records, fold)
        train_edema_net(train_records, val_records, cache_dir, coarse_pred_dir, edema_dir, gpu_id)

    print(f"\n  MyoPS fold {fold}: ALL 3 MODELS COMPLETE (coarse + scar + edema)")


def train_fold_cine(fold: int, data_dir: str, cache_dir: str, output_base: str,
                    manifest: str, gpu_id: int = 0):
    """Train CineMyoPS coarse + fine V2 for one fold."""
    fold_dir = Path(output_base) / (f"fold{fold}" if fold >= 0 else "fold-1")

    # 1. Coarse (CC12)
    coarse_dir = fold_dir / "coarse"
    coarse_config = build_cine_coarse_config(fold_dir)
    if not (coarse_dir / "experiment_result.json").exists():
        run_worker(coarse_config, "coarse", fold, data_dir, str(coarse_dir),
                   cache_dir, "cinemyops", manifest, gpu_id=gpu_id,
                   skip_preprocess=False)

    # 2. Generate coarse predictions
    coarse_ckpt = str(coarse_dir / "best.pt")
    if not Path(coarse_ckpt).exists():
        coarse_ckpt = str(coarse_dir / "last.pt")
    if not Path(coarse_ckpt).exists():
        raise RuntimeError(f"CineMyoPS coarse training failed: no checkpoint at {coarse_dir}")
    coarse_pred_dir = str(fold_dir / "coarse_predictions")

    from myops.data.labels import TRACK_CINE
    from myops.data.splits import filter_records
    from myops.utils.io import read_jsonl
    all_records = filter_records(read_jsonl(manifest), TRACK_CINE)
    generate_coarse_predictions(coarse_ckpt, all_records, cache_dir, coarse_pred_dir,
                                "cinemyops", gpu_id)

    # 3. Fine V2 (CF06 + z-spacing augmentation)
    fine_config = build_cine_fine_config(fold_dir)
    fine_v2_dir = fold_dir / "fine_v2"
    if not (fine_v2_dir / "experiment_result.json").exists():
        run_worker(fine_config, "fine", fold, data_dir, str(fine_v2_dir),
                   cache_dir, "cinemyops", manifest, coarse_pred_dir, gpu_id,
                   skip_preprocess=True, z_spacing_aug=True)

    print(f"\n  CineMyoPS fold {fold}: ALL MODELS COMPLETE (coarse + fine_v2)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, required=True, help="Path to Myo_train data directory")
    parser.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--tracks", type=str, nargs="+", default=["myops", "cine"],
                        choices=["myops", "cine"])
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--mode", type=str, default="cv", choices=["cv", "full"])
    args = parser.parse_args()

    cache_dir = str(ROOT / "cache")
    myops_manifest = str(ROOT / "cache" / "manifest.jsonl")
    cine_manifest = str(ROOT / "cache" / "cine_manifest.jsonl")

    if "myops" in args.tracks and not Path(myops_manifest).exists():
        from myops.data.manifest import build_myops_manifest, assign_folds
        from myops.utils.io import write_jsonl
        print("Building MyoPS manifest...")
        myops_records = build_myops_manifest(Path(args.data_dir))
        myops_records = assign_folds(myops_records, num_folds=5, seed=42)
        Path(myops_manifest).parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(myops_records, myops_manifest)
        print(f"  Wrote {len(myops_records)} MyoPS records")

    if "cine" in args.tracks and not Path(cine_manifest).exists():
        from myops.data.manifest import build_cine_manifest, assign_folds
        from myops.utils.io import write_jsonl
        print("Building CineMyoPS manifest...")
        cine_records = build_cine_manifest(Path(args.data_dir))
        cine_records = assign_folds(cine_records, num_folds=5, seed=42)
        Path(cine_manifest).parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(cine_records, cine_manifest)
        print(f"  Wrote {len(cine_records)} CineMyoPS records")

    if args.mode == "full":
        args.folds = [-1]

    if args.mode == "cv":
        myops_base = str(ROOT / "grid_output" / "5fold")
        cine_base = str(ROOT / "grid_output_cine" / "5fold")
    else:
        myops_base = str(ROOT / "full_train" / "myops")
        cine_base = str(ROOT / "full_train" / "cine")

    for fold in args.folds:
        fold_label = "full" if fold == -1 else f"fold{fold}"
        print(f"\n{'#'*70}")
        print(f"  TRAINING {fold_label}")
        print(f"{'#'*70}")

        if "myops" in args.tracks:
            t0 = time.time()
            train_fold_myops(fold, args.data_dir, cache_dir, myops_base, myops_manifest, args.gpu)
            print(f"  MyoPS {fold_label}: {(time.time()-t0)/3600:.1f}h")

        if "cine" in args.tracks:
            t0 = time.time()
            train_fold_cine(fold, args.data_dir, cache_dir, cine_base, cine_manifest, args.gpu)
            print(f"  CineMyoPS {fold_label}: {(time.time()-t0)/3600:.1f}h")

    print(f"\n{'#'*70}")
    print(f"  ALL TRAINING COMPLETE")
    print(f"{'#'*70}")


if __name__ == "__main__":
    main()
