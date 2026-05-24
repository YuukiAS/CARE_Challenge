#!/usr/bin/env python3
"""Lane A Round15 DeepResearch portfolio controller diagnostics.

This script executes the low-risk front half of the Round15 controller:

* reproducibility and candidate registry gate;
* compliance/metadata matrix;
* batch job matrix;
* first-party one-case feature/gradient smokes for candidate routes A-E.

It does not submit Slurm, train fold0 models, create validation zips, download
weights, clone external repositories, or modify nnU-Net baseline caches.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import SimpleITK as sitk
import torch
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault("MPLCONFIGDIR", str(OUT_ROOT / "mpl_cache") if "OUT_ROOT" in globals() else str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/mpl_cache"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.calibrator.laneA_round14_model import VoxelFeatureCalibrator
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, read_csv, write_csv


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio"
PLAN_PATH = REPO_ROOT / "docs/plans/laneA_round15_next_deepresearch_portfolio_batch_execution.md"
ROUND13_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round13_t2_lge_intensity_anatomy_consistency"
ROUND14_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round14_feature_augmented_calibrator"
BASELINE_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
LABELS_TR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"

EDEMA = 4
SCAR = 5
SEED = 15015


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    mechanism_slot: str
    priority: str
    job_type: str
    role: str
    implementation_mode: str
    external_repo_needed: str
    pretrained_weights_needed: str
    batch_job_allowed: str
    expected_output_dir: str
    gate_before_job: str
    pass_signal: str
    fail_fast: str


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", "\\|") for col in columns) + " |")
    return "\n".join(lines)


def safe_float(value: object, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def candidates() -> list[Candidate]:
    base = "results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio"
    return [
        Candidate(
            "R15_A_intensity_prior_feature_head_fold0_vs",
            "I_MMSeg_style_T2_LGE_intensity_prior_route",
            "highest",
            "fold0 very-short, then fold0 short if promoted",
            "stronger learnable T2/LGE support feature head",
            "first-party feature head from Round13 feature cache plus baseline probabilities",
            "no",
            "no",
            "yes after one-case smoke",
            f"{base}/R15_A_intensity_prior_feature_head_fold0_vs/",
            "feature cache, one-batch forward/backward, scar unchanged, no-T2 policy checked",
            "CenterC or T2-present GT-positive edema improves with HD95/component clean",
            "no CenterC signal, no-T2 FP, scar regression, NaN/Inf",
        ),
        Candidate(
            "R15_B_anatomy_pathology_cascade_fold0_vs",
            "Cascaded_FSN_PTNet_anatomy_pathology_consistency_route",
            "high",
            "fold0 very-short, then fold0 short if promoted",
            "soft anatomy/pathology support without hard deletion",
            "first-party anatomy probability/distance support plus pathology consistency head",
            "no",
            "no",
            "yes after one-case smoke",
            f"{base}/R15_B_anatomy_pathology_cascade_fold0_vs/",
            "anatomy maps located, no hard deletion, label mapping unchanged",
            "remote FP/component improve without true-lesion loss",
            "over-pruning, CenterC Dice/HD95 regression, scar regression",
        ),
        Candidate(
            "R15_C_intensity_plus_anatomy_support_head_fold0_vs",
            "combined_intensity_anatomy_support_route",
            "highest",
            "fold0 very-short, then fold0 short if promoted",
            "combine T2/LGE support with anatomy-lesion support",
            "first-party bounded edema-only support head/calibrator",
            "no",
            "no",
            "yes after A/B one-case gates",
            f"{base}/R15_C_intensity_plus_anatomy_support_head_fold0_vs/",
            "both feature sources cache-isolated and one-batch passes",
            "cleanest CenterC/T2-present edema signal among first-party candidates",
            "support shortcut, no-T2 FP, HD95/component regression",
        ),
        Candidate(
            "R15_D_boundary_surface_auxiliary_fold0_vs",
            "Boundary_HD_InverseForm_surface_auxiliary_route",
            "medium",
            "tiny-overfit or fold0 very-short auxiliary",
            "small-weight boundary/surface auxiliary for class_4 edema",
            "first-party small boundary/smoothness auxiliary before any external InverseForm use",
            "no for first-party; yes only for external InverseForm smoke",
            "no",
            "yes after loss gradient smoke",
            f"{base}/R15_D_boundary_surface_auxiliary_fold0_vs/",
            "loss finite, gradient bounded, class_5 interference zero/negligible",
            "HD95/component improves without Dice/scar trade-off",
            "Dice/HD95 trade-off, fragmented components, scar regression",
        ),
        Candidate(
            "R15_E_modality_conditioned_moe_small_fold0_vs",
            "Missing_modality_representation_route",
            "medium-high",
            "tiny-overfit then fold0 very-short",
            "small first-party modality-conditioned head/MoE",
            "first-party explicit modality conditioning with uncertainty-aware no-T2 policy",
            "no for first-party; yes only for external readiness",
            "no",
            "yes after tiny gate",
            f"{base}/R15_E_modality_conditioned_moe_small_fold0_vs/",
            "no-T2 policy documented, one-batch gradient clean, cache isolated",
            "T2-present edema signal with no-T2 stability",
            "no-T2 FP, center shortcut, scar guardrail regression",
        ),
        Candidate(
            "R15_F_pretrained_or_MedNeXt_readiness_smoke",
            "Pretrained_backbone_feature_route",
            "medium-high",
            "metadata-only, config/shape smoke",
            "pretrained backbone/feature readiness",
            "MedNeXt, nnU-Net Task114/M&Ms, BiomedParse readiness only",
            "maybe",
            "maybe",
            "no training until compliance passes",
            f"{base}/R15_F_pretrained_or_MedNeXt_readiness_smoke/",
            "license/pretrained-data/source/shape/channel audit",
            "one candidate eligible for future one-case smoke",
            "unclear license, external data conflict, incompatible I/O",
        ),
        Candidate(
            "R15_G_external_I_MMSeg_metadata_onecase_smoke",
            "I_MMSeg_style_T2_LGE_intensity_prior_route",
            "high",
            "metadata-only or one-case smoke if source is locally available",
            "external I-MMSeg readiness",
            "metadata audit only in this execution unless separately authorized",
            "yes",
            "unclear",
            "no fold0 training",
            f"{base}/R15_G_external_I_MMSeg_metadata_onecase_smoke/",
            "license/dependency/input-output/label mapping",
            "reusable intensity-prior mechanism identified",
            "external data requirement, opaque LLM dependency, no usable CARE I/O",
        ),
        Candidate(
            "R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke",
            "Cascaded_FSN_PTNet_anatomy_pathology_consistency_route",
            "medium-high",
            "metadata-only or one-case smoke if feasible",
            "external cascaded anatomy/pathology readiness",
            "metadata audit only in this execution unless separately authorized",
            "yes",
            "no",
            "no fold0 training",
            f"{base}/R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke/",
            "compliance/shape/label mapping",
            "soft anatomy/pathology module reusable",
            "hard ROI dependence or incompatible labels",
        ),
        Candidate(
            "R15_I_external_InverseForm_metadata_loss_smoke",
            "Boundary_HD_InverseForm_surface_auxiliary_route",
            "medium",
            "metadata-only plus loss one-batch smoke if safe",
            "external boundary/HD loss readiness",
            "metadata audit; first-party loss smoke preferred",
            "yes",
            "no",
            "no fold0 training until loss gate",
            f"{base}/R15_I_external_InverseForm_metadata_loss_smoke/",
            "finite loss, finite gradients, class_4-only auxiliary scoped",
            "HD-aware auxiliary implementable",
            "unstable gradients or broad class interference",
        ),
        Candidate(
            "R15_J_CAA_Seg_SSA_metadata_centerC_smoke",
            "CAA_Seg_SSA_alignment_route",
            "medium-low",
            "metadata/one-case CenterC alignment smoke",
            "alignment watch/readiness",
            "CARE-only CenterC alignment proxy first; external CAA-Seg only if justified",
            "not for CARE-only audit; yes for external smoke",
            "no",
            "metadata/one-case only unless strong evidence",
            f"{base}/R15_J_CAA_Seg_SSA_metadata_centerC_smoke/",
            "complete CenterC cases and alignment proxies identified",
            "alignment mismatch correlates with failures",
            "no mismatch evidence or silent affine/label changes",
        ),
    ]


def candidate_rows() -> list[dict[str, object]]:
    return [c.__dict__ for c in candidates()]


def compliance_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    local_docs = {
        "R15_G_external_I_MMSeg_metadata_onecase_smoke": "docs/notes/deep_research/Result2.pdf mentions I-MMSeg as open source but local repo is absent",
        "R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke": "docs/notes/deep_research/Result1.pdf mentions Cascaded FSN/PT-Net; local repo is absent",
        "R15_I_external_InverseForm_metadata_loss_smoke": "docs/notes/deep_research/Result1.pdf mentions Qualcomm-AI-research/InverseForm; local repo is absent",
        "R15_J_CAA_Seg_SSA_metadata_centerC_smoke": "docs/notes/deep_research/Result1.pdf describes CAA-Seg/SSA alignment; local repo is absent",
    }
    for c in candidates():
        first_party = c.external_repo_needed == "no"
        local_external = c.candidate_id.startswith("R15_F") or c.candidate_id.startswith("R15_G") or c.candidate_id.startswith("R15_H") or c.candidate_id.startswith("R15_I") or c.candidate_id.startswith("R15_J")
        rows.append(
            {
                "candidate_id": c.candidate_id,
                "mechanism_slot": c.mechanism_slot,
                "candidate_name": c.role,
                "source_url_or_local_path": "first-party CARE implementation" if first_party else local_docs.get(c.candidate_id, "local docs only; no repo checked out"),
                "role": c.role,
                "license": "CARE repo first-party" if first_party else "unclear/not verified in local checkout",
                "license_status": "pass_first_party" if first_party else "postpone_pending_live_license_audit",
                "pretrained_weights_available": "not needed" if first_party else "unclear",
                "pretrained_data_source": "not applicable" if first_party else "unclear",
                "external_data_training_required": "no" if first_party else "unclear; must be treated as not allowed until proven otherwise",
                "challenge_compliance_risk": "low" if first_party else "medium/high until license and pretrained-data source are verified",
                "dependency_risk": "low" if first_party else "medium/high; no external repo cloned or built",
                "input_modalities_expected": "CARE C0/LGE/T2 plus baseline probabilities/features",
                "output_labels_expected": "class_4 edema-only modifications; class_5 scar guardrail",
                "CARE_label_mapping_plan": "compact labels 0..5 unchanged; edema=4 scar=5",
                "channel_count_compatibility": "uses feature/cache tensors; no nnU-Net baseline cache mutation" if first_party else "unknown until one-case smoke",
                "spacing_orientation_assumptions": "reuse GT/reference image geometry; no silent affine changes",
                "one_case_smoke_required": "yes",
                "eligible_for_fold0_training": "yes_after_onecase_gate" if first_party else "no_metadata_only_or_postpone",
                "readiness_status": "go_stage3_first_party_smoke" if first_party else "postpone_external_repo_until_explicit_audit_or_authorization",
                "reason_if_rejected": "" if first_party else "external license/pretrained data/dependencies not verified; no local repo present",
            }
        )
    return rows


def batch_rows() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": c.candidate_id,
            "mechanism_slot": c.mechanism_slot,
            "job_type": c.job_type,
            "expected_output_dir": c.expected_output_dir,
            "can_submit_in_first_batch": c.batch_job_allowed,
            "gate_before_job": c.gate_before_job,
            "pass_signal": c.pass_signal,
            "fail_fast": c.fail_fast,
            "slurm_status": "not_submitted",
            "job_script_status": "not_created_until_stage3_passes",
        }
        for c in candidates()
    ]


def reproducibility_rows(cases: list[RefinerCase]) -> list[dict[str, object]]:
    required = [
        ("round15_plan", PLAN_PATH, True),
        ("README", REPO_ROOT / "README.md", True),
        ("CARE_README_optional", REPO_ROOT / "CARE-README.md", False),
        ("splits_MyoPS", SPLITS_JSON, True),
        ("labelsTr", LABELS_TR, True),
        ("nnUNet501_baseline_root", BASELINE_ROOT, True),
        ("round13_decision", ROUND13_ROOT / "round13_decision_table.md", True),
        ("round13_feature_manifest", ROUND13_ROOT / "t2_lge_intensity_feature_cache_manifest.csv", True),
        ("round14_decision", ROUND14_ROOT / "round14_decision_table.md", True),
        ("round14_recommendation", ROUND14_ROOT / "round14_round15_recommendation.md", True),
        ("round14_component_manifest", ROUND14_ROOT / "round14_component_dataset_manifest.csv", True),
        ("round14_voxel_manifest", ROUND14_ROOT / "round14_voxel_patch_dataset_manifest.csv", True),
    ]
    rows = []
    for name, path, hard_required in required:
        exists = path.exists()
        rows.append(
            {
                "item": name,
                "path": str(path),
                "exists": exists,
                "required": hard_required,
                "status": "pass" if exists else ("fail_missing" if hard_required else "optional_missing"),
            }
        )
    missing_pred = sum(1 for c in cases if not c.prediction_path.is_file())
    missing_prob = sum(1 for c in cases if not c.probability_path.is_file())
    missing_gt = sum(1 for c in cases if not c.gt_path.is_file())
    val_cases = sum(1 for c in cases if c.fold0_split == "val")
    train_cases = sum(1 for c in cases if c.fold0_split == "train")
    complete_cases = sum(1 for c in cases if c.modality_group == "C0+LGE+T2")
    centerc_val = sum(1 for c in cases if c.fold0_split == "val" and c.center == "CenterC")
    rows.extend(
        [
            {"item": "case_count_total", "path": "build_cases()", "exists": len(cases) == 220, "status": len(cases)},
            {"item": "fold0_train_cases", "path": "splits_MyoPS.json", "exists": train_cases > 0, "status": train_cases},
            {"item": "fold0_val_cases", "path": "splits_MyoPS.json", "exists": val_cases == 44, "status": val_cases},
            {"item": "complete_modality_cases", "path": "metadata", "exists": complete_cases > 0, "status": complete_cases},
            {"item": "CenterC_val_cases", "path": "metadata", "exists": centerc_val > 0, "status": centerc_val},
            {"item": "missing_baseline_predictions", "path": "baseline OOF predictions", "exists": missing_pred == 0, "status": missing_pred},
            {"item": "missing_baseline_probabilities", "path": "baseline OOF probabilities", "exists": missing_prob == 0, "status": missing_prob},
            {"item": "missing_gt_labels", "path": "labelsTr", "exists": missing_gt == 0, "status": missing_gt},
        ]
    )
    return rows


def load_feature_case(cases: list[RefinerCase], *, want_t2: bool) -> tuple[RefinerCase, dict[str, np.ndarray], np.ndarray]:
    # Round13 feature caches were generated for fold0 validation cases. Prefer
    # train when available, but allow validation for this disposable compatibility
    # smoke because no learned artifact from this script is promoted or reused.
    ordered_cases = sorted(cases, key=lambda c: 0 if c.fold0_split == "train" else 1)
    for case in ordered_cases:
        if want_t2 and not (case.t2_present and case.edema_gt_positive):
            continue
        if (not want_t2) and case.t2_present:
            continue
        feature_path = ROUND13_ROOT / "feature_cache" / f"{case.case_id}_round13_features.npz"
        if not feature_path.is_file() or not case.gt_path.is_file():
            continue
        with np.load(feature_path) as data:
            features = {key: np.asarray(data[key], dtype=np.float32) for key in data.files}
        gt = sitk.GetArrayFromImage(sitk.ReadImage(str(case.gt_path))).astype(np.uint8, copy=False)
        if features["baseline_edema_prob"].shape != gt.shape:
            continue
        return case, features, gt
    raise RuntimeError(f"no suitable {'T2-present' if want_t2 else 'no-T2'} train case with Round13 feature cache")


def sample_voxels(features: dict[str, np.ndarray], gt: np.ndarray, names: list[str], max_pos: int = 2048, max_neg: int = 2048) -> tuple[torch.Tensor, torch.Tensor]:
    rng = np.random.default_rng(SEED)
    target = gt == EDEMA
    pos = np.flatnonzero(target.ravel())
    neg = np.flatnonzero(~target.ravel())
    if pos.size:
        pos = rng.choice(pos, size=min(max_pos, pos.size), replace=False)
    if neg.size:
        neg = rng.choice(neg, size=min(max_neg, neg.size), replace=False)
    idx = np.concatenate([pos, neg])
    rng.shuffle(idx)
    cols = []
    for name in names:
        arr = features[name].ravel()[idx].astype(np.float32, copy=False)
        cols.append(arr)
    x = np.stack(cols, axis=1)
    y = target.ravel()[idx].astype(np.float32, copy=False)
    return torch.from_numpy(x), torch.from_numpy(y)


def run_voxel_smoke(candidate_id: str, case: RefinerCase, features: dict[str, np.ndarray], gt: np.ndarray, feature_names: list[str]) -> dict[str, object]:
    torch.manual_seed(SEED)
    x, y = sample_voxels(features, gt, feature_names)
    model = VoxelFeatureCalibrator(x.shape[1], hidden_features=12)
    opt = torch.optim.AdamW(model.parameters(), lr=5e-3)
    criterion = nn.BCEWithLogitsLoss()
    losses = []
    for _ in range(6):
        opt.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach().cpu()))
    grad_norm = 0.0
    for p in model.parameters():
        if p.grad is not None:
            grad_norm += float(p.grad.detach().norm().cpu())
    with torch.no_grad():
        probs = torch.sigmoid(model(x))
    finite = all(math.isfinite(v) for v in losses) and math.isfinite(grad_norm)
    return {
        "candidate_id": candidate_id,
        "case_id": case.case_id,
        "center": case.center,
        "modality_group": case.modality_group,
        "smoke_type": "voxel_feature_forward_backward",
        "status": "pass" if finite and losses[-1] <= losses[0] else "watch",
        "fold0_split": case.fold0_split,
        "n_samples": int(x.shape[0]),
        "n_positive": int(y.sum().item()),
        "n_negative": int((1 - y).sum().item()),
        "feature_columns": ",".join(feature_names),
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "loss_delta": losses[0] - losses[-1],
        "last_grad_norm": grad_norm,
        "nan_or_inf": not finite,
        "positive_prob_mean": float(probs[y == 1].mean().cpu()) if int(y.sum().item()) else "",
        "negative_prob_mean": float(probs[y == 0].mean().cpu()) if int((1 - y).sum().item()) else "",
        "scar_changed_voxels": 0,
        "no_t2_policy": "not used for dense hard negative in this smoke",
        "eligible_for_fold0_very_short": "gate_pending_metric_design",
    }


def run_boundary_smoke(case: RefinerCase, features: dict[str, np.ndarray], gt: np.ndarray) -> dict[str, object]:
    x, y = sample_voxels(features, gt, ["baseline_edema_prob", "support_score", "anatomy_support"], max_pos=2048, max_neg=2048)
    baseline_prob = torch.clamp(x[:, 0], 1e-4, 1 - 1e-4)
    logits = torch.logit(baseline_prob).detach().clone().requires_grad_(True)
    criterion = nn.BCEWithLogitsLoss()
    # Lightweight finite-gradient proxy: supervised class-4 BCE plus small
    # residual magnitude penalty. Real surface/HD loss still needs a dedicated
    # follow-up candidate implementation before fold0 jobs.
    loss = criterion(logits, y) + 0.01 * torch.mean((torch.sigmoid(logits) - baseline_prob) ** 2)
    loss.backward()
    grad_norm = float(logits.grad.detach().norm().cpu()) if logits.grad is not None else math.nan
    finite = math.isfinite(float(loss.detach().cpu())) and math.isfinite(grad_norm)
    return {
        "candidate_id": "R15_D_boundary_surface_auxiliary_fold0_vs",
        "case_id": case.case_id,
        "center": case.center,
        "modality_group": case.modality_group,
        "smoke_type": "class4_boundary_auxiliary_proxy_gradient",
        "status": "pass_loss_gradient_only" if finite else "fail_nan_or_inf",
        "fold0_split": case.fold0_split,
        "n_samples": int(x.shape[0]),
        "n_positive": int(y.sum().item()),
        "n_negative": int((1 - y).sum().item()),
        "feature_columns": "baseline_edema_prob,support_score,anatomy_support",
        "initial_loss": float(loss.detach().cpu()),
        "final_loss": float(loss.detach().cpu()),
        "loss_delta": 0.0,
        "last_grad_norm": grad_norm,
        "nan_or_inf": not finite,
        "positive_prob_mean": "",
        "negative_prob_mean": "",
        "scar_changed_voxels": 0,
        "no_t2_policy": "not used for dense hard negative in this smoke",
        "eligible_for_fold0_very_short": "no; needs real surface/HD objective implementation first",
    }


class TinyModalityConditionedMoE(nn.Module):
    def __init__(self, in_features: int) -> None:
        super().__init__()
        self.t2_expert = nn.Sequential(nn.Linear(in_features, 12), nn.LeakyReLU(inplace=True), nn.Linear(12, 1))
        self.missing_expert = nn.Sequential(nn.Linear(in_features, 12), nn.LeakyReLU(inplace=True), nn.Linear(12, 1))

    def forward(self, x: torch.Tensor, t2_present: torch.Tensor) -> torch.Tensor:
        t2_logit = self.t2_expert(x).squeeze(-1)
        missing_logit = self.missing_expert(x).squeeze(-1)
        return t2_present * t2_logit + (1.0 - t2_present) * missing_logit


def run_moe_smoke(
    t2_case: RefinerCase,
    t2_features: dict[str, np.ndarray],
    t2_gt: np.ndarray,
    missing_case: RefinerCase,
    missing_features: dict[str, np.ndarray],
    missing_gt: np.ndarray,
) -> dict[str, object]:
    feature_names = ["baseline_edema_prob", "t2_support", "lge_support", "t2_lge_contrast", "anatomy_support", "support_score"]
    x1, y1 = sample_voxels(t2_features, t2_gt, feature_names, max_pos=2048, max_neg=2048)
    x0, y0 = sample_voxels(missing_features, missing_gt, feature_names, max_pos=0, max_neg=1024)
    x = torch.cat([x1, x0], dim=0)
    y = torch.cat([y1, y0], dim=0)
    t2_present = torch.cat([torch.ones(x1.shape[0]), torch.zeros(x0.shape[0])], dim=0)
    weights = torch.cat([torch.ones(x1.shape[0]), torch.full((x0.shape[0],), 0.05)], dim=0)
    torch.manual_seed(SEED)
    model = TinyModalityConditionedMoE(x.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=5e-3)
    losses: list[float] = []
    for _ in range(8):
        opt.zero_grad(set_to_none=True)
        logits = model(x, t2_present)
        loss_raw = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="none")
        loss = torch.sum(loss_raw * weights) / torch.clamp(weights.sum(), min=1.0)
        loss.backward()
        opt.step()
        losses.append(float(loss.detach().cpu()))
    grad_norm = 0.0
    for p in model.parameters():
        if p.grad is not None:
            grad_norm += float(p.grad.detach().norm().cpu())
    finite = all(math.isfinite(v) for v in losses) and math.isfinite(grad_norm)
    return {
        "candidate_id": "R15_E_modality_conditioned_moe_small_fold0_vs",
        "case_id": f"{t2_case.case_id}+{missing_case.case_id}",
        "center": f"{t2_case.center}+{missing_case.center}",
        "modality_group": f"{t2_case.modality_group}+{missing_case.modality_group}",
        "smoke_type": "tiny_modality_conditioned_moe_forward_backward",
        "status": "pass" if finite and losses[-1] <= losses[0] else "watch",
        "fold0_split": f"{t2_case.fold0_split}+{missing_case.fold0_split}",
        "n_samples": int(x.shape[0]),
        "n_positive": int(y.sum().item()),
        "n_negative": int((1 - y).sum().item()),
        "feature_columns": ",".join(feature_names) + ",T2_present_gate",
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "loss_delta": losses[0] - losses[-1],
        "last_grad_norm": grad_norm,
        "nan_or_inf": not finite,
        "positive_prob_mean": "",
        "negative_prob_mean": "",
        "scar_changed_voxels": 0,
        "no_t2_policy": "weak weight 0.05; no dense hard-negative dominance",
        "eligible_for_fold0_very_short": "gate_pending_candidate_implementation",
    }


def onecase_smoke_rows(cases: list[RefinerCase]) -> list[dict[str, object]]:
    t2_case, t2_features, t2_gt = load_feature_case(cases, want_t2=True)
    missing_case, missing_features, missing_gt = load_feature_case(cases, want_t2=False)
    rows = [
        run_voxel_smoke(
            "R15_A_intensity_prior_feature_head_fold0_vs",
            t2_case,
            t2_features,
            t2_gt,
            ["baseline_edema_prob", "t2_support", "lge_support", "t2_lge_contrast", "entropy", "edema_margin"],
        ),
        run_voxel_smoke(
            "R15_B_anatomy_pathology_cascade_fold0_vs",
            t2_case,
            t2_features,
            t2_gt,
            ["baseline_edema_prob", "anatomy_support", "support_score", "entropy", "edema_margin"],
        ),
        run_voxel_smoke(
            "R15_C_intensity_plus_anatomy_support_head_fold0_vs",
            t2_case,
            t2_features,
            t2_gt,
            [
                "baseline_edema_prob",
                "t2_support",
                "lge_support",
                "t2_lge_contrast",
                "anatomy_support",
                "support_score",
                "entropy",
                "edema_margin",
            ],
        ),
        run_boundary_smoke(t2_case, t2_features, t2_gt),
        run_moe_smoke(t2_case, t2_features, t2_gt, missing_case, missing_features, missing_gt),
    ]
    for c in candidates():
        if c.candidate_id.startswith(("R15_F", "R15_G", "R15_H", "R15_I", "R15_J")):
            rows.append(
                {
                    "candidate_id": c.candidate_id,
                    "case_id": "",
                    "center": "",
                    "modality_group": "",
                    "smoke_type": "metadata_only_external_or_pretrained_readiness",
                    "status": "postpone_no_local_repo_or_weights_no_download",
                    "fold0_split": "",
                    "n_samples": 0,
                    "n_positive": 0,
                    "n_negative": 0,
                    "feature_columns": "",
                    "initial_loss": "",
                    "final_loss": "",
                    "loss_delta": "",
                    "last_grad_norm": "",
                    "nan_or_inf": False,
                    "positive_prob_mean": "",
                    "negative_prob_mean": "",
                    "scar_changed_voxels": 0,
                    "no_t2_policy": "not applicable",
                    "eligible_for_fold0_very_short": "no; metadata/compliance or user authorization required first",
                }
            )
    return rows


def write_markdown_outputs(
    reproducibility: list[dict[str, object]],
    registry: list[dict[str, object]],
    compliance: list[dict[str, object]],
    batch: list[dict[str, object]],
    smoke: list[dict[str, object]],
) -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    readme = f"""# Lane A Round15 Goal Execution Readme

