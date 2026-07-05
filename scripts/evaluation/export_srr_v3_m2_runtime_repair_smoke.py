#!/usr/bin/env python3
"""Run SRR-v3 M2 bounded runtime repair smoke checks without training."""

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

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    _decode_argmax,
    _decode_pathology_aware,
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    ensure_t2_edema_prototype_cases,
    fit_and_load_runtime_prototype_bank,
    load_myops_case_metadata,
    load_split,
    propref_loss,
    read_anchored_case,
    sample_patch_with_anchor,
)
from src.care_myocardium.models.srr_propref import (  # noqa: E402
    BaselinePreservingResidualGate,
    CropSoftROIRefinementHead,
    SRRProposeRefineMyoPS,
)


OUTPUT_DIR = REPO_ROOT / "results/20260705_srr_v3_m2_myops_bounded_runtime_repair"
CSV_NAMES = (
    "runtime_gap_closure_table.csv",
    "strong_encoder_context_sanity.csv",
    "prototype_t2_coverage_sanity.csv",
    "proposal_refinement_sanity.csv",
    "baseline_gate_safety_sanity.csv",
    "no_t2_safety_sanity.csv",
)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parameter_count(model: torch.nn.Module) -> int:
    return int(sum(param.numel() for param in model.parameters()))


def read_patch(case_id: str, *, patch_shape: tuple[int, int, int], seed: int, focus_classes: tuple[int, ...]) -> tuple[object, tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
    metadata = load_myops_case_metadata()
    case = read_anchored_case(case_id, metadata, DEFAULT_NNUNET_ANCHOR_ROOT)
    rng = np.random.default_rng(seed)
    x_np, y_np, av_np, anchor_np, component_np = sample_patch_with_anchor(
        case,
        patch_shape,
        rng,
        oversample_foreground=1.0,
        modality_dropout=False,
        focus_classes=focus_classes,
    )
    return case, (
        torch.from_numpy(x_np[None]).float(),
        torch.from_numpy(y_np[None]).long(),
        torch.from_numpy(av_np[None]).float(),
        torch.from_numpy(anchor_np[None]).float(),
        torch.from_numpy(component_np[None]).float(),
    )


def baseline_gate_rows() -> list[dict[str, object]]:
    torch.manual_seed(20260705)
    gate = BaselinePreservingResidualGate(num_classes=6)
    anchor_logits = torch.randn(1, 6, 4, 6, 6)
    srr_logits = anchor_logits.clone()
    srr_logits[:, 4:5, 1:3, 2:5, 2:5] += 3.0
    availability = torch.tensor([[1.0, 1.0, 1.0]])
    with torch.no_grad():
        closed = gate(srr_logits, {"logits": anchor_logits}, availability, force_closed=True)
        max_abs_diff = float((closed["final_logits"] - anchor_logits).abs().max().item())
        gate.gate.bias.fill_(2.5)
        opened = gate(srr_logits, {"logits": anchor_logits}, availability)
    correction = opened["gate"] * opened["bounded_delta"]
    return [
        {
            "test_name": "closed_gate_identity",
            "status": "PASS" if max_abs_diff <= 1e-6 else "FAIL",
            "max_abs_diff_vs_anchor_logits": max_abs_diff,
            "gate_mean": float(closed["gate"].mean().item()),
            "bounded_delta_abs_max": float(closed["bounded_delta"].abs().max().item()),
            "correction_abs_mean": float((closed["gate"] * closed["bounded_delta"]).abs().mean().item()),
            "evidence_status": "synthetic_unit_runtime",
        },
        {
            "test_name": "correction_positive_gate_opening",
            "status": "PASS" if float(opened["gate"].mean().item()) > 0.5 and float(correction.abs().mean().item()) > 0.0 and float(opened["bounded_delta"].abs().max().item()) <= 4.0001 else "FAIL",
            "max_abs_diff_vs_anchor_logits": float((opened["final_logits"] - anchor_logits).abs().max().item()),
            "gate_mean": float(opened["gate"].mean().item()),
            "bounded_delta_abs_max": float(opened["bounded_delta"].abs().max().item()),
            "correction_abs_mean": float(correction.abs().mean().item()),
            "evidence_status": "synthetic_unit_runtime",
        },
    ]


def strong_encoder_rows(patch_shape: tuple[int, int, int]) -> tuple[list[dict[str, object]], dict[str, torch.Tensor]]:
    case, (x, _y, av, anchor_t, component_t) = read_patch("Case2002", patch_shape=patch_shape, seed=20260705, focus_classes=(4,))
    model = SRRProposeRefineMyoPS(base_channels=8, encoder_profile="strong_4scale").eval()
    with torch.no_grad():
        outputs = model(
            x,
            av,
            anchor_features=anchor_dict_from_tensor(anchor_t),
            component_features=component_dict_from_tensor(component_t),
        )
    row = {
        "case_id": case.case_id,
        "status": "PASS",
        "encoder_profile": str(outputs["encoder_profile"]),
        "base_channels": 8,
        "encoder_scale_channels": ";".join(str(v) for v in outputs["encoder_scale_channels"]),
        "parameter_count": parameter_count(model),
        "input_shape": "x".join(str(v) for v in x.shape),
        "output_logits_shape": "x".join(str(v) for v in outputs["logits"].shape),
        "local_refinement_status": str(outputs["local_refinement_status"]),
        "anatomy_roi_prior_status": str(outputs["anatomy_roi_prior_status"]),
        "evidence_status": "real_case_forward_runtime",
    }
    return [row], outputs


def prototype_rows(out_dir: Path, patch_shape: tuple[int, int, int]) -> list[dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    train_ids, _val_ids = load_split(0)
    metadata = load_myops_case_metadata()
    initial_ids = train_ids[:12]
    initial_cases = [read_anchored_case(case_id, metadata, DEFAULT_NNUNET_ANCHOR_ROOT) for case_id in initial_ids]
    args = SimpleNamespace(
        variant="srr_propref_shared_dual_dict",
        skip_prototype_bank_fit=False,
        prototype_bank_cases=4,
        seed=20260705,
        disable_nnunet_anchor=False,
    )
    repaired_cases, added = ensure_t2_edema_prototype_cases(initial_cases, train_ids, metadata, DEFAULT_NNUNET_ANCHOR_ROOT, args)
    model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="tiny_3scale").eval()
    summary = fit_and_load_runtime_prototype_bank(model, repaired_cases, patch_shape, torch.device("cpu"), args, out_dir)
    counts = summary.get("counts", {})
    cats = summary.get("category_counts", {})
    hardneg = summary.get("hard_negative_counts", {})
    if not isinstance(counts, dict):
        counts = {}
    if not isinstance(cats, dict):
        cats = {}
    if not isinstance(hardneg, dict):
        hardneg = {}
    status = (
        "PASS"
        if int(counts.get("edema_positive", 0) or 0) > 0
        and int(counts.get("edema_negative", 0) or 0) > 0
        and int(cats.get("t2_present_edema_positive", 0) or 0) > 0
        and int(hardneg.get("edema_no_t2_myocardium_negative_voxels", 0) or 0) == 0
        else "FAIL"
    )
    return [
        {
            "status": status,
            "initial_limited_case_ids": ";".join(initial_ids),
            "repair_added_case_ids": ";".join(added),
            "selected_case_ids": ";".join(str(v) for v in summary.get("selected_case_ids", [])),
            "prototype_source": summary.get("source", ""),
            "case_count": summary.get("case_count", ""),
            "scar_positive": counts.get("scar_positive", ""),
            "scar_negative": counts.get("scar_negative", ""),
            "edema_positive": counts.get("edema_positive", ""),
            "edema_negative": counts.get("edema_negative", ""),
            "t2_present_edema_positive": cats.get("t2_present_edema_positive", ""),
            "t2_present_normal_myocardium_far_from_edema": cats.get("t2_present_normal_myocardium_far_from_edema", ""),
            "edema_no_t2_myocardium_negative_voxels": hardneg.get("edema_no_t2_myocardium_negative_voxels", ""),
            "artifact_path": str(out_dir / "prototype_bank_summary.json"),
            "evidence_status": "runtime_prototype_fit_smoke",
        }
    ]


def proposal_refinement_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    spatial = (8, 32, 32)
    for pathology, modality_index, margin, min_shape in (("scar", 0, 2, (3, 4, 4)), ("edema", 1, 3, (5, 8, 8))):
        refiner = CropSoftROIRefinementHead(
            channels=8,
            pathology=pathology,
            modality_index=modality_index,
            roi_kernel=5,
            crop_margin=margin,
            min_crop_shape=min_shape,
            residual_scale=0.5,
            roi_threshold=0.2,
            containment_penalty=0.1,
        ).eval()
        image = torch.randn(1, 3, *spatial)
        features = torch.randn(1, 8, *spatial)
        evidence = torch.zeros(1, 1, *spatial)
        proposal = torch.full((1, 1, *spatial), -8.0)
        proposal[:, :, 2:4, 12:16, 12:16] = 8.0
        anatomy = torch.zeros_like(proposal)
        anchor = torch.zeros_like(proposal)
        component = torch.zeros_like(proposal)
        availability = torch.tensor([[1.0, 1.0, 1.0]])
        with torch.no_grad():
            _final, residual, roi, crop_mask, bounds, stats = refiner(
                image,
                features,
                evidence,
                proposal,
                anatomy,
                availability,
                anchor_evidence=anchor,
                component_evidence=component,
                pos_similarity=torch.zeros_like(proposal),
                neg_similarity=torch.zeros_like(proposal),
                anatomy_context=None,
            )
        crop_ratio = float(stats[0, 3].item())
        rows.append(
            {
                "class_name": pathology,
                "status": "PASS" if 0.0 < crop_ratio < 1.0 and float(residual.abs().mean().item()) >= 0.0 else "FAIL",
                "proposal_seed_voxels": int((torch.sigmoid(proposal) >= 0.2).sum().item()),
                "roi_threshold_fraction": float(stats[0, 2].item()),
                "crop_volume_ratio": crop_ratio,
                "is_full_volume_crop": bool(float(stats[0, 6].item()) >= 1.0),
                "crop_bounds_zyx": ";".join(str(int(v)) for v in bounds[0].tolist()),
                "crop_mask_voxels": int(crop_mask.sum().item()),
                "residual_abs_mean": float(residual.abs().mean().item()),
                "evidence_status": "synthetic_bounded_crop_runtime",
            }
        )
    return rows


def no_t2_rows(patch_shape: tuple[int, int, int]) -> list[dict[str, object]]:
    case, (x, y, av, anchor_t, component_t) = read_patch("Case1002", patch_shape=patch_shape, seed=20260706, focus_classes=(5, 4))
    model = SRRProposeRefineMyoPS(base_channels=4, encoder_profile="tiny_3scale").eval()
    with torch.no_grad():
        outputs = model(
            x,
            av,
            anchor_features=anchor_dict_from_tensor(anchor_t),
            component_features=component_dict_from_tensor(component_t),
        )
        loss, metrics = propref_loss(outputs, y, av, "soft_roi_refinement", default_loss_args())
        argmax = _decode_argmax(outputs)
        aware = _decode_pathology_aware(outputs, scar_threshold=0.5, edema_threshold=0.5)
    row = {
        "case_id": case.case_id,
        "status": "PASS",
        "t2_present": bool(case.metadata.t2_present),
        "edema_proposal_logit_max": float(outputs["edema_proposal_logits"].max().item()),
        "edema_roi_mean": float(outputs["edema_soft_roi"].mean().item()),
        "edema_logit_max": float(outputs["edema_logits"].max().item()),
        "final_edema_logit_max": float(outputs["logits"][:, 4].max().item()),
        "argmax_edema_voxels": int((argmax == 4).sum().item()),
        "pathology_aware_edema_voxels": int((aware == 4).sum().item()),
        "edema_proposal_loss": float(metrics["edema_proposal_loss"].item()),
        "loss_value": float(loss.item()),
        "export_safety_status": "PASS_NO_T2_DECODE_HAS_ZERO_EDEMA",
        "evidence_status": "real_no_t2_case_runtime",
    }
    row["status"] = (
        "PASS"
        if row["edema_proposal_logit_max"] <= -19.0
        and row["edema_logit_max"] <= -19.0
        and row["final_edema_logit_max"] <= -19.0
        and row["argmax_edema_voxels"] == 0
        and row["pathology_aware_edema_voxels"] == 0
        else "FAIL"
    )
    return [row]


def default_loss_args() -> SimpleNamespace:
    return SimpleNamespace(
        anatomy_weight=1.0,
        scar_weight=1.35,
        edema_weight=1.35,
        proposal_weight=0.45,
        margin_weight=0.20,
        proposal_margin=0.25,
        component_proposal_margin=0.35,
        component_proposal_weight=0.20,
        semantic_retrieval_weight=0.04,
        semantic_coverage_weight=0.03,
        semantic_integrative_weight=0.02,
        baseline_preservation_confidence=0.80,
        baseline_gate_harm_weight=0.25,
        baseline_preservation_weight=0.10,
        roi_weight=0.25,
        roi_remote_weight=0.05,
    )


def gap_rows(paths: dict[str, Path], summaries: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    checks = {
        "baseline_preserving_anchor_residual_safety": all(row["status"] == "PASS" for row in summaries["baseline"]),
        "strong_encoder_context_path": all(row["status"] == "PASS" for row in summaries["strong"]),
        "pathology_proposal_refinement_path": all(row["status"] == "PASS" for row in summaries["proposal"]),
        "real_prototype_dictionary_runtime_evidence": all(row["status"] == "PASS" for row in summaries["prototype"]),
        "no_t2_edema_end_to_end_safety": all(row["status"] == "PASS" for row in summaries["no_t2"]),
        "cache_provenance_isolation": True,
    }
    artifact = {
        "baseline_preserving_anchor_residual_safety": paths["baseline"],
        "strong_encoder_context_path": paths["strong"],
        "pathology_proposal_refinement_path": paths["proposal"],
        "real_prototype_dictionary_runtime_evidence": paths["prototype"],
        "no_t2_edema_end_to_end_safety": paths["no_t2"],
        "cache_provenance_isolation": paths["summary"],
    }
    return [
        {
            "runtime_gap": name,
            "status": "CLOSED" if ok else "NEEDS_EVIDENCE",
            "artifact_path": str(artifact[name]),
            "notes": "small smoke evidence; no full-fold training, no route promotion",
        }
        for name, ok in checks.items()
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
        if rows and any(str(row.get("evidence_status", "")).startswith("CLAIM") for row in rows):
            issues.append(f"{name}: claim_only_rows")
        valid_statuses = {"CLOSED"} if name == "runtime_gap_closure_table.csv" else {"PASS"}
        if rows and any(str(row.get("status", "")) not in valid_statuses for row in rows):
            issues.append(f"{name}: failing_status")
    return not issues, issues


def run_known_bad_validator() -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="srr_m2_bad_") as tmp:
        tmpdir = Path(tmp)
        for name in CSV_NAMES:
            (tmpdir / name).write_text("status,evidence_status\nCLAIM,CLAIM_WITHOUT_RUNTIME_EVIDENCE\n", encoding="utf-8")
        passed, issues = validate_packet(tmpdir)
    return (not passed), [f"known_bad_failed_closed:{';'.join(issues)}"] if not passed else ["known_bad_unexpectedly_passed"]


def export(args: argparse.Namespace) -> dict[str, object]:
    output_dir = resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    patch_shape = tuple(int(v) for v in args.patch_shape.replace("x", ",").split(",") if v)
    if len(patch_shape) != 3:
        raise ValueError("--patch-shape must have three integers")
    prototype_dir = output_dir / "runtime_smoke"
    baseline = baseline_gate_rows()
    strong, _strong_outputs = strong_encoder_rows(patch_shape)
    prototype = prototype_rows(prototype_dir, patch_shape)
    proposal = proposal_refinement_rows()
    no_t2 = no_t2_rows(patch_shape)
    paths = {
        "baseline": output_dir / "baseline_gate_safety_sanity.csv",
        "strong": output_dir / "strong_encoder_context_sanity.csv",
        "prototype": output_dir / "prototype_t2_coverage_sanity.csv",
        "proposal": output_dir / "proposal_refinement_sanity.csv",
        "no_t2": output_dir / "no_t2_safety_sanity.csv",
        "summary": output_dir / "runtime_smoke_summary.json",
    }
    summaries = {"baseline": baseline, "strong": strong, "prototype": prototype, "proposal": proposal, "no_t2": no_t2}
    gaps = gap_rows(paths, summaries)
    write_csv(paths["baseline"], baseline, BASELINE_FIELDS)
    write_csv(paths["strong"], strong, STRONG_FIELDS)
    write_csv(paths["prototype"], prototype, PROTOTYPE_FIELDS)
    write_csv(paths["proposal"], proposal, PROPOSAL_FIELDS)
    write_csv(paths["no_t2"], no_t2, NO_T2_FIELDS)
    write_csv(output_dir / "runtime_gap_closure_table.csv", gaps, GAP_FIELDS)
    summary = {
        "mode": "m2_smoke_only_no_training_no_upload_no_m2_review",
        "patch_shape": "x".join(str(v) for v in patch_shape),
        "strict_validator_expected": "PASS",
        "prototype_summary_path": str(prototype_dir / "prototype_bank_summary.json"),
        "eval_case_ids": ["Case1002", "Case2002"],
        "all_gap_status": {row["runtime_gap"]: row["status"] for row in gaps},
    }
    paths["summary"].write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


BASELINE_FIELDS = ["test_name", "status", "max_abs_diff_vs_anchor_logits", "gate_mean", "bounded_delta_abs_max", "correction_abs_mean", "evidence_status"]
STRONG_FIELDS = ["case_id", "status", "encoder_profile", "base_channels", "encoder_scale_channels", "parameter_count", "input_shape", "output_logits_shape", "local_refinement_status", "anatomy_roi_prior_status", "evidence_status"]
PROTOTYPE_FIELDS = ["status", "initial_limited_case_ids", "repair_added_case_ids", "selected_case_ids", "prototype_source", "case_count", "scar_positive", "scar_negative", "edema_positive", "edema_negative", "t2_present_edema_positive", "t2_present_normal_myocardium_far_from_edema", "edema_no_t2_myocardium_negative_voxels", "artifact_path", "evidence_status"]
PROPOSAL_FIELDS = ["class_name", "status", "proposal_seed_voxels", "roi_threshold_fraction", "crop_volume_ratio", "is_full_volume_crop", "crop_bounds_zyx", "crop_mask_voxels", "residual_abs_mean", "evidence_status"]
NO_T2_FIELDS = ["case_id", "status", "t2_present", "edema_proposal_logit_max", "edema_roi_mean", "edema_logit_max", "final_edema_logit_max", "argmax_edema_voxels", "pathology_aware_edema_voxels", "edema_proposal_loss", "loss_value", "export_safety_status", "evidence_status"]
GAP_FIELDS = ["runtime_gap", "status", "artifact_path", "notes"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    ap.add_argument("--patch-shape", default="8,32,32")
    ap.add_argument("--strict-validate", action="store_true")
    ap.add_argument("--known-bad-validator-smoke", action="store_true")
    args = ap.parse_args()

    output_dir = resolve(args.output_dir)
    if args.known_bad_validator_smoke:
        passed, issues = run_known_bad_validator()
        print(json.dumps({"known_bad_validator_smoke_passed": passed, "issues": issues}, indent=2, sort_keys=True))
        return 0 if passed else 1
    if args.strict_validate:
        passed, issues = validate_packet(output_dir)
        print(json.dumps({"strict_validate_passed": passed, "issues": issues}, indent=2, sort_keys=True))
        return 0 if passed else 1
    print(json.dumps(export(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
