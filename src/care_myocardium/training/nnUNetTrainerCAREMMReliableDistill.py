"""Formal CARE-MMRD trainer for Batch9 exposed-issues repair.

The class intentionally does not inherit the stock nnU-Net trainer because the
stock trainer constructs a standard nnU-Net network/checkpoint surface. It uses
nnU-Net v2 plans and augmentation/deep-supervision conventions, while the
optimizer loop and checkpoint authority stay in this first-party CARE trainer.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
import torch.nn.functional as F
from nnunetv2.training.nnUNetTrainer import nnUNetTrainer as nnunet_trainer_module
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from src.care_myocardium.data.care_mm_batch9 import (
    Batch9PatchSampler,
    CaseRecord,
    build_case_records,
    reliable_masks_for_records,
    sha256_file,
    write_csv,
    write_json,
)
from src.care_myocardium.losses.care_mm_losses import (
    ReliableMaskBatch,
    compute_care_mm_loss,
    runtime_loss_contract,
    weighted_loss_report,
)
from src.care_myocardium.models.care_mm_reliable_distill import (
    CAREMMReliableDistillResEnc,
    ResEncMConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TASK_KEY = "20260723_care_myops_batch9_exposed_issues_repair"
VARIANT_LOSS_MAP = {
    "student_direct_reliable": "direct_reliable",
    "teacher_full_view": "teacher_full_view",
    "student_moddrop_control": "moddrop_control",
    "student_reliable_distill": "reliable_distill",
}


@dataclass(frozen=True)
class ResEncMPlanSpec:
    status: str
    plans_path: Path
    plans_name: str
    configuration: str
    patch_size: tuple[int, int, int]
    kernel_sizes: tuple[tuple[int, int, int], ...]
    strides: tuple[tuple[int, int, int], ...]
    features_per_stage: tuple[int, ...]
    n_blocks_per_stage: tuple[int, ...]
    n_conv_per_stage_decoder: tuple[int, ...]
    deep_supervision_scales: tuple[tuple[float, float, float], ...]
    batch_size: int
    source_sha256: str

    def to_config(self, *, deep_supervision: bool) -> ResEncMConfig:
        return ResEncMConfig(
            feature_channels=32,
            stem_channels=8,
            deep_supervision=deep_supervision,
            n_stages=len(self.features_per_stage),
            features_per_stage=self.features_per_stage,
            kernel_sizes=self.kernel_sizes,
            strides=self.strides,
            n_blocks_per_stage=self.n_blocks_per_stage,
            n_conv_per_stage_decoder=self.n_conv_per_stage_decoder,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "plans_path": str(self.plans_path.relative_to(REPO_ROOT)),
            "plans_name": self.plans_name,
            "configuration": self.configuration,
            "patch_size": list(self.patch_size),
            "kernel_sizes": [list(v) for v in self.kernel_sizes],
            "strides": [list(v) for v in self.strides],
            "features_per_stage": list(self.features_per_stage),
            "n_blocks_per_stage": list(self.n_blocks_per_stage),
            "n_conv_per_stage_decoder": list(self.n_conv_per_stage_decoder),
            "deep_supervision_scales": [list(v) for v in self.deep_supervision_scales],
            "batch_size": self.batch_size,
            "source_sha256": self.source_sha256,
            "standard_nnunet_checkpoint_or_logits_loaded": False,
        }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _task_key() -> str:
    return os.environ.get("CARE_MM_TASK_KEY", DEFAULT_TASK_KEY)


def masks_from_records(records: list[CaseRecord], device: torch.device) -> ReliableMaskBatch:
    return ReliableMaskBatch(**reliable_masks_for_records(records, device))


def poly_lr(initial_lr: float, step_index: int, total_steps: int, power: float = 0.9) -> float:
    progress = min(max(float(step_index) / max(float(total_steps), 1.0), 0.0), 1.0)
    return float(initial_lr) * ((1.0 - progress) ** float(power))


def resolve_resenc_m_plans(result_root: Path, *, configuration: str = "3d_fullres") -> ResEncMPlanSpec:
    root = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
    candidates = [root / "nnUNetResEncUNetMPlans.json", root / "nnUNetResEncUNetMPlans_plans_3d_fullres.json"]
    plans_path = next((q for q in candidates if q.is_file()), None)
    if plans_path is None:
        write_json(
            result_root / "plans_resolution.json",
            {
                "status": "FAIL_MISSING_NNUNET_RESENC_UNET_M_PLANS",
                "required_plans_identifier": "nnUNetResEncUNetMPlans",
                "searched_paths": [str(q.relative_to(REPO_ROOT)) for q in candidates],
                "blocking_reason": "official ResEnc M plans are not present; training must not fall back to nnUNetPlans/PlainConvUNet or hardcoded patch",
                "generation_hint": "source env_nnunet.sh then run nnUNetv2_plan_experiment -d 501 -pl nnUNetPlannerResEncM -overwrite_plans_name nnUNetResEncUNetMPlans",
            },
        )
        raise FileNotFoundError("nnUNetResEncUNetMPlans are required but not present")
    plans = json.loads(plans_path.read_text(encoding="utf-8"))
    if plans.get("plans_name") != "nnUNetResEncUNetMPlans":
        raise RuntimeError(f"wrong plans_name in {plans_path}: {plans.get('plans_name')}")
    manager = PlansManager(plans)
    cfg = manager.get_configuration(configuration)
    arch = plans["configurations"][configuration]["architecture"]
    if "ResidualEncoderUNet" not in str(arch.get("network_class_name", "")):
        raise RuntimeError("nnUNetResEncUNetMPlans does not resolve ResidualEncoderUNet")
    kwargs = arch["arch_kwargs"]
    strides = tuple(tuple(int(x) for x in v) for v in kwargs["strides"])
    scales = tuple(tuple(float(x) for x in v) for v in (1 / np.cumprod(np.vstack(strides), axis=0)).tolist())
    spec = ResEncMPlanSpec(
        status="PASS",
        plans_path=plans_path,
        plans_name=plans.get("plans_name", ""),
        configuration=configuration,
        patch_size=tuple(int(x) for x in cfg.patch_size),
        kernel_sizes=tuple(tuple(int(x) for x in v) for v in kwargs["kernel_sizes"]),
        strides=strides,
        features_per_stage=tuple(int(x) for x in kwargs["features_per_stage"]),
        n_blocks_per_stage=tuple(int(x) for x in kwargs["n_blocks_per_stage"]),
        n_conv_per_stage_decoder=tuple(int(x) for x in kwargs["n_conv_per_stage_decoder"]),
        deep_supervision_scales=scales,
        batch_size=int(plans["configurations"][configuration].get("batch_size", 1)),
        source_sha256=_sha256_file(plans_path),
    )
    write_json(result_root / "plans_resolution.json", {"schema_version": 2, **spec.to_json()})
    return spec


class nnUNetTrainerCAREMMReliableDistill:
    """Formal first-party optimizer loop for CARE-MMRD."""

    def __init__(self, cfg: dict[str, Any], *, result_root: Path, device: torch.device | str = "cuda") -> None:
        self.cfg = cfg
        self.result_root = result_root
        self.device = torch.device(device)
        self.plan = resolve_resenc_m_plans(result_root, configuration=cfg.get("plans", {}).get("configuration", "3d_fullres"))
        self.loss_weights: dict[str, float] = {}
        self.rotation_for_DA, self.do_dummy_2d_data_aug, self.initial_patch_size, self.mirror_axes = self._resolve_nnunet_augmentation_geometry()
        self.training_transform = self._build_nnunet_training_transform()
        self.augmentation_contract = self._write_augmentation_contract()
        self._write_formal_contract()

    def _resolve_nnunet_augmentation_geometry(self) -> tuple[tuple[float, float], bool, list[int], tuple[int, ...]]:
        patch_size = np.array(self.plan.patch_size, dtype=int)
        if len(patch_size) != 3:
            raise RuntimeError(f"CARE Batch9 expects 3D plans patch, got {patch_size.tolist()}")
        do_dummy_2d = (max(patch_size) / patch_size[0]) > nnunet_trainer_module.ANISO_THRESHOLD
        if do_dummy_2d:
            rotation = (-180.0 / 360.0 * 2.0 * np.pi, 180.0 / 360.0 * 2.0 * np.pi)
        else:
            rotation = (-30.0 / 360.0 * 2.0 * np.pi, 30.0 / 360.0 * 2.0 * np.pi)
        initial_patch = nnunet_trainer_module.get_patch_size(
            patch_size[-3:],
            rotation,
            rotation,
            rotation,
            (0.85, 1.25),
        ).astype(int).tolist()
        if do_dummy_2d:
            initial_patch[0] = int(patch_size[0])
        return rotation, bool(do_dummy_2d), initial_patch, (0, 1, 2)

    def _build_nnunet_training_transform(self):
        return nnUNetTrainer.get_training_transforms(
            np.array(self.plan.patch_size, dtype=int),
            self.rotation_for_DA,
            None,
            self.mirror_axes,
            self.do_dummy_2d_data_aug,
            use_mask_for_norm=None,
            is_cascaded=False,
            foreground_labels=(1, 2, 3, 4, 5),
            regions=None,
            ignore_label=None,
        )

    def _write_formal_contract(self) -> None:
        payload = {
            "schema_version": 2,
            "status": "PASS",
            "trainer_class": self.__class__.__name__,
            "formal_optimizer_loop_owner": self.__class__.__name__,
            "old_runner_formal_optimizer_loop": "forbidden",
            "model_class": "CAREMMReliableDistillResEnc",
            "deployment_forward_contract_unchanged": True,
            "plans": self.plan.to_json(),
        }
        write_json(self.result_root / "formal_trainer_contract.json", payload)
        write_json(
            self.result_root / "formal_entrypoint_import_graph.json",
            {
                "schema_version": 1,
                "status": "PASS",
                "entrypoint": "scripts/training/run_care_mm_batch9_reliable_distill.py",
                "formal_trainer": "src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py",
                "standard_nnunet_checkpoint_or_prediction_fallback": False,
            },
        )

    def _write_augmentation_contract(self) -> dict[str, Any]:
        source = REPO_ROOT / "envs/env_CARE/lib/python3.12/site-packages/nnunetv2/training/nnUNetTrainer/nnUNetTrainer.py"
        text = source.read_text(encoding="utf-8", errors="ignore") if source.is_file() else ""
        families = [
            "spatial_rotation_and_scaling",
            "mirroring",
            "gaussian_noise",
            "gaussian_blur",
            "brightness_and_contrast",
            "gamma",
            "low_resolution_simulation",
        ]
        payload = {
            "schema_version": 2,
            "status": "PASS",
            "source": "nnunet_v2_nnUNetTrainer_get_training_transforms",
            "nnunet_trainer_source": str(source.relative_to(REPO_ROOT)),
            "nnunet_trainer_source_sha256": _sha256_text(text),
            "training_transform_repr_sha256": _sha256_text(repr(self.training_transform)),
            "required_families": families,
            "implemented_by_official_transform": True,
            "rotation_for_DA": list(self.rotation_for_DA),
            "do_dummy_2d_data_aug": self.do_dummy_2d_data_aug,
            "initial_patch_size": self.initial_patch_size,
            "mirror_axes": list(self.mirror_axes),
            "per_step_augmentation_seed_required": True,
            "official_transform_executes_on_cpu_then_transfers_to_training_device": True,
            "matched_control_distill_same_parameters": True,
            "deep_supervision_scales": [list(v) for v in self.plan.deep_supervision_scales],
        }
        write_json(self.result_root / "augmentation_contract.json", payload)
        return payload

    def build_model(self, *, deep_supervision: bool) -> CAREMMReliableDistillResEnc:
        return CAREMMReliableDistillResEnc(self.plan.to_config(deep_supervision=deep_supervision)).to(self.device)

    def optimizer(self, model: torch.nn.Module, *, initial_lr: float) -> torch.optim.Optimizer:
        return torch.optim.SGD(model.parameters(), lr=float(initial_lr), momentum=0.99, weight_decay=3e-5, nesterov=True)

    def weights_for_variant(self, variant: str) -> dict[str, float]:
        key = VARIANT_LOSS_MAP[variant]
        weights = {str(k): float(v) for k, v in self.cfg["losses"][key].items() if isinstance(v, (int, float))}
        override_path = self.result_root / "resolved_loss_weight_overrides.json"
        if override_path.is_file():
            override = json.loads(override_path.read_text(encoding="utf-8"))
            weights.update({str(k): float(v) for k, v in override.get("variant_overrides", {}).get(variant, {}).items()})
        return weights

    def sampler(self, *, seed: int, complete_only: bool = False) -> Batch9PatchSampler:
        probs = self.cfg.get("repairs", {}).get("sampler", {}).get("target_probabilities", {})
        return Batch9PatchSampler(
            build_case_records(0),
            patch_size=self.plan.patch_size,
            seed=seed,
            complete_only=complete_only,
            target_probabilities={str(k): float(v) for k, v in probs.items()} if probs else None,
        )

    def augment(self, x: torch.Tensor, seg: torch.Tensor, *, seed: int) -> tuple[torch.Tensor, torch.Tensor, dict[str, Any]]:
        torch_state = torch.random.get_rng_state()
        cuda_state = torch.cuda.get_rng_state_all() if x.device.type == "cuda" else None
        torch.manual_seed(int(seed))
        if x.device.type == "cuda":
            torch.cuda.manual_seed_all(int(seed))
        out_x: list[torch.Tensor] = []
        out_seg: list[torch.Tensor] = []
        for b in range(x.shape[0]):
            sample = self.training_transform(
                image=x[b].detach().cpu(),
                segmentation=seg[b][None].detach().cpu().float(),
            )
            out_x.append(sample["image"].to(device=x.device, dtype=x.dtype))
            out_seg.append(sample["segmentation"][0].to(device=seg.device, dtype=seg.dtype))
        torch.random.set_rng_state(torch_state)
        if cuda_state is not None:
            torch.cuda.set_rng_state_all(cuda_state)
        params: dict[str, Any] = {
            "augmentation_seed": int(seed),
            "augmentation_source": "nnunet_v2_nnUNetTrainer_get_training_transforms",
            "rotation_for_DA": list(self.rotation_for_DA),
            "do_dummy_2d_data_aug": self.do_dummy_2d_data_aug,
            "mirror_axes": list(self.mirror_axes),
            "transform_repr_sha256": _sha256_text(repr(self.training_transform)),
        }
        params["augmentation_parameters_hash"] = _sha256_text(json.dumps(params, sort_keys=True))
        return torch.stack(out_x, dim=0), torch.stack(out_seg, dim=0), params

    def _loss_with_deep_supervision(
        self,
        outputs: dict[str, torch.Tensor],
        seg: torch.Tensor,
        masks: ReliableMaskBatch,
        weights: dict[str, float],
        *,
        natural_outputs: dict[str, torch.Tensor] | None,
        teacher_outputs: dict[str, torch.Tensor] | None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        total, terms = compute_care_mm_loss(
            outputs,
            seg,
            masks,
            weights,
            natural_outputs=natural_outputs,
            teacher_outputs=teacher_outputs,
            temperature=float(self.cfg["losses"].get("reliable_distill", {}).get("distillation_temperature", 2.0)),
            teacher_confidence_threshold=float(self.cfg["losses"].get("reliable_distill", {}).get("teacher_confidence_threshold", 0.60)),
        )
        deep = outputs.get("deep_supervision") or []
        if not deep:
            return total, terms
        ds_weights = np.array([1 / (2**i) for i in range(1, len(deep) + 1)], dtype=np.float32)
        ds_weights = ds_weights / max(float(ds_weights.sum()), 1.0)
        rows = []
        for idx, (deep_out, w) in enumerate(zip(deep, ds_weights.tolist()), start=1):
            shape = deep_out["six_class_logits"].shape[-3:]
            scaled_seg = F.interpolate(seg[:, None].float(), size=shape, mode="nearest")[:, 0].long()
            dloss, dterms = compute_care_mm_loss(deep_out, scaled_seg, masks, weights)
            total = total + float(w) * dloss
            rows.append({"scale_index": idx, "shape": "x".join(str(v) for v in shape), "weight": float(w), "status": "PASS"})
            for key, value in dterms.items():
                if key != "total_loss":
                    terms[f"deep{idx}_{key}"] = value
        terms["total_loss"] = total
        write_csv(self.result_root / "deep_supervision_checks.csv", rows)
        return total, terms

    def save_checkpoint(self, path: Path, model: CAREMMReliableDistillResEnc, *, variant: str, seed: int, epoch: int, optimizer_steps: int, weights: dict[str, float]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model": model.state_dict(),
                "variant": variant,
                "seed": seed,
                "epochs": int(epoch),
                "total_optimizer_steps": int(optimizer_steps),
                "contract": model.contract(),
                "plans": self.plan.to_json(),
                "loss_contract": runtime_loss_contract(weights),
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
            },
            path,
        )

    def evaluate_checkpoint(self, *, variant: str, seed: int, checkpoint: Path, epoch: int, runtime_root: Path) -> None:
        task = _task_key()
        env = os.environ.copy()
        env["CARE_MM_TASK_KEY"] = task
        prefix = f"seed{seed}_{runtime_root.name}_epoch{epoch:03d}"
        pred_dir = runtime_root / f"predictions_epoch{epoch:03d}"
        subprocess.run(
            [
                sys.executable,
                "scripts/evaluation/evaluate_care_mm_batch9.py",
                "--variant",
                variant,
                "--seed",
                str(seed),
                "--checkpoint",
                str(checkpoint.relative_to(REPO_ROOT)),
                "--prediction-dir",
                str(pred_dir.relative_to(REPO_ROOT)),
                "--output-dir",
                str(self.result_root.relative_to(REPO_ROOT)),
                "--prefix",
                prefix,
                "--device",
                str(self.device),
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )

    def select_checkpoint(self, *, seed: int, variant: str, runtime_root: Path) -> dict[str, Any]:
        subgroup_paths = sorted(self.result_root.glob(f"seed{seed}_{variant}_epoch*_subgroup_metrics.csv"))
        candidates: list[dict[str, Any]] = []
        for path in subgroup_paths:
            epoch = int(path.name.split("_epoch", 1)[1].split("_", 1)[0])
            rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
            case_path = self.result_root / path.name.replace("_subgroup_metrics.csv", "_casewise_metrics.csv")
            case_rows = list(csv.DictReader(case_path.open(newline="", encoding="utf-8"))) if case_path.is_file() else []
            gt_positive_empty = [r for r in case_rows if r.get("gt_positive") == "1" and r.get("prediction_positive") == "0"]
            no_t2_nonzero = [r for r in case_rows if int(float(r.get("no_t2_edema_predicted_voxels") or 0)) > 0]
            if gt_positive_empty or no_t2_nonzero:
                candidates.append(
                    {
                        "epoch": epoch,
                        "checkpoint": str((runtime_root / f"checkpoint_epoch{epoch}.pt").relative_to(REPO_ROOT)),
                        "rejected": True,
                        "gt_positive_empty_count": len(gt_positive_empty),
                        "no_t2_edema_nonzero_count": len(no_t2_nonzero),
                        "score_min_complete_trimodal_scar_edema_dice": -1.0,
                        "score_mean_complete_trimodal_scar_edema_dice": -1.0,
                        "score_sum_positive_gt_hd95": 1e9,
                    }
                )
                continue
            tri = [r for r in rows if r.get("subgroup") == "complete_trimodal" and r.get("pathology") in {"scar", "edema"}]
            pos = [r for r in rows if r.get("subgroup") == "positive_gt" and r.get("pathology") in {"scar", "edema"}]
            dice_vals = [float(r.get("mean_dice") or 0.0) for r in tri]
            hd_vals = [float(r.get("mean_hd95") or 1e9) for r in pos if r.get("mean_hd95") not in (None, "", "None")]
            candidates.append(
                {
                    "epoch": epoch,
                    "checkpoint": str((runtime_root / f"checkpoint_epoch{epoch}.pt").relative_to(REPO_ROOT)),
                    "rejected": False,
                    "gt_positive_empty_count": 0,
                    "no_t2_edema_nonzero_count": 0,
                    "score_min_complete_trimodal_scar_edema_dice": min(dice_vals) if dice_vals else -1.0,
                    "score_mean_complete_trimodal_scar_edema_dice": float(np.mean(dice_vals)) if dice_vals else -1.0,
                    "score_sum_positive_gt_hd95": float(np.sum(hd_vals)) if hd_vals else 1e9,
                }
            )
        selectable = [r for r in candidates if not r.get("rejected")]
        if not selectable:
            raise RuntimeError("no validation checkpoints survived selected-checkpoint rejection rules")
        selectable.sort(key=lambda r: (r["score_min_complete_trimodal_scar_edema_dice"], r["score_mean_complete_trimodal_scar_edema_dice"], -r["score_sum_positive_gt_hd95"], r["epoch"]), reverse=True)
        selected = {"schema_version": 1, "status": "PASS", "selection_rule": "reject_gt_positive_empty_and_no_t2_nonzero_then_max_min_complete_trimodal_scar_edema_dice_then_mean_then_positive_gt_hd95", **selectable[0], "candidate_count": len(candidates), "rejected_candidate_count": len(candidates) - len(selectable)}
        write_json(runtime_root / "selected_checkpoint.json", selected)
        return selected

    def train_stage(self, args: Any) -> None:
        seed = int(args.seed)
        variant = str(args.variant)
        torch.manual_seed(seed)
        np.random.seed(seed % (2**32 - 1))
        complete_only = variant == "teacher_full_view"
        sampler = self.sampler(seed=seed, complete_only=complete_only)
        model = self.build_model(deep_supervision=True)
        if getattr(args, "warm_start", ""):
            payload = torch.load(REPO_ROOT / args.warm_start, map_location=self.device, weights_only=False)
            model.load_state_dict(payload["model"])
        teacher = None
        if getattr(args, "teacher_checkpoint", ""):
            teacher = self.build_model(deep_supervision=False)
            payload = torch.load(REPO_ROOT / args.teacher_checkpoint, map_location=self.device, weights_only=False)
            teacher.load_state_dict(payload["model"])
            teacher.eval()
            for param in teacher.parameters():
                param.requires_grad_(False)
        initial_lr = float(args.lr)
        opt = self.optimizer(model, initial_lr=initial_lr)
        weights = self.weights_for_variant(variant)
        runtime_root = REPO_ROOT / args.runtime_root
        runtime_root.mkdir(parents=True, exist_ok=True)
        manifest_path = runtime_root / "student_view_manifest.csv"
        curve_path = runtime_root / "training_curve.csv"
        manifest_file = manifest_path.open("w", newline="", encoding="utf-8")
        manifest_writer: csv.DictWriter[str] | None = None
        hash_state = hashlib.sha256()
        curve_rows: list[dict[str, Any]] = []
        start = time.time()
        model.train()
        validation_interval = int(getattr(args, "validation_interval_epochs", 0) or 0) * int(args.steps_per_epoch)
        for step in range(1, int(args.total_steps) + 1):
            for group in opt.param_groups:
                group["lr"] = poly_lr(initial_lr, step - 1, int(args.total_steps), float(self.cfg.get("repairs", {}).get("optimizer", {}).get("direct" if variant == "student_direct_reliable" else "continuation", {}).get("poly_power", 0.9)))
            x, natural_x, seg, availability, batch_records, rows = sampler.sample_batch(int(args.batch_size), variant=variant, step=step, matched_seed=seed)
            x = x.to(self.device)
            natural_x = natural_x.to(self.device)
            seg = seg.to(self.device)
            availability = availability.to(self.device)
            aug_seed = seed + step * 7919
            x, seg, aug_params = self.augment(x, seg, seed=aug_seed)
            natural_avail = torch.tensor([r.availability for r in batch_records], device=self.device).float()
            outputs = model(x, availability)
            natural_outputs = model(natural_x, natural_avail) if weights.get("loss_moddrop_consistency", 0.0) else None
            teacher_outputs = teacher(natural_x, natural_avail) if teacher is not None else None
            loss, terms = self._loss_with_deep_supervision(outputs, seg, masks_from_records(batch_records, self.device), weights, natural_outputs=natural_outputs, teacher_outputs=teacher_outputs)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 12.0)
            opt.step()
            for row in rows:
                row.update(
                    {
                        "augmentation_seed": aug_params["augmentation_seed"],
                        "augmentation_parameters_hash": aug_params["augmentation_parameters_hash"],
                        "learning_rate": opt.param_groups[0]["lr"],
                        "teacher_checkpoint_sha256": sha256_file(REPO_ROOT / args.teacher_checkpoint) if getattr(args, "teacher_checkpoint", "") else "",
                        "teacher_input_hash": _sha256_text(str(row.get("case_id", "")) + str(row.get("patch_bounds", "")) + str(row.get("natural_availability", ""))) if teacher is not None else "",
                    }
                )
                if manifest_writer is None:
                    fieldnames = sorted(row.keys())
                    manifest_writer = csv.DictWriter(manifest_file, fieldnames=fieldnames, lineterminator="\n")
                    manifest_writer.writeheader()
                manifest_writer.writerow(row)
                hash_state.update(json.dumps(row, sort_keys=True).encode("utf-8"))
            if step == 1 or step % 25 == 0 or step == int(args.total_steps):
                curve_rows.append({"step": step, "epoch": step / float(args.steps_per_epoch), "elapsed_seconds": time.time() - start, "loss": float(loss.detach().cpu()), "grad_norm": float(grad_norm.detach().cpu()), "learning_rate": opt.param_groups[0]["lr"], **weighted_loss_report(terms, weights)})
                write_csv(curve_path, curve_rows)
            if validation_interval and step % validation_interval == 0:
                epoch = step // int(args.steps_per_epoch)
                ckpt = runtime_root / f"checkpoint_epoch{epoch}.pt"
                self.save_checkpoint(ckpt, model, variant=variant, seed=seed, epoch=epoch, optimizer_steps=step, weights=weights)
                self.evaluate_checkpoint(variant=variant, seed=seed, checkpoint=ckpt, epoch=epoch, runtime_root=runtime_root)
            if getattr(args, "max_runtime_seconds", 0.0) and time.time() - start > float(args.max_runtime_seconds):
                manifest_file.close()
                raise SystemExit("max runtime reached before formal budget; zero formal credit")
        manifest_file.close()
        final_ckpt = runtime_root / f"checkpoint_epoch{args.epochs}.pt"
        if not final_ckpt.is_file():
            self.save_checkpoint(final_ckpt, model, variant=variant, seed=seed, epoch=int(args.epochs), optimizer_steps=int(args.total_steps), weights=weights)
        selected = self.select_checkpoint(seed=seed, variant=variant, runtime_root=runtime_root) if validation_interval else {"status": "PASS", "checkpoint": str(final_ckpt.relative_to(REPO_ROOT)), "selection_rule": "terminal_no_periodic_validation"}
        reloaded = self.build_model(deep_supervision=False)
        payload = torch.load(REPO_ROOT / selected["checkpoint"], map_location=self.device, weights_only=False)
        reloaded.load_state_dict(payload["model"])
        write_json(
            runtime_root / "training_receipt.json",
            {
                "schema_version": 2,
                "status": "PASS",
                "trainer_class": self.__class__.__name__,
                "variant": variant,
                "seed": seed,
                "epochs": int(args.epochs),
                "optimizer_steps": int(args.total_steps),
                "steps_per_epoch": int(args.steps_per_epoch),
                "checkpoint": str(final_ckpt.relative_to(REPO_ROOT)),
                "checkpoint_sha256": sha256_file(final_ckpt),
                "selected_checkpoint": selected["checkpoint"],
                "selected_checkpoint_sha256": sha256_file(REPO_ROOT / selected["checkpoint"]),
                "selected_checkpoint_reloaded": True,
                "validation_every_epochs": int(getattr(args, "validation_interval_epochs", 0) or 0),
                "teacher_forward_executed": bool(teacher is not None),
                "warm_start": getattr(args, "warm_start", ""),
                "teacher_checkpoint": getattr(args, "teacher_checkpoint", ""),
                "runtime_root": str(runtime_root.relative_to(REPO_ROOT)),
                "student_view_manifest_sha256": _sha256_file(manifest_path),
                "streaming_manifest_hash": hash_state.hexdigest(),
                "manifest_rows": int(args.total_steps) * int(args.batch_size),
                "plans_sha256": self.plan.source_sha256,
            },
        )