Status: Stage 1-3 low-risk diagnostics executed; no training, Slurm, validation zip, upload, external clone, or weight download.

Plan: `{PLAN_PATH}`

Output root: `{OUT_ROOT}`

Round15 stance:

- First-party A-E candidates can proceed only from reproducibility -> metadata -> one-case/gradient smoke -> fold0 very-short.
- External/pretrained F-J candidates are metadata/readiness only until license, pretrained data, dependency, I/O, and label gates are clean.
- Fold1-4, 5-fold, validation zip, and upload are still prohibited without separate user authorization.
"""
    write_text(OUT_ROOT / "round15_goal_execution_readme.md", readme)

    write_text(
        OUT_ROOT / "round15_candidate_registry.md",
        "# Round15 Candidate Registry\n\n"
        + md_table(
            registry,
            [
                "candidate_id",
                "mechanism_slot",
                "priority",
                "job_type",
                "role",
                "batch_job_allowed",
                "fail_fast",
            ],
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round15_compliance_metadata_matrix.md",
        "# Round15 Compliance Metadata Matrix\n\n"
        + md_table(
            compliance,
            [
                "candidate_id",
                "license_status",
                "pretrained_weights_available",
                "external_data_training_required",
                "challenge_compliance_risk",
                "eligible_for_fold0_training",
                "readiness_status",
            ],
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round15_batch_job_matrix.md",
        "# Round15 Batch Job Matrix\n\n"
        + md_table(
            batch,
            [
                "candidate_id",
                "job_type",
                "can_submit_in_first_batch",
                "gate_before_job",
                "slurm_status",
                "job_script_status",
            ],
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "round15_onecase_smoke_summary.md",
        "# Round15 One-Case Smoke Summary\n\n"
        + md_table(
            smoke,
            [
                "candidate_id",
                "status",
                "case_id",
                "n_samples",
                "n_positive",
                "initial_loss",
                "final_loss",
                "loss_delta",
                "last_grad_norm",
                "eligible_for_fold0_very_short",
            ],
        )
        + "\n",
    )
    external_notes = """# Round15 External Method Readiness Notes

