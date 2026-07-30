#!/usr/bin/env python3
"""Run real nnU-Net decoder-reset forensic diagnostics for the CARE V2 packet.

This script intentionally uses nnU-Net v2 plans, network construction,
patch sampling, augmentation, optimizer, scheduler, deep-supervision loss, and
validation exporter. The only override is the forensic split: fold0
`actual_train` for training and frozen `inner_select` for validation/export.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
SPLIT_RECEIPT_REL = Path("results/20260729_care_prism_fold0_fold1_v2/split_freeze_receipt.json")
DEFAULT_CHECKPOINT_REL = Path(
    "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth"
)

VARIANT_SPECS: dict[str, dict[str, Any]] = {
    "D0_FULL_PRETRAINED_IDENTITY": {
        "epochs": 1,
        "diagnostic_train_epochs": 0,
        "iterations_per_epoch": 0,
        "checkpoint_load": "full_checkpoint_for_identity",
        "network_load": "full_network",
        "freeze_policy": "none",
        "validate_after": True,
        "initial_lr": None,
    },
    "D1_DECODER_RESET_ENCODER_FROZEN": {
        "epochs": 6,
        "diagnostic_train_epochs": 6,
        "iterations_per_epoch": 250,
        "checkpoint_load": "encoder_only_fresh_optimizer",
        "network_load": "encoder_only",
        "freeze_policy": "freeze_all_encoder",
        "validate_after": True,
        "initial_lr": None,
    },
    "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE": {
        "epochs": 12,
        "diagnostic_train_epochs": 12,
        "iterations_per_epoch": 250,
        "checkpoint_load": "encoder_only_fresh_optimizer",
        "network_load": "encoder_only",
        "freeze_policy": "freeze_encoder_stages_0_to_3",
        "validate_after": True,
        "initial_lr": None,
    },
    "D3_FULL_MODEL_SHORT_FINETUNE": {
        "epochs": 4,
        "diagnostic_train_epochs": 4,
        "iterations_per_epoch": 250,
        "checkpoint_load": "full_network_fresh_optimizer",
        "network_load": "full_network",
        "freeze_policy": "none",
        "validate_after": True,
        "initial_lr": 1e-5,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True, default=json_default)
        f.write("\n")


def json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, (set, tuple)):
        return list(obj)
    return str(obj)


def git_output(root: Path, args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception as exc:  # pragma: no cover - diagnostic metadata only
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def prepare_env(root: Path, runtime_root: Path) -> None:
    os.environ.setdefault("CARE_ROOT", str(root))
    os.environ["nnUNet_raw"] = str(root / "data/nnUNet/nnUNet_raw")
    os.environ["nnUNet_preprocessed"] = str(root / "data/nnUNet/nnUNet_preprocessed")
    os.environ["nnUNet_results"] = str(runtime_root / "nnUNet_results")
    os.environ.setdefault("nnUNet_compile", "false")
    os.environ.setdefault("OMP_NUM_THREADS", "8")
    os.environ.setdefault("MKL_NUM_THREADS", "8")
    os.environ.setdefault("nnUNet_n_proc_DA", "4")
    os.environ.setdefault("MPLCONFIGDIR", str(Path("/tmp") / "care_forensics_mplconfig"))


def import_nnunet_modules():
    import torch
    import nnunetv2.paths as nn_paths
    from batchgenerators.utilities.file_and_folder_operations import load_json
    from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import (
        nnUNetTrainer_500epochs,
    )

    # nnunetv2.paths captures environment variables during import. Keep it in
    # sync when this script is called from an already-initialized interpreter.
    nn_paths.nnUNet_raw = os.environ["nnUNet_raw"]
    nn_paths.nnUNet_preprocessed = os.environ["nnUNet_preprocessed"]
    nn_paths.nnUNet_results = os.environ["nnUNet_results"]
    return torch, load_json, nnUNetTrainer_500epochs


def make_forensic_trainer_class(base_cls, actual_train: list[str], inner_select: list[str]):
    class CAREForensicSplitNnUNetTrainer(base_cls):
        def do_split(self):  # type: ignore[override]
            self.print_to_log_file(
                "Using CARE forensic V2 split: "
                f"{len(actual_train)} actual_train cases -> {len(inner_select)} inner_select cases"
            )
            return list(actual_train), list(inner_select)

    CAREForensicSplitNnUNetTrainer.__name__ = "CAREForensicSplitNnUNetTrainer"
    return CAREForensicSplitNnUNetTrainer


def unwrap_network(network):
    if hasattr(network, "_orig_mod"):
        return network._orig_mod
    return network


def load_network_weights(torch, trainer, checkpoint_path: Path, network_load: str) -> dict[str, Any]:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    raw_state = checkpoint["network_weights"]
    model = unwrap_network(trainer.network)
    current = model.state_dict()
    load_state = {}
    skipped = []
    for key, value in raw_state.items():
        normalized = key[7:] if key.startswith("module.") else key
        if network_load == "encoder_only" and not normalized.startswith("encoder."):
            skipped.append(normalized)
            continue
        if normalized in current and tuple(current[normalized].shape) == tuple(value.shape):
            load_state[normalized] = value
        else:
            skipped.append(normalized)
    incompatible = model.load_state_dict(load_state, strict=False)
    return {
        "checkpoint_current_epoch": checkpoint.get("current_epoch"),
        "checkpoint_trainer_name": checkpoint.get("trainer_name"),
        "checkpoint_keys": sorted(checkpoint.keys()),
        "raw_weight_count": len(raw_state),
        "loaded_weight_count": len(load_state),
        "skipped_weight_count": len(skipped),
        "missing_keys_count": len(incompatible.missing_keys),
        "unexpected_keys_count": len(incompatible.unexpected_keys),
        "missing_keys_sample": list(incompatible.missing_keys[:20]),
        "unexpected_keys_sample": list(incompatible.unexpected_keys[:20]),
        "skipped_keys_sample": skipped[:20],
    }


def apply_freeze_policy(trainer, policy: str) -> dict[str, Any]:
    import re

    trainable = []
    frozen = []
    for name, param in unwrap_network(trainer.network).named_parameters():
        requires_grad = True
        if policy == "freeze_all_encoder" and name.startswith("encoder."):
            requires_grad = False
        elif policy == "freeze_encoder_stages_0_to_3" and name.startswith("encoder."):
            match = re.match(r"encoder\.stages\.(\d+)\.", name)
            if match is None or int(match.group(1)) <= 3:
                requires_grad = False
        param.requires_grad = requires_grad
        if requires_grad:
            trainable.append(name)
        else:
            frozen.append(name)
    return {
        "freeze_policy": policy,
        "trainable_parameter_tensors": len(trainable),
        "frozen_parameter_tensors": len(frozen),
        "trainable_parameter_names_sample": trainable[:20],
        "frozen_parameter_names_sample": frozen[:20],
    }


def trainer_contract(trainer) -> dict[str, Any]:
    return {
        "trainer_class": trainer.__class__.__name__,
        "configuration": trainer.configuration_name,
        "num_input_channels": getattr(trainer, "num_input_channels", None),
        "num_epochs": trainer.num_epochs,
        "num_iterations_per_epoch": trainer.num_iterations_per_epoch,
        "num_val_iterations_per_epoch": trainer.num_val_iterations_per_epoch,
        "batch_size": trainer.batch_size,
        "oversample_foreground_percent": trainer.oversample_foreground_percent,
        "initial_lr": trainer.initial_lr,
        "weight_decay": trainer.weight_decay,
        "enable_deep_supervision": trainer.enable_deep_supervision,
        "label_heads": trainer.label_manager.num_segmentation_heads,
        "foreground_labels": list(trainer.label_manager.foreground_labels),
        "patch_size": list(trainer.configuration_manager.patch_size),
        "plans_name": trainer.plans_manager.plans_name,
        "dataset_name": trainer.plans_manager.dataset_name,
    }


def append_gpu_manifest(result_root: Path, row: dict[str, Any]) -> None:
    manifest = result_root / "v2_gpu_job_manifest.csv"
    fieldnames = [
        "timestamp_utc",
        "logical_run_id",
        "variant",
        "status",
        "job_id",
        "partition",
        "node",
        "gpu",
        "python",
        "torch",
        "cuda",
        "repo_sha",
        "task_sha",
        "config_sha",
        "split_sha",
        "checkpoint_sha",
        "command",
        "output_path",
    ]
    rows = []
    if manifest.exists():
        with manifest.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for old in reader:
                if old.get("logical_run_id") != row.get("logical_run_id") or old.get("variant") != row.get("variant"):
                    rows.append({k: old.get(k, "") for k in fieldnames})
    rows.append({k: str(row.get(k, "")) for k in fieldnames})
    with manifest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_task_status(result_root: Path, variant: str, status: str, notes: str) -> None:
    path = result_root / "v2_task_status.csv"
    fieldnames = ["task_id", "category", "required", "status", "terminal_status", "evidence_path", "notes"]
    rows = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = [{k: row.get(k, "") for k in fieldnames} for row in csv.DictReader(f)]
    task_id = "G3_REAL_NNUNET_DECODER_RESET"
    found = False
    for row in rows:
        if row.get("task_id") == task_id:
            row.update(
                {
                    "category": "gpu_diagnostic",
                    "required": "true",
                    "status": status,
                    "terminal_status": "false" if "RUNNING" in status or "PREFLIGHT" in status else "true",
                    "evidence_path": str(result_root / "runtime/nnunet_decoder_reset_real"),
                    "notes": f"{variant}: {notes}",
                }
            )
            found = True
    if not found:
        rows.append(
            {
                "task_id": task_id,
                "category": "gpu_diagnostic",
                "required": "true",
                "status": status,
                "terminal_status": "false" if "RUNNING" in status or "PREFLIGHT" in status else "true",
                "evidence_path": str(result_root / "runtime/nnunet_decoder_reset_real"),
                "notes": f"{variant}: {notes}",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result_root = root / RESULT_REL
    result_root.mkdir(parents=True, exist_ok=True)
    variant = args.variant
    spec = VARIANT_SPECS[variant]
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_root = result_root / "runtime/nnunet_decoder_reset_real" / run_id
    variant_root = runtime_root / variant
    variant_root.mkdir(parents=True, exist_ok=True)

    prepare_env(root, runtime_root)
    torch, load_json, trainer_base = import_nnunet_modules()

    plans_path = root / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
    dataset_json_path = root / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json"
    checkpoint_path = Path(args.checkpoint).resolve() if args.checkpoint else root / DEFAULT_CHECKPOINT_REL
    split_receipt_path = root / SPLIT_RECEIPT_REL
    split_receipt = read_json(split_receipt_path)
    fold0 = split_receipt["folds"]["fold0"]
    actual_train = list(fold0["inner_select_cases"]) if args.micro_debug else list(
        set(read_json(root / "data/benchmarks/protocol/splits_MyoPS.json")["folds"][0]["train"])
        - set(fold0["inner_select_cases"])
    )
    actual_train = sorted(actual_train)
    inner_select = list(fold0["inner_select_cases"])
    split_contract = {
        "source_receipt": str(split_receipt_path.relative_to(root)),
        "source_receipt_sha256": sha256_file(split_receipt_path),
        "actual_train_count": len(actual_train),
        "inner_select_count": len(inner_select),
        "actual_train_sha256": sha256_json(actual_train),
        "inner_select_sha256": sha256_json(inner_select),
        "micro_debug": bool(args.micro_debug),
        "outer_accessed_for_training_decisions": False,
    }

    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    forensic_cls = make_forensic_trainer_class(trainer_base, actual_train, inner_select)
    plans = load_json(str(plans_path))
    plans.setdefault("continue_training", False)
    trainer = forensic_cls(plans, "3d_fullres", 0, load_json(str(dataset_json_path)), device=device)
    trainer.output_folder_base = str(runtime_root / "nnUNet_output" / variant)
    trainer.output_folder = str(Path(trainer.output_folder_base) / "fold_0")
    trainer.num_epochs = int(spec["epochs"])
    trainer.num_iterations_per_epoch = int(spec["iterations_per_epoch"])
    trainer.save_every = 1
    if spec["initial_lr"] is not None:
        trainer.initial_lr = float(spec["initial_lr"])

    init_error = None
    try:
        trainer.initialize()
    except Exception as exc:
        init_error = f"{type(exc).__name__}: {exc}"
        raise

    if spec["checkpoint_load"] == "full_checkpoint_for_identity":
        trainer.load_checkpoint(str(checkpoint_path))
        load_receipt = {"loaded_by": "trainer.load_checkpoint", "network_load": "full_network"}
    else:
        load_receipt = load_network_weights(torch, trainer, checkpoint_path, str(spec["network_load"]))
        trainer.current_epoch = 0
        trainer.my_init_kwargs = trainer.my_init_kwargs

    freeze_receipt = apply_freeze_policy(trainer, str(spec["freeze_policy"]))
    trainer.optimizer, trainer.lr_scheduler = trainer.configure_optimizers()

    contract = {
        "created_at_utc": utc_now(),
        "status": "PREFLIGHT_READY" if args.action == "preflight" else "RUNNING_OR_COMPLETED",
        "task_key": "20260730_care_failure_forensics_deep_research_packet_v2_completion",
        "variant": variant,
        "run_id": run_id,
        "action": args.action,
        "uses_real_nnunet": True,
        "uses_real_nnunet_plans": True,
        "uses_real_nnunet_decoder": True,
        "uses_real_patch_sampling_and_augmentation": True,
        "uses_real_deep_supervision_loss": True,
        "prism_wrapper_residue_counted": False,
        "root": str(root),
        "runtime_root": str(runtime_root),
        "variant_root": str(variant_root),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "plans_path": str(plans_path),
        "plans_sha256": sha256_file(plans_path),
        "dataset_json_path": str(dataset_json_path),
        "dataset_json_sha256": sha256_file(dataset_json_path),
        "split_contract": split_contract,
        "variant_spec": spec,
        "trainer_contract": trainer_contract(trainer),
        "load_receipt": load_receipt,
        "freeze_receipt": freeze_receipt,
        "environment": {
            "python": sys.executable,
            "python_version": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "hostname": socket.gethostname(),
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": getattr(torch.version, "cuda", None),
            "cuda_device_count": torch.cuda.device_count(),
            "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", ""),
            "slurm_step_id": os.environ.get("SLURM_STEP_ID", ""),
            "slurm_partition": os.environ.get("SLURM_JOB_PARTITION", ""),
        },
        "git": {
            "head": git_output(root, ["rev-parse", "HEAD"]),
            "branch": git_output(root, ["branch", "--show-current"]),
        },
        "init_error": init_error,
    }
    write_json(variant_root / "preflight_receipt.json", contract)
    write_json(result_root / "nnunet_decoder_reset_contract_v2.json", contract)

    command = " ".join(sys.argv)
    append_gpu_manifest(
        result_root,
        {
            "timestamp_utc": utc_now(),
            "logical_run_id": run_id,
            "variant": variant,
            "status": "PREFLIGHT_READY" if args.action == "preflight" else "RUNNING",
            "job_id": os.environ.get("SLURM_JOB_ID", ""),
            "partition": os.environ.get("SLURM_JOB_PARTITION", ""),
            "node": socket.gethostname(),
            "gpu": contract["environment"]["cuda_device_name"],
            "python": sys.executable,
            "torch": torch.__version__,
            "cuda": contract["environment"]["cuda_version"],
            "repo_sha": contract["git"]["head"],
            "task_sha": args.task_sha or "",
            "config_sha": sha256_file(plans_path),
            "split_sha": split_contract["actual_train_sha256"] + ":" + split_contract["inner_select_sha256"],
            "checkpoint_sha": sha256_file(checkpoint_path),
            "command": command,
            "output_path": str(variant_root),
        },
    )
    update_task_status(result_root, variant, "PREFLIGHT_READY", str(variant_root / "preflight_receipt.json"))

    if args.action == "preflight":
        print(json.dumps(contract, indent=2, sort_keys=True, default=json_default))
        return 0

    if int(spec.get("diagnostic_train_epochs", spec["epochs"])) > 0:
        trainer.run_training()
    validation_ran = False
    if spec["validate_after"]:
        trainer.perform_actual_validation(save_probabilities=args.save_probabilities)
        validation_ran = True

    final_receipt = dict(contract)
    final_receipt.update(
        {
            "completed_at_utc": utc_now(),
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "validation_ran": validation_ran,
            "final_checkpoint": str(Path(trainer.output_folder) / "checkpoint_final.pth"),
            "best_checkpoint": str(Path(trainer.output_folder) / "checkpoint_best.pth"),
            "validation_folder": str(Path(trainer.output_folder) / "validation"),
        }
    )
    write_json(variant_root / "completion_receipt.json", final_receipt)
    append_gpu_manifest(
        result_root,
        {
            "timestamp_utc": utc_now(),
            "logical_run_id": run_id,
            "variant": variant,
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "job_id": os.environ.get("SLURM_JOB_ID", ""),
            "partition": os.environ.get("SLURM_JOB_PARTITION", ""),
            "node": socket.gethostname(),
            "gpu": contract["environment"]["cuda_device_name"],
            "python": sys.executable,
            "torch": torch.__version__,
            "cuda": contract["environment"]["cuda_version"],
            "repo_sha": contract["git"]["head"],
            "task_sha": args.task_sha or "",
            "config_sha": sha256_file(plans_path),
            "split_sha": split_contract["actual_train_sha256"] + ":" + split_contract["inner_select_sha256"],
            "checkpoint_sha": sha256_file(checkpoint_path),
            "command": command,
            "output_path": str(variant_root),
        },
    )
    update_task_status(result_root, variant, "RUNNING_PARTIAL_VARIANT_COMPLETED", str(variant_root / "completion_receipt.json"))
    print(json.dumps(final_receipt, indent=2, sort_keys=True, default=json_default))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="/users/a/e/aereinh/CARE")
    parser.add_argument("--variant", required=True, choices=sorted(VARIANT_SPECS))
    parser.add_argument("--action", choices=["preflight", "run"], default="preflight")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--task-sha", default="")
    parser.add_argument("--save-probabilities", action="store_true")
    parser.add_argument("--micro-debug", action="store_true", help="Use the 12 inner_select cases as train too; never for final evidence.")
    parser.add_argument("--cpu", action="store_true", help="CPU only smoke mode; never satisfies GPU task evidence.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
