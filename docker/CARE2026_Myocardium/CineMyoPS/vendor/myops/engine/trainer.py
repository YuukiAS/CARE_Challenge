from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader, WeightedRandomSampler

from myops.data.sampling import ClassQuotaBatchSampler
from myops.engine.losses import StageLoss
from myops.inference.predict import (
    evaluate_predictions,
    predict_case_coarse,
    predict_case_fine,
    predict_records_coarse,
)


def _build_loader(
    dataset, batch_size: int, num_workers: int,
    weighted_sampling: bool, sampling_cfg: dict[str, Any] | None = None,
) -> DataLoader:
    sampling_cfg = sampling_cfg or {}
    fine_quota = sampling_cfg.get("fine_class_quota")
    if fine_quota and getattr(dataset, "sample_groups", None):
        batch_sampler = ClassQuotaBatchSampler(
            dataset.sample_groups, batch_size=batch_size, quotas=fine_quota,
            seed=int(sampling_cfg.get("seed", 3407)),
        )
        return DataLoader(dataset, batch_sampler=batch_sampler, num_workers=num_workers, pin_memory=True)
    sampler = None
    shuffle = False
    if weighted_sampling and getattr(dataset, "sample_weights", None):
        weights = torch.as_tensor(dataset.sample_weights, dtype=torch.double)
        sampler = WeightedRandomSampler(weights=weights, num_samples=len(weights), replacement=True)
    else:
        shuffle = True
    return DataLoader(
        dataset, batch_size=batch_size, shuffle=shuffle, sampler=sampler,
        num_workers=num_workers, pin_memory=True, drop_last=False,
    )