No external repository was cloned, no external weights were downloaded, and no external data was used.

- `R15_F_pretrained_or_MedNeXt_readiness_smoke`: postponed to live license/pretrained-data audit before any weight use.
- `R15_G_external_I_MMSeg_metadata_onecase_smoke`: local DeepResearch notes identify the mechanism, but the local repo is absent; postpone full smoke until source/license/dependency audit is explicit.
- `R15_H_external_CascadedFSN_or_PTNet_metadata_onecase_smoke`: local notes identify the mechanism; hard ROI behavior must be rejected, soft anatomy support only.
- `R15_I_external_InverseForm_metadata_loss_smoke`: first-party boundary proxy gradient smoke passed/failed as recorded; external InverseForm still needs license/dependency audit.
- `R15_J_CAA_Seg_SSA_metadata_centerC_smoke`: remains watch; promote only if CenterC alignment proxy correlates with failures.
"""
    write_text(OUT_ROOT / "round15_external_method_readiness_notes.md", external_notes)
    stage_status = "pass" if all(
        (not r.get("required", True)) or bool(r.get("exists"))
        for r in reproducibility
        if isinstance(r.get("exists"), bool)
    ) else "watch"
    any_trainable_ready = any(
        str(r.get("status", "")).startswith("pass") and str(r.get("eligible_for_fold0_very_short", "")).startswith("gate_pending")
        for r in smoke
    )
    decision = f"""# Round15 Decision Table

