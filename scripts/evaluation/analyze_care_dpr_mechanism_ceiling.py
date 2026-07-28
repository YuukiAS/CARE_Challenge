#!/usr/bin/env python3
"""W0 mechanism ceiling analysis for CARE-DPR."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
from scipy import ndimage as ndi

from scripts.training.run_care_dg import CaseCache, PATCH_SHAPE, crop_pad, deterministic_inner_split, load_splits, move_tensors, sha256_file
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL
from src.care_myocardium.training.care_dg_trainer import load_care_dg_checkpoint

TASK_KEY = "20260728_care_dpr_fold0_global_redesign"
DEFAULT_RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
DEFAULT_CKPT = (
    REPO_ROOT
    / "results/20260727_care_dg_dual_pathology_validation/runtime/repaired_formal_scar_priority/fold0/checkpoints/checkpoint_step04000.pt"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set()
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aupr_score(scores: list[float], labels: list[int]) -> float:
    if not scores or sum(labels) == 0:
        return 0.0
    order = np.argsort(-np.asarray(scores, dtype=np.float64))
    y = np.asarray(labels, dtype=np.float64)[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1.0 - y)
    recall = tp / max(float(tp[-1]), 1.0)
    precision = tp / np.maximum(tp + fp, 1.0)
    recall = np.concatenate([[0.0], recall])
    precision = np.concatenate([[1.0], precision])
    return float(np.trapz(precision, recall))


def component_rows(mask: np.ndarray, *, max_components: int) -> list[tuple[int, np.ndarray]]:
    labeled, count = ndi.label(mask.astype(bool), structure=ndi.generate_binary_structure(3, 1))
    sizes = [(idx, int(np.count_nonzero(labeled == idx))) for idx in range(1, int(count) + 1)]
    sizes.sort(key=lambda item: item[1], reverse=True)
    return [(idx, labeled == idx) for idx, _ in sizes[:max_components]]


def center_of(mask: np.ndarray) -> tuple[int, int, int]:
    coords = np.argwhere(mask)
    return tuple(int(v) for v in np.round(coords.mean(axis=0)).astype(int))


def make_batch(record: dict[str, np.ndarray], center: tuple[int, int, int], availability: tuple[float, float, float], t2_present: bool) -> dict[str, Any]:
    return {
        "images": torch.from_numpy(crop_pad(record["images"], center, PATCH_SHAPE, fill=0.0)[None]).float(),
        "labels": torch.from_numpy(crop_pad(record["labels"][None], center, PATCH_SHAPE, fill=0)[None, 0]).long(),
        "anchor_logits": torch.from_numpy(crop_pad(record["anchor_logits"], center, PATCH_SHAPE, fill=-12.0)[None]).float(),
        "availability": torch.tensor([availability], dtype=torch.float32),
        "t2_present": torch.tensor([1.0 if t2_present else 0.0], dtype=torch.float32),
        "uncertainty": torch.from_numpy(crop_pad(record["uncertainty"], center, PATCH_SHAPE, fill=1.0)[None]).float(),
        "myocardium_support": torch.from_numpy(crop_pad(record["myocardium_support"], center, PATCH_SHAPE, fill=0.0)[None]).float(),
        "edema_support": torch.from_numpy(crop_pad(record["edema_support"], center, PATCH_SHAPE, fill=0.0)[None]).float(),
        "distance_to_myocardium": torch.from_numpy(crop_pad(record["distance_to_myocardium"], center, PATCH_SHAPE, fill=99.0)[None]).float(),
        "anchor_value_kind": "log_probabilities",
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    result_root = Path(args.result_root)
    result_root.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata()
    fold = load_splits()[args.fold]
    split = deterministic_inner_split(sorted(fold["train"]), args.fold, metadata)
    case_to_fold = {case_id: int(f["fold"]) for f in load_splits() for case_id in f["val"]}
    inner_cases = list(split["inner_select_cases"])
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model, step, extra = load_care_dg_checkpoint(Path(args.checkpoint))
    model.to(device).eval()
    cache = CaseCache(max_cases=args.cache_cases)
    rows: list[dict[str, Any]] = []
    score_bank: dict[str, dict[str, list[Any]]] = {
        "scar_fn": {"scores": [], "labels": []},
        "scar_fp": {"scores": [], "labels": []},
        "edema_fn": {"scores": [], "labels": []},
        "edema_fp": {"scores": [], "labels": []},
    }
    with torch.no_grad():
        for case_id in inner_cases:
            meta = metadata[case_id]
            rec = cache.get(case_id, case_to_fold[case_id], tuple(meta.availability))
            labels = rec["labels"]
            anchor = rec["anchor_mask"]
            masks = {
                "scar_fn": (labels == SCAR_CHANNEL) & (anchor != SCAR_CHANNEL),
                "scar_fp": (labels != SCAR_CHANNEL) & (anchor == SCAR_CHANNEL),
                "edema_fn": ((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)) & ~((anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)) if meta.t2_present else np.zeros_like(labels, dtype=bool),
                "edema_fp": ~((labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)) & ((anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)) if meta.t2_present else np.zeros_like(labels, dtype=bool),
            }
            for kind, mask in masks.items():
                pathology = "scar" if kind.startswith("scar") else "edema"
                q_key = "scar_q_fn" if kind == "scar_fn" else "scar_q_fp" if kind == "scar_fp" else "edema_q_fn" if kind == "edema_fn" else "edema_q_fp"
                for comp_idx, comp in component_rows(mask, max_components=args.max_components_per_kind):
                    center = center_of(comp)
                    batch = move_tensors(make_batch(rec, center, tuple(meta.availability), bool(meta.t2_present)), device)
                    out = model(
                        batch["images"],
                        batch["availability"],
                        batch["anchor_logits"],
                        uncertainty=batch["uncertainty"],
                        myocardium_support=batch["myocardium_support"],
                        edema_support=batch["edema_support"],
                        distance_to_myocardium=batch["distance_to_myocardium"],
                        t2_present=batch["t2_present"],
                        strict_inputs=True,
                        anchor_value_kind="log_probabilities",
                    )
                    local_comp = crop_pad(comp.astype(np.uint8)[None], center, PATCH_SHAPE, fill=0)[0].astype(bool)
                    q = out[q_key].detach().float().cpu().numpy()[0, 0]
                    final = out["final_mask"].detach().cpu().numpy()[0]
                    local_label = batch["labels"].cpu().numpy()[0]
                    local_anchor = batch["anchor_logits"].argmax(1).cpu().numpy()[0]
                    positive = local_comp
                    recalled = bool(q[positive].max(initial=0.0) >= float(args.recall_threshold)) if positive.any() else False
                    gt_error = int(np.count_nonzero(local_label[positive] != local_anchor[positive]))
                    realized_error = int(np.count_nonzero(local_label[positive] != final[positive]))
                    oracle_gain = gt_error
                    realized_gain = gt_error - realized_error
                    rows.append(
                        {
                            "case_id": case_id,
                            "pathology": pathology,
                            "error_kind": kind,
                            "component_index": comp_idx,
                            "component_voxels": int(np.count_nonzero(comp)),
                            "q_max": float(q[positive].max(initial=0.0)) if positive.any() else 0.0,
                            "component_recalled": int(recalled),
                            "oracle_component_acceptor_gain": int(oracle_gain),
                            "oracle_local_replacement_gain": int(oracle_gain),
                            "current_realized_gain": int(realized_gain),
                        }
                    )
                    flat_q = q.reshape(-1)
                    flat_target = local_comp.reshape(-1)
                    take = np.linspace(0, flat_q.size - 1, num=min(flat_q.size, args.aupr_voxels_per_component), dtype=np.int64)
                    score_bank[kind]["scores"].extend(flat_q[take].astype(float).tolist())
                    score_bank[kind]["labels"].extend(flat_target[take].astype(int).tolist())
    write_csv(result_root / "mechanism_ceiling_casewise.csv", rows)
    summary: dict[str, Any] = {
        "status": "PASS",
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256_file(Path(args.checkpoint)),
        "checkpoint_step": step,
        "analysis_population": "fixed_train_side_inner_cases_only",
        "outer_fold0_used": False,
        "inner_case_count": len(inner_cases),
        "inner_cases_sha256": hashlib.sha256("\n".join(sorted(inner_cases)).encode()).hexdigest(),
        "generated_at_utc": now_utc(),
    }
    for pathology in ("scar", "edema"):
        for kind in ("fn", "fp"):
            key = f"{pathology}_{kind}"
            subset = [r for r in rows if r["error_kind"] == key]
            denom = max(1, len(subset))
            summary[f"{key}_component_recall"] = float(sum(int(r["component_recalled"]) for r in subset) / denom)
            summary[f"{key}_q_aupr"] = aupr_score(score_bank[key]["scores"], score_bank[key]["labels"])
    summary["soft_roi_gt_coverage"] = float(np.mean([r["component_recalled"] for r in rows])) if rows else 0.0
    summary["oracle_component_acceptor_gain"] = int(sum(int(r["oracle_component_acceptor_gain"]) for r in rows))
    summary["oracle_local_replacement_gain"] = int(sum(int(r["oracle_local_replacement_gain"]) for r in rows))
    summary["current_realized_gain"] = int(sum(int(r["current_realized_gain"]) for r in rows))
    write_json(result_root / "mechanism_ceiling_summary.json", summary)
    limited = [
        k for k in ("scar_fn_component_recall", "scar_fp_component_recall", "edema_fn_component_recall", "edema_fp_component_recall")
        if float(summary.get(k, 0.0)) < 0.70
    ]
    classification = {
        "failure_classification": "PROPOSAL_LIMITED" if limited else "REFINEMENT_LIMITED",
        "limited_recall_fields": limited,
        "execution_failure": False,
        "architecture_ceiling_low": summary["oracle_local_replacement_gain"] < 1,
        "outer_fold0_used": False,
    }
    if classification["architecture_ceiling_low"]:
        classification["failure_classification"] = "ARCHITECTURE_CEILING_LOW"
    write_json(result_root / "failure_classification.json", classification)
    write_json(
        result_root / "frozen_input_contract.json",
        {
            "fold": args.fold,
            "train_side_inner_only": True,
            "outer_fold0_used_for_design_or_selection": False,
            "source_checkpoint": str(args.checkpoint),
            "source_checkpoint_sha256": summary["checkpoint_sha256"],
            "inner_cases_sha256": summary["inner_cases_sha256"],
        },
    )
    write_json(
        result_root / "controller_context.json",
        {
            "task_key": TASK_KEY,
            "phase": "W0_FORENSIC_CEILING",
            "git_head": hashlib.sha256((REPO_ROOT / "prompts/tasks/20260728_care_dpr_fold0_global_redesign_controller.md").read_bytes()).hexdigest(),
            "slurm_allocation_id": args.allocation_id,
            "outer_state_files_stale": ["prompts/routes/handoffs/CURRENT.md", "wiki/README.md"],
            "files_read": [
                "prompts/blueprints/CARE_DPR_dual_pathology_proposal_refine_arbitrate_20260728.md",
                "prompts/tasks/20260728_care_dpr_fold0_global_redesign_executor_plan.yaml",
            ],
        },
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--result-root", default=str(DEFAULT_RESULT_ROOT))
    parser.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    parser.add_argument("--allocation-id", default="60657290")
    parser.add_argument("--recall-threshold", type=float, default=0.5)
    parser.add_argument("--max-components-per-kind", type=int, default=40)
    parser.add_argument("--aupr-voxels-per-component", type=int, default=4096)
    parser.add_argument("--cache-cases", type=int, default=24)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    summary = analyze(args)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
