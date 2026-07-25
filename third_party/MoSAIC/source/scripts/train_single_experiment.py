#!/usr/bin/env python3
"""Worker script: trains a single experiment (coarse or fine stage) with a given config.

Used by grid_search.py but also works standalone:
    python scripts/train_single_experiment.py \
        --config configs/myops_coarse.yaml --stage coarse --fold 0 \
        --data-dir /path/to/data --output-dir /path/to/exp_output
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from myops.config import load_config, save_config
from myops.data.dataset import CoarseSliceDataset, FineSliceDataset
from myops.data.labels import TRACK_MYOPS, TRACK_CINE, num_classes, modalities_for_track
from myops.data.manifest import build_myops_manifest, build_cine_manifest, assign_folds
from myops.data.preprocessing import preprocess_myops_case, preprocess_cine_case, cache_path
from myops.data.splits import split_records_by_fold, filter_records
from myops.engine.trainer import SegmentationTrainer
from myops.inference.predict import predict_case_coarse, predict_case_fine, evaluate_predictions
from myops.models import build_model
from myops.utils.io import write_jsonl, read_jsonl, torch_save, torch_load


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a single MyoPS experiment.")
    p.add_argument("--config", type=str, required=True, help="YAML config file path")
    p.add_argument("--stage", type=str, required=True, choices=["coarse", "fine"])
    p.add_argument("--fold", type=int, default=0)
    p.add_argument("--num-folds", type=int, default=5)
    p.add_argument("--data-dir", type=str, required=True, help="Root dir containing MyoPS_train/")
    p.add_argument("--output-dir", type=str, required=True, help="Experiment output directory")
    p.add_argument("--cache-dir", type=str, default=None, help="Shared preprocessing cache")
    p.add_argument("--manifest", type=str, default=None, help="Pre-built manifest JSONL")
    p.add_argument("--coarse-pred-dir", type=str, default=None, help="Coarse predictions dir (fine stage)")
    p.add_argument("--track", type=str, default="myops", choices=["myops", "cinemyops"])
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--skip-preprocess", action="store_true")
    p.add_argument("--z-spacing-aug", action="store_true", help="Enable Z-spacing augmentation for CineMyoPS fine training")
    return p.parse_args()


def ensure_manifest(data_dir: Path, manifest_path: Path, num_folds: int, track: str = TRACK_MYOPS) -> list[dict]:
    if manifest_path.exists():
        return read_jsonl(str(manifest_path))
    print("  Building manifest...")
    if track == TRACK_CINE:
        records = build_cine_manifest(data_dir)
    else:
        records = build_myops_manifest(data_dir)
    records = assign_folds(records, num_folds=num_folds, seed=42)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(records, str(manifest_path))
    print(f"  Wrote {len(records)} records")
    return records


def ensure_preprocessed(records: list[dict], cache_dir: Path, config: dict, track: str = TRACK_MYOPS) -> None:
    total = len(records)
    done = 0
    for i, rec in enumerate(records):
        dest = cache_path(str(cache_dir), track, rec["case_id"])
        if dest.exists():
            done += 1
            continue
        print(f"  Preprocessing {rec['case_id']} ({i+1}/{total})")
        if track == TRACK_CINE:
            spacing = config["data"].get("cine_target_spacing", [1.25, 1.25, 8.0])
            preprocess_cine_case(rec, str(cache_dir), spacing, temporal_config=config.get("data"))
        else:
            spacing = config["data"].get("myops_target_spacing", [1.25, 1.25, 10.0])
            reg_cfg = config["data"].get("registration")
            preprocess_myops_case(rec, str(cache_dir), spacing, registration_config=reg_cfg)
        done += 1
    print(f"  Cache ready: {done}/{total} cases in {cache_dir}")


def build_coarse_model(config: dict, track: str = TRACK_MYOPS):
    image_size = config["data"].get("image_size", [192, 192])
    base_ch = int(config["model"].get("base_channels", 24))
    n_mod = len(modalities_for_track(track))
    in_ch = n_mod * 2
    out_ch = num_classes(track, "coarse")
    model = build_model(
        stage="coarse", track=track, arch="2d_coarse",
        in_channels=in_ch, out_channels=out_ch, base_channels=base_ch,
        deep_supervision=bool(config["model"].get("deep_supervision", True)),
    )
    return model, image_size


def build_fine_model(config: dict, track: str = TRACK_MYOPS):
    image_size = config["data"].get("image_size", [192, 192])
    base_ch = int(config["model"].get("base_channels", 24))
    arch = config["model"].get("arch", "2d_multi")

    if track == TRACK_CINE and arch == "cine_hybrid":
        num_frames = int(config["model"].get("num_frames", config["data"].get("max_cine_frames", 20)))
        out_ch = num_classes(track, "fine")
        model = build_model(
            stage="fine", track=track, arch="cine_hybrid",
            in_channels=num_frames + 1, out_channels=out_ch,
            base_channels=base_ch, deep_supervision=False,
            num_frames=num_frames,
            max_displacement=float(config["model"].get("max_displacement", 0.25)),
            pathology_input=str(config["model"].get("pathology_input", "flow")),
        )
    else:
        n_mod = len(modalities_for_track(track))
        in_ch = n_mod * 2 + 1
        out_ch = num_classes(track, "fine")
        model = build_model(
            stage="fine", track=track, arch=arch,
            in_channels=in_ch, out_channels=out_ch, base_channels=base_ch,
            deep_supervision=bool(config["model"].get("deep_supervision", True)),
            grid_size=int(config["model"].get("grid_size", 4)),
            span_range=float(config["model"].get("span_range", 0.98)),
            image_size=int(image_size[0]),
            use_tps=bool(config["model"].get("use_tps", True)),
            use_spg=bool(config["model"].get("use_spg", True)),
            use_consistency=bool(config["model"].get("use_consistency", True)),
        )
    return model, image_size


def train_coarse(config, train_records, val_records, cache_dir, output_dir, device, fold, track=TRACK_MYOPS):
    model, image_size = build_coarse_model(config, track)
    print(f"  CoarseNet params: {sum(p.numel() for p in model.parameters()):,}")

    dataset = CoarseSliceDataset(train_records, str(cache_dir), "train", image_size)
    print(f"  Train slices: {len(dataset)}")

    trainer = SegmentationTrainer(
        model=model, config=config, track=track, stage="coarse",
        arch="2d_coarse", fold=fold, train_dataset=dataset,
        val_records=val_records, cache_root=str(cache_dir),
        output_dir=str(output_dir), device=device,
    )
    return trainer.run()


def train_fine(config, train_records, val_records, cache_dir, output_dir, device, fold, coarse_pred_dir, track=TRACK_MYOPS, z_spacing_augment=False):
    arch = config["model"].get("arch", "2d_multi")
    is_cine_hybrid = (track == TRACK_CINE and arch == "cine_hybrid")

    model, image_size = build_fine_model(config, track)
    print(f"  {'CineHybridNet' if is_cine_hybrid else 'FinePathNet'} params: {sum(p.numel() for p in model.parameters()):,}")

    cine_frame_count = int(config["model"].get("num_frames", config["data"].get("max_cine_frames", 20))) if is_cine_hybrid else 20
    channel_order = config.get("data", {}).get("channel_order")
    edema_mode = bool(config.get("data", {}).get("edema_mode", False))
    dataset = FineSliceDataset(
        train_records, str(cache_dir), "train", image_size,
        coarse_prediction_root=str(coarse_pred_dir),
        crop_margin=config.get("data", {}).get("crop_margin", [1, 16, 16]),
        cine_hybrid=is_cine_hybrid,
        cine_frame_count=cine_frame_count,
        z_spacing_augment=z_spacing_augment,
        channel_order=channel_order,
        edema_mode=edema_mode,
        disable_coarse_prior=bool(config.get("data", {}).get("disable_coarse_prior", False)),
    )
    print(f"  Train slices: {len(dataset)}")

    trainer = SegmentationTrainer(
        model=model, config=config, track=track, stage="fine",
        arch=arch, fold=fold, train_dataset=dataset,
        val_records=val_records, cache_root=str(cache_dir),
        output_dir=str(output_dir), device=device,
        coarse_prediction_root=str(coarse_pred_dir),
    )
    return trainer.run()


def evaluate_with_tta(stage, config, val_records, cache_dir, run_dir, device, coarse_pred_dir=None, track=TRACK_MYOPS):
    """Load best checkpoint and evaluate with TTA for final metrics."""
    ckpt_path = run_dir / "best.pt"
    if not ckpt_path.exists():
        ckpt_path = run_dir / "last.pt"
    if not ckpt_path.exists():
        return {}

    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    image_size = config["data"].get("image_size", [192, 192])

    if stage == "coarse":
        model, _ = build_coarse_model(config, track)
    else:
        model, _ = build_fine_model(config, track)

    model.load_state_dict(ckpt["model_state"], strict=False)
    model = model.to(device).eval()

    tta_cfg = config.get("inference", {}).get("tta")
    thresholds = config.get("inference", {}).get("thresholds")
    if isinstance(thresholds, dict):
        if track == TRACK_CINE:
            thresholds = [thresholds.get(k, 0.5) for k in ["myo", "lv", "scar"]]
        else:
            thresholds = [thresholds.get(k, 0.5) for k in ["myo", "lv", "rv", "edema", "scar"]]

    arch = config["model"].get("arch", "2d_multi")
    is_cine_hybrid = (track == TRACK_CINE and arch == "cine_hybrid")
    cine_frame_count = int(config["model"].get("num_frames", config["data"].get("max_cine_frames", 20)))

    results = []
    for i, rec in enumerate(val_records):
        payload = torch_load(cache_path(str(cache_dir), track, rec["case_id"]))
        with torch.no_grad():
            if stage == "coarse":
                result = predict_case_coarse(model, payload, track, device, image_size=image_size)
            else:
                coarse_pt = torch_load(Path(coarse_pred_dir) / track / f"{rec['case_id']}.pt")
                coarse_prior = np.asarray(coarse_pt["label"], dtype=np.int16)
                result = predict_case_fine(
                    model, payload, track, device,
                    coarse_prior=coarse_prior, image_size=image_size,
                    thresholds=thresholds, tta_config=tta_cfg,
                    crop_margin=config.get("data", {}).get("crop_margin", [1, 16, 16]),
                    use_cine_sequence=is_cine_hybrid,
                    cine_frame_count=cine_frame_count,
                    pathology_dilation_iterations=int(config.get("postprocess", {}).get("pathology_dilation_iterations", 1)),
                    channel_order=config.get("data", {}).get("channel_order"),
                    disable_coarse_prior=bool(config.get("data", {}).get("disable_coarse_prior", False)),
                )
        results.append(result)
        if (i + 1) % 10 == 0:
            print(f"  Evaluated {i+1}/{len(val_records)} cases")

    metrics = evaluate_predictions(track, stage, results, str(cache_dir))
    del model
    torch.cuda.empty_cache()
    return metrics


def main() -> None:
    args = parse_args()
    track = TRACK_CINE if args.track == "cinemyops" else TRACK_MYOPS
    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    cache_dir = Path(args.cache_dir).resolve() if args.cache_dir else output_dir.parent / "cache"
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    save_config(config, output_dir / "config.yaml")

    manifest_path = Path(args.manifest) if args.manifest else output_dir.parent / "manifest.jsonl"
    records = ensure_manifest(data_dir, manifest_path, args.num_folds, track)
    records = filter_records(records, track)

    if not args.skip_preprocess:
        ensure_preprocessed(records, cache_dir, config, track)

    train_records, val_records = split_records_by_fold(records, args.fold)
    print(f"  Fold {args.fold}: {len(train_records)} train, {len(val_records)} val")

    t0 = time.time()

    if args.stage == "coarse":
        summary = train_coarse(config, train_records, val_records, cache_dir, output_dir, device, args.fold, track)
    else:
        if not args.coarse_pred_dir:
            print("ERROR: --coarse-pred-dir required for fine stage", file=sys.stderr)
            sys.exit(1)
        summary = train_fine(config, train_records, val_records, cache_dir, output_dir, device, args.fold, args.coarse_pred_dir, track, z_spacing_augment=args.z_spacing_aug)

    elapsed_train = time.time() - t0
    print(f"  Training done in {elapsed_train/3600:.1f}h. Best epoch: {summary.get('best_epoch')}")

    print("  Running final evaluation with TTA...")
    final_metrics = evaluate_with_tta(
        args.stage, config, val_records, cache_dir, output_dir, device,
        coarse_pred_dir=args.coarse_pred_dir, track=track,
    )

    elapsed_total = time.time() - t0
    result = {
        "experiment": output_dir.name,
        "stage": args.stage,
        "fold": args.fold,
        "config_path": args.config,
        "training_summary": summary,
        "final_metrics": {k: float(v) for k, v in final_metrics.items()},
        "elapsed_train_seconds": elapsed_train,
        "elapsed_total_seconds": elapsed_total,
    }
    result_path = output_dir / "experiment_result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n  Results for {output_dir.name}:")
    for k, v in sorted(final_metrics.items()):
        if "dice" in k:
            print(f"    {k:30s}: {v:.4f}")
    print(f"  Saved to {result_path}")


if __name__ == "__main__":
    main()