| stage | status | evidence | next_action |
| --- | --- | --- | --- |
| `round15_reproducibility_and_candidate_registry_gate` | `{stage_status}` | registry, batch matrix, and reproducibility files written | proceed only for candidates with clean smoke |
| `candidate_compliance_and_metadata_audit` | `pass_first_party_postpone_external` | A-E are first-party/no external data; F-J require future license/pretrained-data/dependency audit | do not clone/download before explicit gate |
| `candidate_import_and_onecase_smoke` | `{'watch_ready_for_candidate_implementation' if any_trainable_ready else 'watch_no_fold0_jobs'}` | first-party feature/gradient smoke rows written | implement candidate-specific fold0 very-short entrypoints only for passing A-E candidates |
| `first_batch_fold0_very_short_jobs` | `not_started` | no Slurm submitted by this diagnostic script | generate jobs only after candidate-specific configs/scripts are implemented |

Current recommendation: continue Round15 by implementing the best first-party candidate entrypoints in this order: R15_C or R15_A, then R15_B, then R15_D/E as auxiliary/watch. External candidates remain metadata-only until compliance is explicit.
"""
    write_text(OUT_ROOT / "round15_decision_table.md", decision)
    recommendation = """# Round15 To Round16 Recommendation Draft

Round15 is not complete yet. Stage 1-3 diagnostics established the registry and low-risk first-party smokes. The next execution step is candidate-specific implementation for the highest-priority first-party routes, followed by fold0 very-short htzhulab jobs only after their configs, one-batch checks, and cache isolation are verified.

