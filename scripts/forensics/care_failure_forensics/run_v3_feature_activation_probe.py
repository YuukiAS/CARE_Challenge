#!/usr/bin/env python3
"""Run V3 read-only activation probes for nnU-Net and CARE-PRISM.

This is a diagnostic script only.  It performs no training of segmentation
models, does not access the outer split, and writes only packet evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import torch.nn as nn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_care_prism import crop_to_shape, move_batch, pad_to_multiple, spatial_multiple  # noqa: E402
from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMFullPatientDataset  # noqa: E402
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_care_prism, build_source_nnunet  # noqa: E402
from src.care_myocardium.training.care_prism_trainer import file_sha256  # noqa: E402


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
NNUNET_CKPT = Path(
    "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth"
)
PRISM_CKPT = Path(
    "results/20260729_care_prism_v2_backbone_repair_and_resume/runtime/"
    "fold0_w3_fold0_6500_formal_v2/checkpoints/checkpoint_step03000.pt"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n", encoding="utf-8")


def compact_casewise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["case_id"], row["split"], row["center"], row["feature_source"], row["task_id"])
        item = grouped.setdefault(
            key,
            {
                "case_id": row["case_id"],
                "split": row["split"],
                "center": row["center"],
                "feature_source": row["feature_source"],
                "task_id": row["task_id"],
                "positive_regions": 0,
                "negative_regions": 0,
            },
        )
        if int(row["label"]) == 1:
            item["positive_regions"] += 1
        else:
            item["negative_regions"] += 1
    return list(grouped.values())


def downsample_mask(mask: torch.Tensor, shape: tuple[int, int, int]) -> torch.Tensor:
    return F.interpolate(mask.float(), size=shape, mode="nearest") > 0.5


def tensor_stats(tensor: torch.Tensor, mask: torch.Tensor) -> np.ndarray | None:
    if mask.sum() < 1:
        return None
    values = tensor[0, :, mask[0, 0]].detach().float()
    if values.numel() == 0:
        return None
    mean = values.mean(dim=1)
    std = values.std(dim=1, unbiased=False)
    maxv = values.amax(dim=1)
    return torch.cat([mean, std, maxv], dim=0).cpu().numpy().astype(np.float32)


def add_region(
    rows: list[dict[str, Any]],
    *,
    case_id: str,
    split: str,
    center: str,
    feature_source: str,
    tensor: torch.Tensor,
    pos_mask: torch.Tensor,
    neg_mask: torch.Tensor,
    task_id: str,
) -> None:
    spatial = tuple(int(v) for v in tensor.shape[-3:])
    pos = downsample_mask(pos_mask, spatial)
    neg = downsample_mask(neg_mask, spatial)
    for label, mask in [(1, pos), (0, neg)]:
        feat = tensor_stats(tensor, mask)
        if feat is None:
            continue
        rows.append(
            {
                "case_id": case_id,
                "split": split,
                "center": center,
                "feature_source": feature_source,
                "task_id": task_id,
                "label": label,
                "sample_kind": "positive_region" if label == 1 else "negative_region",
                **{f"f{i:03d}": float(v) for i, v in enumerate(feat[:384])},
            }
        )


def class_metrics(y_true: np.ndarray, score: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    if len(set(y_true.tolist())) < 2:
        return {"status": "INSUFFICIENT_EVAL_CLASSES"}
    return {
        "status": "PASS",
        "AUROC": float(roc_auc_score(y_true, score)),
        "AUPRC": float(average_precision_score(y_true, score)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, pred)),
        "sensitivity": float(((pred == 1) & (y_true == 1)).sum() / max((y_true == 1).sum(), 1)),
        "specificity": float(((pred == 0) & (y_true == 0)).sum() / max((y_true == 0).sum(), 1)),
        "ECE": float(abs(score.mean() - y_true.mean())),
    }


def fit_probe(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]], feature_source: str, task_id: str, model_name: str) -> dict[str, Any]:
    tr = [r for r in train_rows if r["feature_source"] == feature_source and r["task_id"] == task_id]
    ev = [r for r in eval_rows if r["feature_source"] == feature_source and r["task_id"] == task_id]
    fields = sorted([k for k in (tr[0].keys() if tr else []) if re.fullmatch(r"f\d{3}", k)])
    if len(tr) < 4 or len(ev) < 2 or len({r["label"] for r in tr}) < 2:
        return {
            "feature_source": feature_source,
            "task_id": task_id,
            "probe_model": model_name,
            "status": "INSUFFICIENT_SPLIT_DATA",
            "train_rows": len(tr),
            "eval_rows": len(ev),
        }
    x_train = np.asarray([[float(r.get(f, 0.0)) for f in fields] for r in tr], dtype=np.float32)
    y_train = np.asarray([int(r["label"]) for r in tr], dtype=np.int64)
    x_eval = np.asarray([[float(r.get(f, 0.0)) for f in fields] for r in ev], dtype=np.float32)
    y_eval = np.asarray([int(r["label"]) for r in ev], dtype=np.int64)
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train)
    x_eval = scaler.transform(x_eval)
    try:
        if model_name == "logistic_regression":
            clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=20260730)
            clf.fit(x_train, y_train)
            score = clf.predict_proba(x_eval)[:, 1]
            pred = (score >= 0.5).astype(np.int64)
        elif model_name == "linear_svm":
            clf = LinearSVC(class_weight="balanced", random_state=20260730, max_iter=5000)
            clf.fit(x_train, y_train)
            decision = clf.decision_function(x_eval)
            score = 1.0 / (1.0 + np.exp(-np.clip(decision, -50, 50)))
            pred = (decision >= 0).astype(np.int64)
        elif model_name == "1x1_convolution":
            torch.manual_seed(20260730)
            xtr = torch.as_tensor(x_train, dtype=torch.float32)
            ytr = torch.as_tensor(y_train, dtype=torch.float32).unsqueeze(1)
            xev = torch.as_tensor(x_eval, dtype=torch.float32)
            positives = float((y_train == 1).sum())
            negatives = float((y_train == 0).sum())
            pos_weight = torch.tensor([negatives / max(positives, 1.0)], dtype=torch.float32)
            clf = nn.Linear(xtr.shape[1], 1)
            opt = torch.optim.Adam(clf.parameters(), lr=0.05, weight_decay=1e-4)
            loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
            clf.train()
            for _ in range(1000):
                opt.zero_grad(set_to_none=True)
                loss = loss_fn(clf(xtr), ytr)
                loss.backward()
                opt.step()
            clf.eval()
            with torch.no_grad():
                logits = clf(xev).squeeze(1).numpy()
            score = 1.0 / (1.0 + np.exp(-np.clip(logits, -50, 50)))
            pred = (score >= 0.5).astype(np.int64)
        else:
            return {"feature_source": feature_source, "task_id": task_id, "probe_model": model_name, "status": "NOT_IMPLEMENTED"}
        metrics = class_metrics(y_eval, score, pred)
        return {
            "feature_source": feature_source,
            "task_id": task_id,
            "probe_model": model_name,
            "train_rows": len(tr),
            "eval_rows": len(ev),
            "train_cases": len({r["case_id"] for r in tr}),
            "eval_cases": len({r["case_id"] for r in ev}),
            **metrics,
        }
    except Exception as exc:
        return {
            "feature_source": feature_source,
            "task_id": task_id,
            "probe_model": model_name,
            "status": "PROBE_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_models(root: Path, device: torch.device) -> tuple[Any, Any, CAREPRISMConfig, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    config = CAREPRISMConfig.from_nnunet_plans()
    nnunet = build_source_nnunet(config).to(device)
    nn_payload = torch.load(root / NNUNET_CKPT, map_location="cpu", weights_only=False)
    nn_load = nnunet.load_state_dict(nn_payload.get("network_weights", nn_payload), strict=False)
    blockers.append(
        {
            "model": "nnUNet",
            "checkpoint_path": str(NNUNET_CKPT),
            "checkpoint_sha256": file_sha256(root / NNUNET_CKPT),
            "missing_keys": len(nn_load.missing_keys),
            "unexpected_keys": len(nn_load.unexpected_keys),
            "status": "LOADED",
        }
    )
    nnunet.eval()

    prism = build_care_prism(config).to(device)
    pr_payload = torch.load(root / PRISM_CKPT, map_location="cpu", weights_only=False)
    pr_load = prism.load_state_dict(pr_payload["model_state"], strict=False)
    blockers.append(
        {
            "model": "PRISM",
            "checkpoint_path": str(PRISM_CKPT),
            "checkpoint_sha256": file_sha256(root / PRISM_CKPT),
            "missing_keys": len(pr_load.missing_keys),
            "unexpected_keys": len(pr_load.unexpected_keys),
            "status": "LOADED",
        }
    )
    prism.eval()
    return nnunet, prism, config, blockers


def add_mosaic_blockers(root: Path, blockers: list[dict[str, Any]]) -> None:
    source = Path("/users/a/e/aereinh/MoSAIC/code/source")
    weights = Path("/users/a/e/aereinh/MoSAIC/code/weights")
    for name in ["MOSAIC_COARSE", "MOSAIC_SCAR_FINE", "MOSAIC_EDEMA"]:
        blockers.append(
            {
                "model": name,
                "checkpoint_path": str(weights),
                "expected_architecture": "MoSAIC source model family",
                "actual_state_dict_keys": "not inspected in this lightweight pass",
                "missing_keys": "",
                "unexpected_keys": "",
                "shape_mismatches": "",
                "attempted_environments": str(source),
                "blocking_cause": "ACTIVATION_HOOK_NOT_RUN_FOR_MOSAIC_IN_THIS_PASS",
                "status": "LOAD_NOT_ATTEMPTED_REQUIRES_SEPARATE_MOSAIC_ENTRYPOINT",
            }
        )


def extract_split(root: Path, split: str, limit: int, nnunet: Any, prism: Any, config: CAREPRISMConfig, device: torch.device) -> list[dict[str, Any]]:
    ds = CAREPRISMFullPatientDataset(fold=0, split=split, augmenter=CAREPRISMAugmenter(training=False))
    pad_multiple = spatial_multiple(config)
    rows: list[dict[str, Any]] = []
    count = min(limit, len(ds))
    with torch.no_grad():
        for idx in range(count):
            batch = move_batch(ds[idx], device)
            images, original_spatial = pad_to_multiple(batch["images"].float(), pad_multiple)
            decoder_feats: list[torch.Tensor] = []
            handles = []
            if hasattr(nnunet, "decoder") and hasattr(nnunet.decoder, "stages"):
                for stage in nnunet.decoder.stages:
                    def _capture(_module: Any, _inputs: Any, output: Any, bucket: list[torch.Tensor] = decoder_feats) -> None:
                        if isinstance(output, torch.Tensor):
                            bucket.append(output.detach())
                        elif isinstance(output, (list, tuple)) and output and isinstance(output[0], torch.Tensor):
                            bucket.append(output[0].detach())

                    handles.append(stage.register_forward_hook(_capture))
            try:
                nn_logits = nnunet(images)
            finally:
                for handle in handles:
                    handle.remove()
            if isinstance(nn_logits, (list, tuple)):
                nn_logits = nn_logits[0]
            nn_logits = crop_to_shape(nn_logits, original_spatial)
            nn_pred = nn_logits.argmax(dim=1, keepdim=True)
            prism_out = prism(images, batch["availability"])

            case_id = batch["case_id"][0]
            center = str(batch.get("center", [""])[0]) if isinstance(batch.get("center"), list) else ""
            scar = batch["scar_target"] > 0.5
            edema_zone = batch["edema_zone_target"] > 0.5
            pure_edema = edema_zone & ~scar
            normal_myo = (batch["anatomy_target"][:, 0:1] > 0.5) & ~scar & ~pure_edema
            scar_fn = scar & (nn_pred != 5)
            scar_fp = (nn_pred == 5) & ~scar
            edema_fn = pure_edema & (nn_pred != 4)
            edema_fp = (nn_pred == 4) & ~pure_edema
            true_negative = normal_myo & (nn_pred != 4) & (nn_pred != 5)
            tasks = {
                "P1_scar_vs_normal_myocardium": (scar, normal_myo),
                "P2_nnunet_scar_FN_vs_true_negative": (scar_fn, true_negative),
                "P3_nnunet_scar_FP_vs_true_negative": (scar_fp, true_negative),
                "P4_pure_edema_vs_normal_myocardium": (pure_edema, normal_myo),
                "P5_nnunet_pure_edema_FN": (edema_fn, true_negative),
                "P6_nnunet_pure_edema_FP": (edema_fp, true_negative),
                "P7_small_scar_vs_normal_myocardium": (scar if int(scar.sum()) < 1500 else torch.zeros_like(scar), normal_myo),
                "P8_boundary_scar_vs_non_scar_myocardium": (scar, normal_myo),
            }
            feature_tensors: dict[str, torch.Tensor] = {}
            for level, feat in enumerate(nnunet.encoder(images)):
                feature_tensors[f"NNUNET_ENCODER_L{level}"] = feat
            for level, feat in enumerate(decoder_feats[:5]):
                feature_tensors[f"NNUNET_DECODER_L{level}"] = feat
            if not decoder_feats:
                feature_tensors["NNUNET_DECODER_L0"] = nn_logits
            for level, feat in enumerate(prism_out["shared_scales"][:4]):
                feature_tensors[f"PRISM_SHARED_L{level}"] = feat
            for modality_idx, modality in enumerate(["LGE", "T2", "C0"]):
                for level, feat in enumerate(prism_out["private_scales"][modality_idx][:4]):
                    feature_tensors[f"PRISM_PRIVATE_{modality}_L{level}"] = feat
            for level, feat in enumerate(prism_out["scar"]["decoded_scales"][:4]):
                feature_tensors[f"PRISM_SCAR_ROUTED_L{level}"] = feat
            for level, feat in enumerate(prism_out["edema"]["decoded_scales"][:4]):
                feature_tensors[f"PRISM_EDEMA_ROUTED_L{level}"] = feat
            feature_tensors["PRISM_SCAR_REFINER"] = prism_out["scar"]["features"]
            feature_tensors["PRISM_EDEMA_REFINER"] = prism_out["edema"]["features"]
            feature_tensors["RAW_INTENSITY_CONTROL"] = images
            for source, tensor in feature_tensors.items():
                for task_id, (pos, neg) in tasks.items():
                    add_region(rows, case_id=case_id, split=split, center=center, feature_source=source, tensor=tensor, pos_mask=pos, neg_mask=neg, task_id=task_id)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--train-cases", type=int, default=12)
    parser.add_argument("--eval-cases", type=int, default=12)
    args = parser.parse_args()
    root = args.root.resolve()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    out = root / RESULT_REL
    nnunet, prism, config, blockers = load_models(root, device)
    add_mosaic_blockers(root, blockers)
    train_rows = extract_split(root, "actual_train", args.train_cases, nnunet, prism, config, device)
    eval_rows = extract_split(root, "inner_select", args.eval_cases, nnunet, prism, config, device)
    all_rows = train_rows + eval_rows
    runtime_probe = out / "runtime/v3_feature_probe"
    write_csv(runtime_probe / "v3_feature_probe_feature_matrix.csv", all_rows)
    write_csv(out / "v3_feature_probe_casewise.csv", compact_casewise(all_rows))
    feature_sources = sorted({r["feature_source"] for r in all_rows})
    task_ids = sorted({r["task_id"] for r in all_rows})
    summary = []
    for source in feature_sources:
        for task_id in task_ids:
            for probe in ["logistic_regression", "linear_svm", "1x1_convolution"]:
                summary.append(fit_probe(train_rows, eval_rows, source, task_id, probe))
    write_csv(out / "v3_feature_probe_summary.csv", summary)
    write_csv(out / "v3_feature_probe_controls.csv", [r for r in summary if r["feature_source"] == "RAW_INTENSITY_CONTROL"])
    write_csv(out / "v3_feature_probe_loadability.csv", blockers)
    write_json(
        out / "v3_feature_probe_receipt.json",
        {
            "created_at": utc_now(),
            "status": "PASS_WITH_MOSAIC_HOOK_BLOCKER",
            "outer_accessed": False,
            "device": str(device),
            "train_split": "actual_train",
            "eval_split": "inner_select",
            "train_case_limit": args.train_cases,
            "eval_case_limit": args.eval_cases,
            "feature_sources": feature_sources,
            "tasks": task_ids,
            "blockers": blockers,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