class SegmentationTrainer:
    def __init__(
        self, *, model: torch.nn.Module, config: dict[str, Any],
        track: str, stage: str, arch: str, fold: int,
        train_dataset, val_records: list[dict[str, Any]],
        cache_root: str | Path, output_dir: str | Path,
        device: torch.device, coarse_prediction_root: str | Path | None = None,
        pretrained_checkpoint: str | Path | None = None,
    ) -> None:
        self.model = model.to(device)
        if pretrained_checkpoint is not None:
            ckpt = torch.load(str(pretrained_checkpoint), map_location="cpu", weights_only=False)
            state = ckpt.get("model_state", ckpt)
            missing, unexpected = self.model.load_state_dict(state, strict=False)
            print(f"  Transfer learning: loaded {len(state) - len(missing)} params, "
                  f"{len(missing)} missing, {len(unexpected)} unexpected")
        self.config = config
        self.track = track
        self.stage = stage
        self.arch = arch
        self.use_cine_sequence = bool(arch == "cine_hybrid")
        # model.num_frames wins: it fixes the architecture, so validation must use the
        # same T the network was built with. (Matches build_fine_model / eval_5fold.)
        self.cine_frame_count = int(config.get("model", {}).get("num_frames", config.get("data", {}).get("max_cine_frames", 20)))
        self.fold = int(fold)
        self.val_records = val_records
        self.cache_root = Path(cache_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = device
        self.coarse_prediction_root = Path(coarse_prediction_root) if coarse_prediction_root is not None else None
        self.channel_order = config.get("data", {}).get("channel_order")
        self.disable_coarse_prior = bool(config.get("data", {}).get("disable_coarse_prior", False))

        tcfg = config["training"]
        self.loader = _build_loader(
            train_dataset,
            batch_size=int(tcfg["batch_size"]),
            num_workers=int(tcfg.get("num_workers", 0)),
            weighted_sampling=bool(tcfg.get("weighted_sampling", True)),
            sampling_cfg=config.get("data", {}).get("sampling"),
        )
        loss_cfg = config.get("loss", {})
        self.loss_fn = StageLoss(
            track=track, stage=stage,
            class_weights=loss_cfg.get("class_weights"),
            deep_supervision_weights=loss_cfg.get("deep_supervision_weights"),
            pathology_tversky_weight=float(loss_cfg.get("pathology_tversky_weight", 0.0)),
            pathology_focal_weight=float(loss_cfg.get("pathology_focal_weight", 0.0)),
            pathology_tversky_alpha=float(loss_cfg.get("pathology_tversky_alpha", 0.7)),
            pathology_tversky_beta=float(loss_cfg.get("pathology_tversky_beta", 0.3)),
            pathology_focal_gamma=float(loss_cfg.get("pathology_focal_gamma", 2.0)),
            class_specific_pathology=loss_cfg.get("class_specific_pathology"),
            enabled_classes=loss_cfg.get("enabled_classes"),
            ignore_supervision_mask=bool(loss_cfg.get("ignore_supervision_mask", False)),
            consistency_weight=float(loss_cfg.get("consistency_weight", 0.0)),
            registration_weight=float(loss_cfg.get("registration_weight", 0.0)),
            inclusiveness_weight=float(loss_cfg.get("inclusiveness_weight", 0.0)),
            t2_aux_weight=float(loss_cfg.get("t2_aux_weight", 0.0)),
            edema_gaussian_dice_weight=float(loss_cfg.get("edema_gaussian_dice_weight", 0.0)),
            edema_gaussian_dice_sigma=float(loss_cfg.get("edema_gaussian_dice_sigma", 1.5)),
            cine_aux_weights=loss_cfg.get("cine_aux_weights"),
        )

        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=float(tcfg["learning_rate"]),
            weight_decay=float(tcfg.get("weight_decay", 1e-4)),
        )

        self.max_epochs = int(tcfg["max_epochs"])
        self.val_every = int(tcfg.get("val_every", 1))
        self.max_batches_per_epoch = int(tcfg.get("max_batches_per_epoch", 0))

        self.use_amp = bool(tcfg.get("use_amp", False))
        self.grad_clip_norm = float(tcfg.get("gradient_clip_norm", 0.0))
        self.tps_warmup_epochs = int(tcfg.get("tps_warmup_epochs", 0))

        scheduler_cfg = tcfg.get("scheduler", {})
        scheduler_type = str(scheduler_cfg.get("type", "none"))
        if scheduler_type == "cosine":
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer, T_max=self.max_epochs,
                eta_min=float(scheduler_cfg.get("min_lr", 1e-6)),
            )
        elif scheduler_type == "step":
            self.scheduler = torch.optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=int(scheduler_cfg.get("step_size", 100)),
                gamma=float(scheduler_cfg.get("gamma", 0.5)),
            )
        else:
            self.scheduler = None

        self.scaler = GradScaler(enabled=self.use_amp)

        self.selection_metric = str(config.get("selection", {}).get("metric", "pathology_mean_dice"))
        self.metrics_to_save = list(config.get("selection", {}).get(
            "metrics_to_save",
            ["mean_dice", "edema_dice", "scar_dice", "cine_scar_dice", "pathology_mean_dice"],
        ))

    def _freeze_tps(self) -> None:
        for name, param in self.model.named_parameters():
            if "tps" in name or "warper" in name:
                param.requires_grad_(False)

    def _unfreeze_tps(self) -> None:
        for name, param in self.model.named_parameters():
            if "tps" in name or "warper" in name:
                param.requires_grad_(True)

    def _save_json(self, content: dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(content, handle, indent=2, ensure_ascii=True)

    def _save_checkpoint(self, name: str, epoch: int, metrics: dict[str, float], train_metrics: dict[str, float]) -> Path:
        destination = self.output_dir / f"{name}.pt"
        torch.save({
            "model_state": self.model.state_dict(),
            "optimizer_state": self.optimizer.state_dict(),
            "epoch": int(epoch), "metrics": metrics, "train_metrics": train_metrics,
            "config": self.config, "track": self.track, "stage": self.stage,
            "arch": self.arch, "fold": self.fold,
        }, destination)
        return destination

    def _metric_value(self, metrics: dict[str, float], metric_name: str, fallback: str = "mean_dice") -> float:
        value = metrics.get(metric_name, metrics.get(fallback, 0.0))
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        return value if np.isfinite(value) else 0.0

    def train_one_epoch(self, epoch: int) -> dict[str, float]:
        self.model.train()

        if self.tps_warmup_epochs > 0:
            if epoch <= self.tps_warmup_epochs:
                self._freeze_tps()
            elif epoch == self.tps_warmup_epochs + 1:
                self._unfreeze_tps()

        meter: dict[str, list[float]] = {}
        for batch_idx, batch in enumerate(self.loader):
            image = batch["image"].to(self.device, non_blocking=True)
            batch_gpu = {
                "image": image,
                "label": batch["label"].to(self.device, non_blocking=True),
                "supervision_mask": batch["supervision_mask"].to(self.device, non_blocking=True),
            }

            self.optimizer.zero_grad(set_to_none=True)

            with autocast(enabled=self.use_amp):
                outputs = self.model(image)
                losses = self.loss_fn(outputs, batch_gpu)

            self.scaler.scale(losses["loss"]).backward()

            if self.grad_clip_norm > 0:
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=self.grad_clip_norm)

            self.scaler.step(self.optimizer)
            self.scaler.update()

            for key, value in losses.items():
                meter.setdefault(key, []).append(float(value.detach().cpu().item()))

            if self.max_batches_per_epoch > 0 and (batch_idx + 1) >= self.max_batches_per_epoch:
                break

        if self.scheduler is not None:
            self.scheduler.step()

        return {key: float(np.mean(values)) if values else 0.0 for key, values in meter.items()}

    def validate(self) -> dict[str, float]:
        if not self.val_records:
            return {"mean_dice": 0.0}

        from myops.data.preprocessing import cache_path
        from myops.utils.io import torch_load

        self.model.eval()
        results = []
        image_size = self.config["data"].get("image_size", [192, 192])

        for record in self.val_records:
            payload = torch_load(cache_path(self.cache_root, record["track"], record["case_id"]))

            if self.stage == "coarse":
                result = predict_case_coarse(
                    self.model, payload, self.track, self.device, image_size=image_size,
                )
            else:
                if self.coarse_prediction_root is not None:
                    coarse_pt = torch_load(
                        self.coarse_prediction_root / self.track / f'{record["case_id"]}.pt'
                    )
                    coarse_prior = np.asarray(coarse_pt["label"], dtype=np.int16)
                else:
                    coarse_prior = np.asarray(payload.get("coarse_label", np.zeros(1)), dtype=np.int16)

                thresholds = self.config.get("inference", {}).get("thresholds")
                if isinstance(thresholds, dict):
                    from myops.data.labels import TRACK_CINE
                    if self.track == TRACK_CINE:
                        thresholds = [thresholds.get(k, 0.5) for k in ["myo", "lv", "scar"]]
                    else:
                        thresholds = [thresholds.get(k, 0.5) for k in ["myo", "lv", "rv", "edema", "scar"]]
                result = predict_case_fine(
                    self.model, payload, self.track, self.device,
                    coarse_prior=coarse_prior, image_size=image_size,
                    thresholds=thresholds,
                    use_cine_sequence=self.use_cine_sequence,
                    cine_frame_count=self.cine_frame_count,
                    channel_order=self.channel_order,
                    disable_coarse_prior=self.disable_coarse_prior,
                )
            results.append(result)

        metrics = evaluate_predictions(self.track, self.stage, results, str(self.cache_root))
        self.model.train()
        return metrics

    @staticmethod
    def _checkpoint_name_for_metric(metric_name: str) -> str:
        if metric_name == "mean_dice":
            return "best_mean"
        if metric_name.endswith("_dice"):
            return f"best_{metric_name[:-5]}"
        return f"best_{metric_name}"

    def run(self) -> dict[str, Any]:
        best_dice = -1.0
        best_pathology = -1.0
        best_epoch = 0
        best_pathology_epoch = 0
        best_by_metric: dict[str, dict[str, float | int]] = {}
        history: list[dict[str, Any]] = []

        for epoch in range(1, self.max_epochs + 1):
            train_metrics = self.train_one_epoch(epoch)
            val_metrics: dict[str, float] = {}

            if epoch % self.val_every == 0 or epoch == self.max_epochs:
                val_metrics = self.validate()
                self._save_checkpoint("last", epoch, val_metrics, train_metrics)

                mean_dice = float(val_metrics.get("mean_dice", 0.0))
                if mean_dice >= best_dice:
                    best_dice = mean_dice
                    best_epoch = int(epoch)
                    self._save_checkpoint("best", epoch, val_metrics, train_metrics)
                    self._save_checkpoint("best_mean", epoch, val_metrics, train_metrics)

                pathology_value = self._metric_value(val_metrics, self.selection_metric)
                if pathology_value >= best_pathology:
                    best_pathology = pathology_value
                    best_pathology_epoch = int(epoch)
                    self._save_checkpoint("best_pathology", epoch, val_metrics, train_metrics)

                for metric_name in self.metrics_to_save:
                    if metric_name != "mean_dice" and metric_name not in val_metrics:
                        continue
                    mv = self._metric_value(val_metrics, metric_name)
                    current_best = float(best_by_metric.get(metric_name, {}).get("value", -1.0))
                    if mv >= current_best:
                        best_by_metric[metric_name] = {"value": mv, "epoch": int(epoch)}
                        self._save_checkpoint(self._checkpoint_name_for_metric(metric_name), epoch, val_metrics, train_metrics)

            history.append({"epoch": epoch, "train": train_metrics, "val": val_metrics})

            if epoch % 10 == 0 or epoch == self.max_epochs:
                self._save_json({"history": history}, self.output_dir / "history.json")

            current_lr = self.optimizer.param_groups[0]["lr"]
            print(f"  Epoch {epoch}/{self.max_epochs}  loss={train_metrics.get('loss', 0):.4f}  lr={current_lr:.6f}")

        summary = {
            "best_epoch": best_epoch, "best_mean_dice": best_dice,
            "best_pathology_epoch": best_pathology_epoch,
            "best_pathology_metric": self.selection_metric,
            "best_pathology_value": best_pathology,
            "best_metrics": best_by_metric, "output_dir": str(self.output_dir),
        }
        self._save_json(summary, self.output_dir / "summary.json")
        self._save_json({"history": history}, self.output_dir / "history.json")
        return summary
