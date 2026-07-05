#!/usr/bin/env python3
"""Export SRR-v3 M1 eval-only runtime instrumentation from existing checkpoints."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.export_srr_v25_full_fold0_metrics import checkpoint_args  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    _decode_argmax,
    _decode_pathology_aware,
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    load_myops_case_metadata,
    parse_shape,
    propref_loss,
    read_anchored_case,
    sample_patch_with_anchor,
)
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402


DEFAULT_MATRIX_ROOT = REPO_ROOT / "results/20260704_srr_v25_training_ablation_matrix/bounded_matrix"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results/20260705_srr_v3_m1_runtime_instrumentation_gate"
DEFAULT_CASE_IDS = "Case1002,Case2002,Case3004,Case3011"
CSV_NAMES = (
    "gate_residual_export.csv",
    "prototype_coverage_export.csv",
    "anchor_context_alignment_export.csv",
    "no_t2_safety_export.csv",
)
THRESHOLDS = (0.01, 0.05, 0.10, 0.25, 0.50)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_case_ids(text: str) -> list[str]:
    return [item.strip() for item in text.replace(";", ",").split(",") if item.strip()]


def tensor_stats(values: torch.Tensor) -> dict[str, float]:
    flat = values.detach().float().flatten().cpu()
    if flat.numel() == 0:
        return {"mean": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "mean": float(flat.mean().item()),
        "p95": float(torch.quantile(flat, 0.95).item()),
        "max": float(flat.max().item()),
    }


def gate_open_rates(gate: torch.Tensor) -> dict[str, float]:
    flat = gate.detach().float().flatten().cpu()
    return {f"gate_open_rate_ge_{threshold:.2f}": float((flat >= threshold).float().mean().item()) for threshold in THRESHOLDS}


def class_channel(gate: torch.Tensor, class_id: int) -> torch.Tensor:
    if gate.shape[1] == 1:
        return gate[:, :1]
    return gate[:, class_id : class_id + 1]


def anchor_uncertainty(anchor_logits: torch.Tensor) -> dict[str, float]:
    prob = torch.softmax(anchor_logits, dim=1)
    conf = prob.max(dim=1).values
    entropy = -(prob.clamp_min(1e-6) * prob.clamp_min(1e-6).log()).sum(dim=1)
    return {
        "anchor_confidence_mean": float(conf.detach().mean().cpu().item()),
        "anchor_confidence_p05": float(torch.quantile(conf.detach().flatten().cpu(), 0.05).item()),
        "anchor_entropy_mean": float(entropy.detach().mean().cpu().item()),
        "anchor_entropy_p95": float(torch.quantile(entropy.detach().flatten().cpu(), 0.95).item()),
    }


def source_summary_row(variant: str, source_summary: dict[str, object], checkpoint_path: Path) -> dict[str, object]:
    proto = source_summary.get("prototype_bank_summary", {})
    if not isinstance(proto, dict):
        proto = {}
    counts = proto.get("counts", {})
    if not isinstance(counts, dict):
        counts = {}
    categories = proto.get("category_counts", {})
    if not isinstance(categories, dict):
        categories = {}
    selected = proto.get("selected_case_ids", [])
    if not isinstance(selected, list):
        selected = []
    return {
        "variant": variant,
        "source": str(source_summary.get("prototype_bank_summary_path", "")),
        "checkpoint_path": str(checkpoint_path),
        "actual_optimizer_steps": source_summary.get("actual_optimizer_steps", ""),
        "train_cases": source_summary.get("train_cases", ""),
        "eval_cases": source_summary.get("eval_cases", ""),
        "prototype_case_count": proto.get("case_count", ""),
        "selected_case_ids": ";".join(str(item) for item in selected),
        "scar_positive": counts.get("scar_positive", ""),
        "scar_negative": counts.get("scar_negative", ""),
        "edema_positive": counts.get("edema_positive", ""),
        "edema_negative": counts.get("edema_negative", ""),
        "t2_present_edema_positive": categories.get("t2_present_edema_positive", ""),
        "t2_present_normal_myocardium_far_from_edema": categories.get("t2_present_normal_myocardium_far_from_edema", ""),
        "edema_no_t2_myocardium_negative_voxels": (proto.get("hard_negative_counts", {}) or {}).get("edema_no_t2_myocardium_negative_voxels", "")
        if isinstance(proto.get("hard_negative_counts", {}), dict)
        else "",
        "coverage_status": "EDEMA_PROTOTYPES_EMPTY" if int(counts.get("edema_positive", 0) or 0) == 0 or int(counts.get("edema_negative", 0) or 0) == 0 else "PRESENT",
        "evidence_status": "source_summary_runtime_json",
    }


def load_model(variant: str, matrix_root: Path, checkpoint_name: str, device: torch.device) -> tuple[SRRProposeRefineMyoPS, SimpleNamespace, dict[str, object], Path]:
    src_dir = matrix_root / "variants" / variant
    source_summary = read_json(src_dir / "summary.json")
    checkpoint_path = src_dir / "checkpoints/fold_0/propref_config" / f"{checkpoint_name}.pt"
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    run_args = checkpoint_args(checkpoint, source_summary)
    model = SRRProposeRefineMyoPS(
        base_channels=int(run_args.base_channels),
        variant=str(run_args.variant),
        encoder_profile=str(run_args.encoder_profile),
        disable_local_refinement=bool(getattr(run_args, "disable_local_refinement", False)),
        disable_anatomy_roi_prior=bool(getattr(run_args, "disable_anatomy_roi_prior", False)),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, run_args, source_summary, checkpoint_path


def export_variant(args: argparse.Namespace) -> dict[str, object]:
    matrix_root = resolve(args.matrix_root)
    output_dir = resolve(args.output_dir)
    anchor_root = resolve(args.nnunet_anchor_root)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model, run_args, source_summary, checkpoint_path = load_model(args.variant, matrix_root, args.checkpoint_name, device)
    metadata = load_myops_case_metadata()
    case_ids = parse_case_ids(args.case_ids)
    cases = [read_anchored_case(case_id, metadata, anchor_root) for case_id in case_ids]
    patch_shape = parse_shape(str(args.patch_shape))
    rng = np.random.default_rng(int(args.seed))

    gate_rows: list[dict[str, object]] = []
    align_rows: list[dict[str, object]] = []
    no_t2_rows: list[dict[str, object]] = []
    proto_rows = [source_summary_row(args.variant, source_summary, checkpoint_path)]

    for case in cases:
        focus = (4,) if bool(case.metadata.t2_present) and np.any(case.label_arr == 4) else (5, 4)
        x_np, y_np, av_np, anchor_np, component_np = sample_patch_with_anchor(
            case,
            patch_shape,
            rng,
            oversample_foreground=float(args.oversample_foreground),
            modality_dropout=False,
            focus_classes=focus,
        )
        x = torch.from_numpy(x_np[None]).float().to(device)
        y = torch.from_numpy(y_np[None]).long().to(device)
        av = torch.from_numpy(av_np[None]).float().to(device)
        anchor_t = torch.from_numpy(anchor_np[None]).float().to(device)
        component_t = torch.from_numpy(component_np[None]).float().to(device)
        anchor_features = anchor_dict_from_tensor(anchor_t)
        component_features = component_dict_from_tensor(component_t)
        disable_anchor = bool(getattr(run_args, "disable_nnunet_anchor", False))
        with torch.no_grad():
            outputs = model(
                x,
                av,
                anchor_features=None if disable_anchor else anchor_features,
                component_features=None if disable_anchor else component_features,
            )
            loss, loss_metrics = propref_loss(outputs, y, av, "soft_roi_refinement", run_args)
            argmax_pred = _decode_argmax(outputs)
            aware_pred = _decode_pathology_aware(
                outputs,
                scar_threshold=float(getattr(run_args, "scar_decode_threshold", 0.5)),
                edema_threshold=float(getattr(run_args, "edema_decode_threshold", 0.5)),
            )
        gate = outputs["baseline_residual_gate"].detach()
        delta = outputs["bounded_delta_srr"].detach()
        correction = (gate * delta).detach()
        anchor_logits = outputs["nnunet_anchor_logits"].detach()
        anchor_pred = torch.argmax(anchor_logits, dim=1)
        final_pred = argmax_pred.detach()
        aware_pred = aware_pred.detach()
        uncertainty = anchor_uncertainty(anchor_logits)
        gate_status = str(outputs.get("baseline_gate_status", ""))
        for class_id, metric_name in ((4, "myops_edema"), (5, "myops_scar")):
            class_gate = class_channel(gate, class_id)
            class_delta_abs = delta[:, class_id : class_id + 1].abs()
            class_correction_abs = correction[:, class_id : class_id + 1].abs()
            row = {
                "variant": args.variant,
                "checkpoint_name": args.checkpoint_name,
                "case_id": case.case_id,
                "sample_scope": "single_seeded_validation_patch",
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": bool(case.metadata.t2_present),
                "class_id": class_id,
                "metric_name": metric_name,
                "gate_status": gate_status,
                "baseline_residual_gate_mean": tensor_stats(class_gate)["mean"],
                "baseline_residual_gate_p95": tensor_stats(class_gate)["p95"],
                **gate_open_rates(class_gate),
                "bounded_delta_abs_mean": tensor_stats(class_delta_abs)["mean"],
                "bounded_delta_abs_p95": tensor_stats(class_delta_abs)["p95"],
                "bounded_delta_abs_max": tensor_stats(class_delta_abs)["max"],
                "correction_abs_mean": tensor_stats(class_correction_abs)["mean"],
                "correction_abs_p95": tensor_stats(class_correction_abs)["p95"],
                "correction_abs_max": tensor_stats(class_correction_abs)["max"],
                "decode_argmax_delta_voxels_vs_anchor": int(((final_pred == class_id) != (anchor_pred == class_id)).sum().detach().cpu().item()),
                "decode_pathology_aware_delta_voxels_vs_anchor": int(((aware_pred == class_id) != (anchor_pred == class_id)).sum().detach().cpu().item()),
                "anchor_class_voxels": int((anchor_pred == class_id).sum().detach().cpu().item()),
                "argmax_class_voxels": int((final_pred == class_id).sum().detach().cpu().item()),
                "pathology_aware_class_voxels": int((aware_pred == class_id).sum().detach().cpu().item()),
                "evidence_status": "runtime_instrumented",
                **uncertainty,
            }
            gate_rows.append(row)
        align_rows.append(
            {
                "variant": args.variant,
                "checkpoint_name": args.checkpoint_name,
                "case_id": case.case_id,
                "sample_scope": "single_seeded_validation_patch",
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": bool(case.metadata.t2_present),
                "image_shape": "x".join(str(v) for v in x_np.shape),
                "label_shape": "x".join(str(v) for v in y_np.shape),
                "availability": ";".join(str(float(v)) for v in av_np.tolist()),
                "anchor_shape": "x".join(str(v) for v in anchor_np.shape),
                "component_shape": "x".join(str(v) for v in component_np.shape),
                "output_logits_shape": "x".join(str(v) for v in outputs["logits"].shape),
                "anchor_logits_shape": "x".join(str(v) for v in anchor_logits.shape),
                "gate_shape": "x".join(str(v) for v in gate.shape),
                "bounded_delta_shape": "x".join(str(v) for v in delta.shape),
                "anchor_present": bool(anchor_np.any()) and not disable_anchor,
                "component_present": bool(component_np.any()) and not disable_anchor,
                "anchor_source": case.anchor_source,
                "anchor_fold": case.anchor_fold,
                "shape_alignment_status": "PASS" if tuple(outputs["logits"].shape[-3:]) == tuple(y_np.shape) and tuple(anchor_logits.shape[-3:]) == tuple(y_np.shape) else "FAIL",
                "evidence_status": "runtime_instrumented",
            }
        )
        no_t2_mask = not bool(case.metadata.t2_present)
        no_t2_rows.append(
            {
                "variant": args.variant,
                "checkpoint_name": args.checkpoint_name,
                "case_id": case.case_id,
                "sample_scope": "single_seeded_validation_patch",
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": bool(case.metadata.t2_present),
                "no_t2_case": no_t2_mask,
                "edema_logit_max": float(outputs["edema_logits"][:, 0].detach().max().cpu().item()),
                "final_edema_logit_max": float(outputs["logits"][:, 4].detach().max().cpu().item()),
                "argmax_edema_voxels": int((final_pred == 4).sum().detach().cpu().item()),
                "pathology_aware_edema_voxels": int((aware_pred == 4).sum().detach().cpu().item()),
                "loss_value": float(loss.detach().cpu().item()),
                "edema_proposal_loss": float(loss_metrics["edema_proposal_loss"].detach().cpu().item()),
                "final_loss": float(loss_metrics["final_loss"].detach().cpu().item()),
                "no_t2_logit_guard_status": "PASS" if no_t2_mask and float(outputs["edema_logits"][:, 0].detach().max().cpu().item()) <= -19.0 else ("NOT_APPLICABLE_T2_PRESENT" if not no_t2_mask else "FAIL"),
                "no_t2_decode_guard_status": "PASS" if no_t2_mask and int((aware_pred == 4).sum().detach().cpu().item()) == 0 else ("NOT_APPLICABLE_T2_PRESENT" if not no_t2_mask else "FAIL"),
                "loss_path_status": "runtime_loss_evaluated_soft_roi_refinement",
                "evidence_status": "runtime_instrumented",
            }
        )

    for class_id, metric_name in ((4, "myops_edema"), (5, "myops_scar")):
        subset = [row for row in gate_rows if int(row["class_id"]) == class_id]
        if subset:
            gate_rows.append(
                {
                    "variant": args.variant,
                    "checkpoint_name": args.checkpoint_name,
                    "case_id": "AGGREGATE",
                    "sample_scope": "single_seeded_validation_patch",
                    "center": "ALL",
                    "modality_group": "ALL",
                    "t2_present": "MIXED",
                    "class_id": class_id,
                    "metric_name": metric_name,
                    "gate_status": subset[0]["gate_status"],
                    "baseline_residual_gate_mean": float(np.mean([float(row["baseline_residual_gate_mean"]) for row in subset])),
                    "baseline_residual_gate_p95": float(np.mean([float(row["baseline_residual_gate_p95"]) for row in subset])),
                    "gate_open_rate_ge_0.01": float(np.mean([float(row["gate_open_rate_ge_0.01"]) for row in subset])),
                    "gate_open_rate_ge_0.05": float(np.mean([float(row["gate_open_rate_ge_0.05"]) for row in subset])),
                    "gate_open_rate_ge_0.10": float(np.mean([float(row["gate_open_rate_ge_0.10"]) for row in subset])),
                    "gate_open_rate_ge_0.25": float(np.mean([float(row["gate_open_rate_ge_0.25"]) for row in subset])),
                    "gate_open_rate_ge_0.50": float(np.mean([float(row["gate_open_rate_ge_0.50"]) for row in subset])),
                    "bounded_delta_abs_mean": float(np.mean([float(row["bounded_delta_abs_mean"]) for row in subset])),
                    "bounded_delta_abs_p95": float(np.mean([float(row["bounded_delta_abs_p95"]) for row in subset])),
                    "bounded_delta_abs_max": float(np.max([float(row["bounded_delta_abs_max"]) for row in subset])),
                    "correction_abs_mean": float(np.mean([float(row["correction_abs_mean"]) for row in subset])),
                    "correction_abs_p95": float(np.mean([float(row["correction_abs_p95"]) for row in subset])),
                    "correction_abs_max": float(np.max([float(row["correction_abs_max"]) for row in subset])),
                    "decode_argmax_delta_voxels_vs_anchor": int(sum(int(row["decode_argmax_delta_voxels_vs_anchor"]) for row in subset)),
                    "decode_pathology_aware_delta_voxels_vs_anchor": int(sum(int(row["decode_pathology_aware_delta_voxels_vs_anchor"]) for row in subset)),
                    "anchor_class_voxels": int(sum(int(row["anchor_class_voxels"]) for row in subset)),
                    "argmax_class_voxels": int(sum(int(row["argmax_class_voxels"]) for row in subset)),
                    "pathology_aware_class_voxels": int(sum(int(row["pathology_aware_class_voxels"]) for row in subset)),
                    "anchor_confidence_mean": float(np.mean([float(row["anchor_confidence_mean"]) for row in subset])),
                    "anchor_confidence_p05": float(np.mean([float(row["anchor_confidence_p05"]) for row in subset])),
                    "anchor_entropy_mean": float(np.mean([float(row["anchor_entropy_mean"]) for row in subset])),
                    "anchor_entropy_p95": float(np.mean([float(row["anchor_entropy_p95"]) for row in subset])),
                    "evidence_status": "runtime_instrumented_aggregate",
                }
            )

    write_csv(output_dir / "gate_residual_export.csv", gate_rows, GATE_FIELDS)
    write_csv(output_dir / "prototype_coverage_export.csv", proto_rows, PROTO_FIELDS)
    write_csv(output_dir / "anchor_context_alignment_export.csv", align_rows, ALIGN_FIELDS)
    write_csv(output_dir / "no_t2_safety_export.csv", no_t2_rows, NO_T2_FIELDS)
    return {
        "variant": args.variant,
        "checkpoint": str(checkpoint_path),
        "output_dir": str(output_dir),
        "case_ids": case_ids,
        "device": str(device),
        "gate_rows": len(gate_rows),
        "alignment_rows": len(align_rows),
        "no_t2_rows": len(no_t2_rows),
        "prototype_rows": len(proto_rows),
    }


GATE_FIELDS = [
    "variant",
    "checkpoint_name",
    "case_id",
    "sample_scope",
    "center",
    "modality_group",
    "t2_present",
    "class_id",
    "metric_name",
    "gate_status",
    "baseline_residual_gate_mean",
    "baseline_residual_gate_p95",
    "gate_open_rate_ge_0.01",
    "gate_open_rate_ge_0.05",
    "gate_open_rate_ge_0.10",
    "gate_open_rate_ge_0.25",
    "gate_open_rate_ge_0.50",
    "bounded_delta_abs_mean",
    "bounded_delta_abs_p95",
    "bounded_delta_abs_max",
    "correction_abs_mean",
    "correction_abs_p95",
    "correction_abs_max",
    "decode_argmax_delta_voxels_vs_anchor",
    "decode_pathology_aware_delta_voxels_vs_anchor",
    "anchor_class_voxels",
    "argmax_class_voxels",
    "pathology_aware_class_voxels",
    "anchor_confidence_mean",
    "anchor_confidence_p05",
    "anchor_entropy_mean",
    "anchor_entropy_p95",
    "evidence_status",
]

PROTO_FIELDS = [
    "variant",
    "source",
    "checkpoint_path",
    "actual_optimizer_steps",
    "train_cases",
    "eval_cases",
    "prototype_case_count",
    "selected_case_ids",
    "scar_positive",
    "scar_negative",
    "edema_positive",
    "edema_negative",
    "t2_present_edema_positive",
    "t2_present_normal_myocardium_far_from_edema",
    "edema_no_t2_myocardium_negative_voxels",
    "coverage_status",
    "evidence_status",
]

ALIGN_FIELDS = [
    "variant",
    "checkpoint_name",
    "case_id",
    "sample_scope",
    "center",
    "modality_group",
    "t2_present",
    "image_shape",
    "label_shape",
    "availability",
    "anchor_shape",
    "component_shape",
    "output_logits_shape",
    "anchor_logits_shape",
    "gate_shape",
    "bounded_delta_shape",
    "anchor_present",
    "component_present",
    "anchor_source",
    "anchor_fold",
    "shape_alignment_status",
    "evidence_status",
]

NO_T2_FIELDS = [
    "variant",
    "checkpoint_name",
    "case_id",
    "sample_scope",
    "center",
    "modality_group",
    "t2_present",
    "no_t2_case",
    "edema_logit_max",
    "final_edema_logit_max",
    "argmax_edema_voxels",
    "pathology_aware_edema_voxels",
    "loss_value",
    "edema_proposal_loss",
    "final_loss",
    "no_t2_logit_guard_status",
    "no_t2_decode_guard_status",
    "loss_path_status",
    "evidence_status",
]


def validate_packet(output_dir: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for name in CSV_NAMES:
        path = output_dir / name
        if not path.is_file():
            issues.append(f"{name}: missing")
            continue
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not reader.fieldnames:
                issues.append(f"{name}: empty_header")
            if not rows:
                issues.append(f"{name}: no_rows")
            if rows and all(str(row.get("evidence_status", "")).startswith("CLAIM") for row in rows):
                issues.append(f"{name}: claim_only_rows")
    gate_path = output_dir / "gate_residual_export.csv"
    if gate_path.is_file():
        with gate_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not any("runtime_instrumented" in str(row.get("evidence_status", "")) and row.get("case_id") != "EVIDENCE_NOT_FOUND" for row in rows):
            issues.append("gate_residual_export.csv: no_runtime_instrumented_row")
    proto_path = output_dir / "prototype_coverage_export.csv"
    if proto_path.is_file():
        with proto_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows and any(str(row.get("coverage_status")) == "EDEMA_PROTOTYPES_EMPTY" for row in rows):
            issues.append("prototype_coverage_export.csv: edema_prototypes_empty")
    return not issues, issues


def run_known_bad_validator(output_dir: Path) -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="srr_m1_bad_") as tmp:
        tmpdir = Path(tmp)
        for name in CSV_NAMES:
            (tmpdir / name).write_text("case_id,evidence_status\nCLAIM_ONLY,CLAIM_WITHOUT_RUNTIME_EVIDENCE\n", encoding="utf-8")
        passed, issues = validate_packet(tmpdir)
    if passed:
        return False, ["known_bad_packet_unexpectedly_passed"]
    return True, [f"known_bad_failed_closed:{';'.join(issues)}"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-root", type=Path, default=DEFAULT_MATRIX_ROOT)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--variant", default="srr_propref_shared_dual_dict")
    ap.add_argument("--checkpoint-name", default="checkpoint_final")
    ap.add_argument("--case-ids", default=DEFAULT_CASE_IDS)
    ap.add_argument("--patch-shape", default="12,96,96")
    ap.add_argument("--oversample-foreground", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20260705)
    ap.add_argument("--device", choices=["cuda", "cpu"], default="cpu")
    ap.add_argument("--nnunet-anchor-root", type=Path, default=DEFAULT_NNUNET_ANCHOR_ROOT)
    ap.add_argument("--strict-validate", action="store_true")
    ap.add_argument("--known-bad-validator-smoke", action="store_true")
    args = ap.parse_args()

    output_dir = resolve(args.output_dir)
    if args.known_bad_validator_smoke:
        passed, issues = run_known_bad_validator(output_dir)
        print(json.dumps({"known_bad_validator_smoke_passed": passed, "issues": issues}, indent=2, sort_keys=True))
        return 0 if passed else 1
    if args.strict_validate:
        passed, issues = validate_packet(output_dir)
        print(json.dumps({"strict_validate_passed": passed, "issues": issues}, indent=2, sort_keys=True))
        return 0 if passed else 1
    summary = export_variant(args)
    (output_dir / "runtime_instrumentation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
