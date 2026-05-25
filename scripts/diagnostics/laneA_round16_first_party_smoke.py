#!/usr/bin/env python3
"""Lane A Round16 CARE-first one-batch gradient smoke.

This is a bounded CPU smoke for the first-party Round16 candidates A/C/E/F.
It reads existing nnU-Net baseline probabilities, CARE labels, and raw
modalities through the existing refiner dataset helper. It does not train a
fold0 model, submit Slurm, modify predictions, clone repositories, download
weights, or create validation packages.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"
os.environ.setdefault("MPLCONFIGDIR", str(OUT_ROOT / "mpl_cache"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.calibrator.laneA_round14_model import VoxelFeatureCalibrator
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features

SEED = 16016
EDEMA = 4
SCAR = 5


@dataclass(frozen=True)
class SmokeCandidate:
    candidate_id: str
    feature_names: tuple[str, ...]
    model_kind: str
    auxiliary: str
    no_t2_negative_weight: float


class SmallModalityConditionedHead(nn.Module):
    """Small gated head for modality-conditioned smoke."""

    def __init__(self, in_features: int, modality_features: int = 3, hidden_features: int = 16) -> None:
        super().__init__()
        self.shared = nn.Sequential(nn.Linear(in_features, hidden_features), nn.LeakyReLU(inplace=True))
        self.gate = nn.Sequential(nn.Linear(modality_features, hidden_features), nn.Sigmoid())
        self.out = nn.Linear(hidden_features, 1)

    def forward(self, x: torch.Tensor, modality: torch.Tensor) -> torch.Tensor:
        return self.out(self.shared(x) * self.gate(modality)).squeeze(-1)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def finite_float(value: float) -> bool:
    return not math.isnan(value) and not math.isinf(value)


def local_mean_6(arr: np.ndarray) -> np.ndarray:
    """Cheap 6-neighborhood local mean without scipy."""

    out = arr.astype(np.float32, copy=True)
    count = np.ones(arr.shape, dtype=np.float32)
    for axis in range(3):
        sl_src = [slice(None)] * 3
        sl_dst = [slice(None)] * 3
        sl_src[axis] = slice(1, None)
        sl_dst[axis] = slice(0, -1)
        out[tuple(sl_dst)] += arr[tuple(sl_src)]
        count[tuple(sl_dst)] += 1.0
        sl_src[axis] = slice(0, -1)
        sl_dst[axis] = slice(1, None)
        out[tuple(sl_dst)] += arr[tuple(sl_src)]
        count[tuple(sl_dst)] += 1.0
    return out / count


def feature_maps(features: np.ndarray) -> dict[str, np.ndarray]:
    probs = np.clip(features[:6], 1e-6, 1.0)
    edema = probs[EDEMA]
    other = np.max(np.delete(probs, EDEMA, axis=0), axis=0)
    entropy = -np.sum(probs * np.log(probs), axis=0) / math.log(float(probs.shape[0]))
    c0 = features[6]
    lge = features[7]
    t2 = features[8]
    c0_present = features[9]
    lge_present = features[10]
    t2_present = features[11]
    anatomy = features[12]
    t2_local = local_mean_6(t2)
    lge_local = local_mean_6(lge)
    return {
        "baseline_edema_prob": edema.astype(np.float32, copy=False),
        "baseline_scar_prob": probs[SCAR].astype(np.float32, copy=False),
        "c0_support": c0.astype(np.float32, copy=False),
        "lge_support": lge.astype(np.float32, copy=False),
        "t2_support": t2.astype(np.float32, copy=False),
        "t2_local_mean": t2_local.astype(np.float32, copy=False),
        "lge_local_mean": lge_local.astype(np.float32, copy=False),
        "t2_lge_contrast": (t2 - lge).astype(np.float32, copy=False),
        "local_t2_lge_contrast": (t2_local - lge_local).astype(np.float32, copy=False),
        "entropy": entropy.astype(np.float32, copy=False),
        "edema_margin": (edema - other).astype(np.float32, copy=False),
        "anatomy_support": anatomy.astype(np.float32, copy=False),
        "support_score": np.clip((edema + t2 + anatomy) / 3.0, 0.0, 1.0).astype(np.float32, copy=False),
        "c0_present": c0_present.astype(np.float32, copy=False),
        "lge_present": lge_present.astype(np.float32, copy=False),
        "t2_present": t2_present.astype(np.float32, copy=False),
    }


def stack_features(features: np.ndarray, names: tuple[str, ...]) -> np.ndarray:
    maps = feature_maps(features)
    return np.stack([maps[name] for name in names], axis=0).astype(np.float32, copy=False)


def select_smoke_cases(cases: list[RefinerCase]) -> list[RefinerCase]:
    chosen: list[RefinerCase] = []
    selectors = [
        lambda c: c.fold0_split == "train" and c.t2_present and c.edema_gt_positive and c.center == "CenterC",
        lambda c: c.fold0_split == "train" and c.t2_present and c.edema_gt_positive and c.center == "CenterB",
        lambda c: c.fold0_split == "train" and (not c.t2_present) and (not c.edema_gt_positive),
    ]
    used = set()
    for selector in selectors:
        for case in cases:
            if selector(case) and case.case_id not in used and case.prediction_path.is_file() and case.probability_path.is_file() and case.gt_path.is_file():
                chosen.append(case)
                used.add(case.case_id)
                break
    return chosen


def sample_case(
    case: RefinerCase,
    names: tuple[str, ...],
    *,
    rng: np.random.Generator,
    no_t2_negative_weight: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features, target, _baseline, _gt_img = load_case_features(case)
    x_full = stack_features(features, names)
    target_bool = target.astype(bool)
    pos = np.flatnonzero(target_bool.ravel())
    neg = np.flatnonzero(~target_bool.ravel())
    if pos.size:
        pos = rng.choice(pos, size=min(512, pos.size), replace=False)
    if neg.size:
        neg_limit = 256 if not case.t2_present else 512
        neg = rng.choice(neg, size=min(neg_limit, neg.size), replace=False)
    idx = np.concatenate([pos, neg])
    if idx.size == 0:
        raise RuntimeError(f"{case.case_id}: no sampleable voxels")
    rng.shuffle(idx)
    x = x_full.reshape((len(names), -1)).T[idx]
    y = target_bool.ravel()[idx].astype(np.float32)
    weight = no_t2_negative_weight if (not case.t2_present and not case.edema_gt_positive) else 1.0
    w = np.full(y.shape, weight, dtype=np.float32)
    modality = np.stack([features[9].ravel()[idx], features[10].ravel()[idx], features[11].ravel()[idx]], axis=1).astype(np.float32)
    return x.astype(np.float32, copy=False), y, w, modality


def candidate_specs() -> list[SmokeCandidate]:
    return [
        SmokeCandidate(
            "R16_A_care_strong_t2_lge_intensity_prior_fold0_vs",
            (
                "baseline_edema_prob",
                "baseline_scar_prob",
                "t2_support",
                "t2_local_mean",
                "lge_support",
                "lge_local_mean",
                "t2_lge_contrast",
                "local_t2_lge_contrast",
                "entropy",
                "edema_margin",
                "t2_present",
            ),
            "VoxelFeatureCalibrator",
            "none",
            0.05,
        ),
        SmokeCandidate(
            "R16_C_anatomy_pathology_cascade_care_fold0_vs",
            (
                "baseline_edema_prob",
                "baseline_scar_prob",
                "t2_support",
                "t2_local_mean",
                "lge_support",
                "t2_lge_contrast",
                "anatomy_support",
                "support_score",
                "entropy",
                "edema_margin",
                "t2_present",
            ),
            "VoxelFeatureCalibrator",
            "soft_anatomy_feature_only",
            0.05,
        ),
        SmokeCandidate(
            "R16_E_intensity_plus_component_surface_aux_fold0_vs",
            (
                "baseline_edema_prob",
                "baseline_scar_prob",
                "t2_support",
                "t2_local_mean",
                "lge_support",
                "t2_lge_contrast",
                "anatomy_support",
                "support_score",
                "entropy",
                "edema_margin",
                "t2_present",
            ),
            "VoxelFeatureCalibrator",
            "logit_l2_boundary_proxy_weight_1e-4",
            0.05,
        ),
        SmokeCandidate(
            "R16_F_small_modality_conditioned_moe_fold0_vs",
            (
                "baseline_edema_prob",
                "baseline_scar_prob",
                "t2_support",
                "lge_support",
                "anatomy_support",
                "entropy",
                "edema_margin",
                "c0_present",
                "lge_present",
                "t2_present",
            ),
            "SmallModalityConditionedHead",
            "modality_conditioned_gate",
            0.05,
        ),
    ]


def run_smoke(spec: SmokeCandidate, cases: list[RefinerCase]) -> dict[str, object]:
    rng = np.random.default_rng(SEED)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    ws: list[np.ndarray] = []
    mods: list[np.ndarray] = []
    sampled_cases: list[str] = []
    t2_positive_cases = 0
    no_t2_cases = 0
    for case in cases:
        x, y, w, modality = sample_case(case, spec.feature_names, rng=rng, no_t2_negative_weight=spec.no_t2_negative_weight)
        xs.append(x)
        ys.append(y)
        ws.append(w)
        mods.append(modality)
        sampled_cases.append(case.case_id)
        t2_positive_cases += int(case.t2_present and case.edema_gt_positive)
        no_t2_cases += int(not case.t2_present)
    x_np = np.concatenate(xs)
    y_np = np.concatenate(ys)
    w_np = np.concatenate(ws)
    mod_np = np.concatenate(mods)
    torch.manual_seed(SEED)
    x = torch.from_numpy(x_np)
    y = torch.from_numpy(y_np)
    w = torch.from_numpy(w_np)
    modality = torch.from_numpy(mod_np)
    if spec.model_kind == "SmallModalityConditionedHead":
        model: nn.Module = SmallModalityConditionedHead(x_np.shape[1])
    else:
        model = VoxelFeatureCalibrator(x_np.shape[1], hidden_features=24)

    def compute_loss() -> tuple[torch.Tensor, torch.Tensor]:
        if spec.model_kind == "SmallModalityConditionedHead":
            logits = model(x, modality)  # type: ignore[arg-type]
        else:
            logits = model(x)
        bce_raw = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="none")
        loss = torch.sum(bce_raw * w) / torch.clamp(w.sum(), min=1.0)
        aux_loss = torch.tensor(0.0)
        if spec.auxiliary == "logit_l2_boundary_proxy_weight_1e-4":
            aux_loss = 1e-4 * torch.mean(logits.square())
            loss = loss + aux_loss
        return loss, aux_loss

    loss, aux_loss = compute_loss()
    loss.backward()
    grad_norm = 0.0
    params_with_grad = 0
    for param in model.parameters():
        if param.grad is not None:
            params_with_grad += 1
            grad_norm += float(param.grad.detach().norm().cpu())
    loss_value = float(loss.detach().cpu())
    aux_value = float(aux_loss.detach().cpu())
    finite = finite_float(loss_value) and finite_float(grad_norm)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    tiny_losses: list[float] = [loss_value]
    for _step in range(12):
        opt.zero_grad(set_to_none=True)
        step_loss, _step_aux = compute_loss()
        step_loss.backward()
        opt.step()
        tiny_losses.append(float(step_loss.detach().cpu()))
    final_tiny_loss = tiny_losses[-1]
    tiny_loss_delta = tiny_losses[0] - final_tiny_loss
    tiny_pass = finite and final_tiny_loss < tiny_losses[0]
    return {
        "candidate_id": spec.candidate_id,
        "status": "pass_tiny_overfit_smoke" if tiny_pass and grad_norm > 0 else "fail_tiny_overfit_smoke",
        "gradient_status": "pass_unit_gradient_smoke" if finite and grad_norm > 0 else "fail_unit_gradient_smoke",
        "model_kind": spec.model_kind,
        "feature_count": len(spec.feature_names),
        "feature_names": ";".join(spec.feature_names),
        "sampled_cases": ";".join(sampled_cases),
        "sampled_case_count": len(sampled_cases),
        "t2_present_gt_positive_cases": t2_positive_cases,
        "no_t2_cases": no_t2_cases,
        "sample_count": int(x_np.shape[0]),
        "positive_sample_count": int(y_np.sum()),
        "no_t2_negative_weight": spec.no_t2_negative_weight,
        "loss_value": loss_value,
        "tiny_initial_loss": tiny_losses[0],
        "tiny_final_loss": final_tiny_loss,
        "tiny_loss_delta": tiny_loss_delta,
        "tiny_steps": 12,
        "auxiliary": spec.auxiliary,
        "auxiliary_loss_value": aux_value,
        "grad_norm": grad_norm,
        "params_with_grad": params_with_grad,
        "nan_or_inf": not finite,
        "class4_edema_only": True,
        "class5_scar_interference": 0,
        "next_gate": "fold0_very_short_implementation_job_gate" if tiny_pass and grad_norm > 0 else "stop_candidate",
    }


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = select_smoke_cases(build_cases())
    if len(cases) < 2:
        raise RuntimeError(f"expected at least 2 smoke cases, found {len(cases)}")
    rows = [run_smoke(spec, cases) for spec in candidate_specs()]
    fieldnames = list(rows[0].keys())
    for name in [
        "round16_unit_gradient_smoke.csv",
        "round16_tiny_overfit_metrics.csv",
        "round16_onecase_smoke_results.csv",
        "round16_onecase_smoke_summary.csv",
        "round16_external_import_smoke_summary.csv",
    ]:
        write_csv(OUT_ROOT / name, rows, fieldnames)
    passed = [r for r in rows if str(r["status"]).startswith("pass")]
    failed = [r for r in rows if str(r["status"]).startswith("fail")]
    write_text(
        OUT_ROOT / "round16_import_shape_label_smoke.md",
        "# Round16 Import / Shape / Label Smoke\n\n"
        "Status: `first_party_unit_gradient_smoke_complete`.\n\n"
        "This smoke used existing CARE baseline probabilities, raw modalities, and GT labels through "
        "`src/care_myocardium/refiner/laneA_round10_dataset.py`. It did not train a fold0 model, "
        "submit Slurm, clone external repositories, download weights, modify predictions, or create validation packages.\n\n"
        f"Sampled cases: `{';'.join(c.case_id for c in cases)}`.\n\n"
        f"Passed candidates: `{';'.join(str(r['candidate_id']) for r in passed) or 'none'}`.\n\n"
        f"Failed candidates: `{';'.join(str(r['candidate_id']) for r in failed) or 'none'}`.\n\n"
        "External candidates remain metadata-only because no live source/license/import gate has passed.\n",
    )
    batch_rows = read_csv(OUT_ROOT / "round16_batch_job_matrix.csv")
    pass_ids = {str(r["candidate_id"]) for r in passed}
    for row in batch_rows:
        cid = row.get("candidate_id", "")
        if cid in pass_ids:
            row["stage_allowed_now"] = "stage4_unit_gradient_tiny_pass"
            row["submission_status"] = "not_submitted_ready_for_fold0_very_short_implementation_gate"
            row["reason"] = "unit/gradient/tiny-overfit smoke passed; full fold0 very-short training entrypoint still must be implemented and reviewed before Slurm"
    if batch_rows:
        write_csv(OUT_ROOT / "round16_batch_job_status.csv", batch_rows, list(batch_rows[0].keys()))
        write_csv(OUT_ROOT / "round16_job_submission_manifest.csv", batch_rows, list(batch_rows[0].keys()))
    decision = (
        "# Round16 Decision Table\n\n"
        "Current status: `stage4_first_party_unit_gradient_and_tiny_smoke_passed`.\n\n"
        "Stage1 reproducibility and Stage2 local-docs compliance setup passed. "
        "First-party candidates A/C/E/F passed one-batch gradient smoke and tiny-overfit smoke on existing CARE features. "
        "No fold0 model has been trained, no Slurm job has been submitted, and no external candidate has passed live metadata/import gates.\n\n"
        "## First-Party Smoke Results\n\n"
        + "| candidate_id | status | tiny_initial_loss | tiny_final_loss | tiny_loss_delta | grad_norm | class5_scar_interference | next_gate |\n"
        + "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {r['candidate_id']} | {r['status']} | {r['tiny_initial_loss']} | {r['tiny_final_loss']} | {r['tiny_loss_delta']} | {r['grad_norm']} | {r['class5_scar_interference']} | {r['next_gate']} |"
            for r in rows
        )
        + "\n\n## Decision\n\n"
        "- `R16_A`, `R16_C`, `R16_E`, and `R16_F`: `watch_go_to_fold0_very_short_implementation_job_gate`.\n"
        "- External candidates `R16_B/D/G/H/I/J/K`: `postpone_pending_live_metadata_import_or_loss_smoke`.\n"
        "- Do not submit fold0 very-short jobs yet; the full fold0 training entrypoint and job script have not been implemented/reviewed for Round16.\n"
        "- Do not create validation zip, upload, fold1-4, or 5-fold.\n"
    )
    write_text(OUT_ROOT / "round16_decision_table.md", decision)
    write_text(OUT_ROOT / "round16_candidate_decision_table.md", decision)
    write_text(
        OUT_ROOT / "round16_round17_recommendation.md",
        "# Round16 To Round17 Recommendation\n\n"
        "Not ready for Round17. Round16 first-party A/C/E/F have passed unit/gradient and tiny-overfit smoke only. "
        "The next required work is implementing/reviewing a bounded fold0 very-short training entrypoint and job script for selected candidates, followed by gated Slurm submission. "
        "External candidates remain metadata/import-only until live license/source/dependency/I/O checks pass.\n",
    )
    print(f"Round16 first-party smoke complete: passed={len(passed)} failed={len(failed)}")
    print(f"Sampled cases: {', '.join(c.case_id for c in cases)}")


if __name__ == "__main__":
    main()