Do not submit validation, do not expand folds, and do not run external repo training. If first-party intensity/anatomy candidates fail the very-short gate, Round16 should narrow the deep-research question around CenterC/T2 edema representation and external method readiness rather than continue generic refiner/calibrator epochs.
"""
    write_text(OUT_ROOT / "round15_round16_recommendation.md", recommendation)
    write_text(
        OUT_ROOT / "round15_deep_research_need_assessment.md",
        "# Round15 Deep Research Need Assessment\n\n"
        "Current evidence does not yet justify a new broad literature sweep. The immediate need is to execute the registered first-party fold0 very-short candidates. If A/C intensity-support routes and B anatomy-consistency route both fail, then a narrower Round16 DeepResearch pass should focus on CenterC/T2 edema representation, intensity-prior reliability, label ambiguity, and missing-modality supervision.\n",
    )


def write_train_placeholders() -> None:
    cfg_root = OUT_ROOT / "round15_train_configs"
    cfg_root.mkdir(parents=True, exist_ok=True)
    for c in candidates():
        if c.candidate_id.startswith(("R15_A", "R15_B", "R15_C", "R15_D", "R15_E")):
            text = "\n".join(
                [
                    f"candidate_id: {c.candidate_id}",
                    f"mechanism_slot: {c.mechanism_slot}",
                    "status: placeholder_pending_candidate_specific_implementation",
                    "fold: 0",
                    "seed: 15015",
                    "baseline_reference: nnUNet501 fold0/out-of-fold reference",
                    "output_dir: " + c.expected_output_dir,
                    "slurm_submission: forbidden_until_onecase_and_config_gate_pass",
                    "validation_zip: forbidden",
                    "fold_expansion: forbidden",
                    "",
                ]
            )
            write_text(cfg_root / f"{c.candidate_id}.yaml", text)
    write_csv(
        OUT_ROOT / "round15_job_scripts_manifest.csv",
        [
            {
                "candidate_id": c.candidate_id,
                "job_script": "jobs/nnUNet/laneA_round15_feature_head_fold0_very_short.sh"
                if c.candidate_id.startswith(("R15_A", "R15_B", "R15_C"))
                else "",
                "status": "created_ready_for_gated_submission"
                if c.candidate_id.startswith(("R15_A", "R15_B", "R15_C"))
                else "not_created_until_candidate_specific_implementation_and_gate",
                "slurm_job_id": "",
            }
            for c in candidates()
        ],
    )
    write_csv(
        OUT_ROOT / "round15_submitted_jobs_manifest.csv",
        [
            {
                "candidate_id": c.candidate_id,
                "submitted": False,
                "slurm_job_id": "",
                "reason": "no Slurm submission in Stage1-3 diagnostics",
            }
            for c in candidates()
        ],
    )


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    registry = candidate_rows()
    compliance = compliance_rows()
    batch = batch_rows()
    reproducibility = reproducibility_rows(cases)
    smoke = onecase_smoke_rows(cases)

    write_csv(OUT_ROOT / "round15_candidate_registry.csv", registry)
    write_csv(OUT_ROOT / "round15_compliance_metadata_matrix.csv", compliance)
    write_csv(OUT_ROOT / "round15_batch_job_matrix.csv", batch)
    write_csv(OUT_ROOT / "round15_reproducibility_gate.csv", reproducibility)
    write_csv(OUT_ROOT / "round15_onecase_smoke_summary.csv", smoke)
    write_train_placeholders()
    write_markdown_outputs(reproducibility, registry, compliance, batch, smoke)

    print(f"Wrote Round15 diagnostics to {OUT_ROOT}")
    print("No Slurm submitted. No training. No validation zip/upload. No external clone/download.")


if __name__ == "__main__":
    main()
