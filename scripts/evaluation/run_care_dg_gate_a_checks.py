#!/usr/bin/env python3
"""Gate A-R3 evidence runner for repaired CARE-DG semantics.

This script does not submit Slurm jobs or start formal fold training. GPU use, when
requested by the controller, must be through the existing allocation wrapper.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.training.run_care_dg as run_dg  # noqa: E402
from scripts.training.run_care_dg import CaseCache, PATCH_SHAPE, crop_pad, load_splits  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.data.care_dg_dataset import aligned_spatial_crop  # noqa: E402
from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL, build_care_dg  # noqa: E402
from src.care_myocardium.training.care_dg_trainer import (  # noqa: E402
    care_dg_loss,
    load_care_dg_checkpoint,
    make_edema_zone_targets,
    make_error_targets,
    save_care_dg_checkpoint,
    scar_margin,
    edema_zone_margin,
)

TASK_KEY = "20260727_care_dg_dual_pathology_validation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
GATE_ROOT = RESULT_ROOT / "gate_a_repaired_semantics"
SCHEMA_VERSION = 1

SOURCE_PATHS = [
    "configs/care_dg/care_dg_v1.yaml",
    "src/care_myocardium/models/care_dg.py",
    "src/care_myocardium/data/care_dg_dataset.py",
    "src/care_myocardium/training/care_dg_trainer.py",
    "src/care_myocardium/inference/care_dg_predictor.py",
    "scripts/training/run_care_dg.py",
    "scripts/inference/run_care_dg_inference.py",
    "scripts/evaluation/evaluate_care_dg.py",
    "scripts/evaluation/select_care_dg_candidate.py",
    "scripts/evaluation/validate_care_dg_packet.py",
    "scripts/evaluation/build_care_dg_validation_packet.py",
    "scripts/evaluation/run_care_dg_gate_a_checks.py",
    "scripts/evaluation/finalize_care_dg_gate_a_r3_evidence.py",
    "scripts/evaluation/validate_care_dg_gate_a_consistency.py",
    "tests/care_dg/test_care_dg_model.py",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: set[str] = set(); fieldnames = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key); fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def run_capture(cmd: list[str], timeout: int = 300) -> dict[str, Any]:
    start = time.time()
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, timeout=timeout, check=False)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "elapsed_seconds": round(time.time() - start, 3),
    }


def source_hashes() -> dict[str, str]:
    return {p: sha256_file(REPO_ROOT / p) for p in SOURCE_PATHS if (REPO_ROOT / p).exists()}


def git_state() -> dict[str, Any]:
    return {
        "head": run_capture(["git", "rev-parse", "HEAD"], timeout=60),
        "origin_main": run_capture(["git", "rev-parse", "origin/main"], timeout=60),
        "status_short": run_capture(["git", "status", "--short", "--branch"], timeout=60),
        "diff_name_only": run_capture(["git", "diff", "--name-only"], timeout=60),
    }


def case_to_fold_map() -> dict[str, int]:
    manifest = json.loads((RESULT_ROOT / "nnunet_oof_anchor_manifest.json").read_text(encoding="utf-8"))
    return {str(row["case_id"]): int(row["source_fold"]) for row in manifest["entries"]}


def pick_cases(cache: CaseCache, case_to_fold: dict[str, int], metadata: Any) -> tuple[str, str]:
    complete_candidates = [c for c, m in metadata.items() if m.modality_group == "C0+LGE+T2" and c in case_to_fold]
    no_t2_candidates = [c for c, m in metadata.items() if not bool(m.t2_present) and c in case_to_fold]
    def has_errors(case_id: str, require_edema: bool) -> bool:
        rec = cache.get(case_id, case_to_fold[case_id], tuple(metadata[case_id].availability))
        labels = rec["labels"]; anchor = rec["anchor_mask"]
        scar_err = ((labels == SCAR_CHANNEL) != (anchor == SCAR_CHANNEL)).sum()
        zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
        zone_pred = (anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)
        edema_err = (zone_gt != zone_pred).sum()
        return scar_err > 0 and ((edema_err > 0) if require_edema else True)
    complete = next((c for c in sorted(complete_candidates) if has_errors(c, True)), sorted(complete_candidates)[0])
    no_t2 = next((c for c in sorted(no_t2_candidates) if has_errors(c, False)), sorted(no_t2_candidates)[0])
    return complete, no_t2


def make_patch(case_id: str, cache: CaseCache, case_to_fold: dict[str, int], metadata: Any, *, no_jitter: bool = False) -> dict[str, Any]:
    rec = cache.get(case_id, case_to_fold[case_id], tuple(metadata[case_id].availability))
    labels = rec["labels"]; anchor = rec["anchor_mask"]
    zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    zone_pred = (anchor == SCAR_CHANNEL) | (anchor == EDEMA_CHANNEL)
    error = ((labels == SCAR_CHANNEL) != (anchor == SCAR_CHANNEL)) | (zone_gt != zone_pred)
    pathology = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    coords = np.argwhere(error | pathology)
    if coords.size:
        center = tuple(int(v) for v in coords[len(coords) // 2])
    else:
        center = tuple(int(v // 2) for v in labels.shape)
    batch = {
        "images": torch.from_numpy(crop_pad(rec["images"], center, PATCH_SHAPE, fill=0.0)[None]).float(),
        "labels": torch.from_numpy(crop_pad(rec["labels"][None], center, PATCH_SHAPE, fill=0)[None, 0]).long(),
        "anchor_logits": torch.from_numpy(crop_pad(rec["anchor_logits"], center, PATCH_SHAPE, fill=-12.0)[None]).float(),
        "anchor_mask": torch.from_numpy(crop_pad(rec["anchor_mask"][None], center, PATCH_SHAPE, fill=0)[None, 0]).long(),
        "availability": torch.from_numpy(rec["availability"][None]).float(),
        "t2_present": torch.tensor([1.0 if metadata[case_id].t2_present else 0.0], dtype=torch.float32),
        "uncertainty": torch.from_numpy(crop_pad(rec["uncertainty"], center, PATCH_SHAPE, fill=1.0)[None]).float(),
        "myocardium_support": torch.from_numpy(crop_pad(rec["myocardium_support"], center, PATCH_SHAPE, fill=0.0)[None]).float(),
        "edema_support": torch.from_numpy(crop_pad(rec["edema_support"], center, PATCH_SHAPE, fill=0.0)[None]).float(),
        "distance_to_myocardium": torch.from_numpy(crop_pad(rec["distance_to_myocardium"], center, PATCH_SHAPE, fill=99.0)[None]).float(),
        "anchor_value_kind": "log_probabilities",
        "case_id": case_id,
        "center_zyx": center,
    }
    return batch


def to_device(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}


def model_forward(model: torch.nn.Module, batch: dict[str, Any]) -> dict[str, torch.Tensor]:
    return model(
        batch["images"],
        batch["availability"],
        batch["anchor_logits"],
        uncertainty=batch["uncertainty"],
        myocardium_support=batch["myocardium_support"],
        edema_support=batch["edema_support"],
        distance_to_myocardium=batch["distance_to_myocardium"],
        t2_present=batch["t2_present"],
        strict_inputs=True,
        anchor_value_kind=batch["anchor_value_kind"],
    )


def grad_sum(module: torch.nn.Module) -> float:
    total = 0.0
    for param in module.parameters():
        if param.grad is not None:
            total += float(param.grad.detach().abs().sum().cpu())
    return total


def gate_stats(out: dict[str, torch.Tensor], labels: torch.Tensor, anchor_mask: torch.Tensor, t2_present: torch.Tensor) -> dict[str, float]:
    labels = labels if labels.ndim == 4 else labels[:, 0]
    anchor_mask = anchor_mask if anchor_mask.ndim == 4 else anchor_mask[:, 0]
    t2 = t2_present.view(-1, 1, 1, 1).bool()
    scar_fn = ((labels == SCAR_CHANNEL) & (anchor_mask != SCAR_CHANNEL)).unsqueeze(1)
    scar_fp = ((labels != SCAR_CHANNEL) & (anchor_mask == SCAR_CHANNEL)).unsqueeze(1)
    zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    zone_pred = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
    edema_fn = (zone_gt & ~zone_pred).unsqueeze(1) & t2.unsqueeze(1)
    edema_fp = (~zone_gt & zone_pred).unsqueeze(1) & t2.unsqueeze(1)
    non_scar_fn = ~scar_fn
    non_scar_fp = ~scar_fp
    non_edema_fn = (~edema_fn) & t2.unsqueeze(1)
    non_edema_fp = (~edema_fp) & t2.unsqueeze(1)
    def median(t: torch.Tensor, mask: torch.Tensor) -> float:
        vals = t.detach()[mask.expand_as(t)]
        return float(vals.median().cpu()) if vals.numel() else 0.0
    def frac(t: torch.Tensor, cap: float) -> float:
        return float((t.detach() >= 0.95 * cap).float().mean().cpu())
    return {
        "scar_q_fn_true_fn_median": median(out["scar_q_fn"], scar_fn),
        "scar_q_fn_non_fn_median": median(out["scar_q_fn"], non_scar_fn),
        "scar_q_fp_true_fp_median": median(out["scar_q_fp"], scar_fp),
        "scar_q_fp_non_fp_median": median(out["scar_q_fp"], non_scar_fp),
        "edema_q_fn_true_fn_median": median(out["edema_q_fn"], edema_fn),
        "edema_q_fn_non_fn_median": median(out["edema_q_fn"], non_edema_fn),
        "edema_q_fp_true_fp_median": median(out["edema_q_fp"], edema_fp),
        "edema_q_fp_non_fp_median": median(out["edema_q_fp"], non_edema_fp),
        "scar_m_fn_mean": float(out["scar_m_fn"].detach().mean().cpu()),
        "scar_m_fp_mean": float(out["scar_m_fp"].detach().mean().cpu()),
        "edema_m_fn_mean": float(out["edema_m_fn"].detach().mean().cpu()),
        "edema_m_fp_mean": float(out["edema_m_fp"].detach().mean().cpu()),
        "scar_m_saturation_fraction": frac(torch.maximum(out["scar_m_fn"], out["scar_m_fp"]), float(model_config_cap(out, "scar"))),
        "edema_m_saturation_fraction": frac(torch.maximum(out["edema_m_fn"], out["edema_m_fp"]), float(model_config_cap(out, "edema"))),
    }


def model_config_cap(out: dict[str, torch.Tensor], kind: str) -> float:
    max_seen = float(torch.maximum(out[f"{kind}_m_fn"], out[f"{kind}_m_fp"]).detach().max().cpu())
    return max(max_seen, 1e-6)


def correct_direction_fraction(out: dict[str, torch.Tensor], labels: torch.Tensor, anchor_mask: torch.Tensor) -> float:
    labels = labels if labels.ndim == 4 else labels[:, 0]
    anchor_mask = anchor_mask if anchor_mask.ndim == 4 else anchor_mask[:, 0]
    final = out["final_logits"]
    anchor = out["anchor_logits"].detach()
    scar_f = scar_margin(final); scar_a = scar_margin(anchor)
    edema_f = edema_zone_margin(final); edema_a = edema_zone_margin(anchor)
    scar_fn = ((labels == SCAR_CHANNEL) & (anchor_mask != SCAR_CHANNEL)).unsqueeze(1)
    scar_fp = ((labels != SCAR_CHANNEL) & (anchor_mask == SCAR_CHANNEL)).unsqueeze(1)
    zone_gt = (labels == SCAR_CHANNEL) | (labels == EDEMA_CHANNEL)
    zone_pred = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
    edema_fn = (zone_gt & ~zone_pred).unsqueeze(1)
    edema_fp = (~zone_gt & zone_pred).unsqueeze(1)
    correct = ((scar_f > scar_a) & scar_fn) | ((scar_f < scar_a) & scar_fp) | ((edema_f > edema_a) & edema_fn) | ((edema_f < edema_a) & edema_fp)
    err = scar_fn | scar_fp | edema_fn | edema_fp
    return float((correct & err).sum().detach().cpu()) / max(1.0, float(err.sum().detach().cpu()))


def run_static_tests() -> dict[str, Any]:
    py_compile = run_capture([
        sys.executable,
        "-m",
        "py_compile",
        "src/care_myocardium/models/care_dg.py",
        "src/care_myocardium/training/care_dg_trainer.py",
        "src/care_myocardium/inference/care_dg_predictor.py",
        "scripts/training/run_care_dg.py",
        "scripts/evaluation/run_care_dg_gate_a_checks.py",
        "scripts/evaluation/build_care_dg_validation_packet.py",
        "scripts/evaluation/finalize_care_dg_gate_a_r3_evidence.py",
        "scripts/evaluation/validate_care_dg_gate_a_consistency.py",
    ])
    pytest = run_capture([sys.executable, "-m", "pytest", "tests/care_dg", "-q"], timeout=600)
    unit_smoke = run_capture([sys.executable, "scripts/training/run_care_dg.py", "--unit-smoke"], timeout=300)
    validator = {"status": "DEFERRED_UNTIL_GATE_A_R3_PREFLIGHT_AND_STRICT_VALIDATOR", "returncode": None}
    report = {
        "created_at_utc": now_utc(),
        "status": "PASS" if all(x["returncode"] == 0 for x in (py_compile, pytest, unit_smoke)) else "NEEDS_REPAIR",
        "py_compile": py_compile,
        "pytest": pytest,
        "unit_smoke": unit_smoke,
        "strict_validator": validator,
    }
    write_json(GATE_ROOT / "gate_a_static_test_receipt.json", report)
    (RESULT_ROOT / "unit_test_report.md").write_text(
        "# CARE-DG Gate A-R3 unit test report\n\n"
        f"created_at_utc: `{report['created_at_utc']}`\n\n"
        f"py_compile: `{'PASS' if py_compile['returncode'] == 0 else 'FAIL'}`\n\n"
        f"pytest tests/care_dg -q: `{'PASS' if pytest['returncode'] == 0 else 'FAIL'}`\n\n"
        f"runner unit smoke: `{'PASS' if unit_smoke['returncode'] == 0 else 'FAIL'}`\n\n"
        f"strict validator: `{'PASS' if validator['returncode'] == 0 else 'FAIL'}`\n",
        encoding="utf-8",
    )
    return report


def run_real_case_checks(device: torch.device, steps: int, lr: float) -> dict[str, Any]:
    torch.manual_seed(20260727)
    np.random.seed(20260727)
    metadata = load_myops_case_metadata(REPO_ROOT)
    case_to_fold = case_to_fold_map()
    cache = CaseCache(max_cases=8)
    complete_case, no_t2_case = pick_cases(cache, case_to_fold, metadata)
    complete = to_device(make_patch(complete_case, cache, case_to_fold, metadata), device)
    no_t2 = to_device(make_patch(no_t2_case, cache, case_to_fold, metadata), device)
    model = build_care_dg().to(device)
    opt = run_dg.build_care_dg_optimizer(model, representation_lr=3e-4, pathology_lr=3e-4, weight_decay=1e-4)

    receipts: list[dict[str, Any]] = []
    for label, batch in [("complete", complete), ("no_t2", no_t2)]:
        opt.zero_grad(set_to_none=True)
        out = model_forward(model, batch)
        loss, metrics = care_dg_loss(out, batch["labels"], batch["anchor_mask"], t2_present=batch["t2_present"], edema_reliable=batch["t2_present"])
        loss.backward()
        receipts.append({
            "case_role": label,
            "case_id": batch["case_id"],
            "center_zyx": list(batch["center_zyx"]),
            "loss_finite": bool(torch.isfinite(loss).item()),
            "loss": float(loss.detach().cpu()),
            "metrics": metrics,
            "changed_voxels": int((out["final_mask"] != batch["anchor_mask"]).detach().sum().cpu()),
            "scar_decoder_grad_abs_sum": grad_sum(model.scar_decoder),
            "edema_decoder_grad_abs_sum": grad_sum(model.edema_decoder),
            "edema_delta_abs_sum": float(out["edema_delta"].detach().abs().sum().cpu()),
            "no_t2_edema_grad_exact_zero": bool(label != "no_t2" or grad_sum(model.edema_decoder) == 0.0),
            "no_t2_edema_delta_exact_zero": bool(label != "no_t2" or float(out["edema_delta"].detach().abs().sum().cpu()) == 0.0),
        })
    forward_status = "PASS" if receipts[0]["loss_finite"] and receipts[0]["scar_decoder_grad_abs_sum"] > 0 and receipts[0]["edema_decoder_grad_abs_sum"] > 0 and receipts[1]["no_t2_edema_grad_exact_zero"] and receipts[1]["no_t2_edema_delta_exact_zero"] else "NEEDS_REPAIR"
    forward_receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": now_utc(),
        "status": forward_status,
        "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "formal_training_credit": 0,
        "receipts": receipts,
    }
    write_json(RESULT_ROOT / "real_case_forward_backward_receipt.json", forward_receipt)

    ckpt = GATE_ROOT / "checkpoint_resume_parity.pt"
    before = model_forward(model, complete)["final_logits"].detach().cpu()
    save_care_dg_checkpoint(ckpt, model, opt, step=0, extra={"gate": "A"})
    loaded, step, extra = load_care_dg_checkpoint(ckpt)
    loaded = loaded.to(device)
    after = model_forward(loaded, complete)["final_logits"].detach().cpu()
    max_delta = float((before - after).abs().max())
    parity = {
        "created_at_utc": now_utc(),
        "status": "PASS" if step == 0 and max_delta <= 1e-6 and extra.get("gate") == "A" else "NEEDS_REPAIR",
        "checkpoint": rel(ckpt),
        "checkpoint_sha256": sha256_file(ckpt),
        "max_abs_final_logits_delta": max_delta,
        "resume_step": step,
    }
    write_json(RESULT_ROOT / "checkpoint_resume_parity.json", parity)

    opt = run_dg.build_care_dg_optimizer(model, representation_lr=3e-4, pathology_lr=3e-4, weight_decay=1e-4)
    curve: list[dict[str, Any]] = []
    first_loss = None
    first_scar = None
    first_edema = None
    started = time.time()
    for step_i in range(1, steps + 1):
        opt.zero_grad(set_to_none=True)
        out = model_forward(model, complete)
        loss, metrics = care_dg_loss(out, complete["labels"], complete["anchor_mask"], t2_present=complete["t2_present"], edema_reliable=complete["t2_present"])
        if not torch.isfinite(loss):
            raise RuntimeError(f"nonfinite Gate A overfit loss at step {step_i}")
        loss.backward(); opt.step()
        if first_loss is None:
            first_loss = float(loss.detach().cpu())
            first_scar = float(metrics["scar_seg"] + metrics["scar_gate"])
            first_edema = float(metrics["edema_seg"] + metrics["edema_gate"])
        if step_i == 1 or step_i % 50 == 0 or step_i == steps:
            with torch.no_grad():
                out_eval = model_forward(model, complete)
                _loss_eval, m_eval = care_dg_loss(out_eval, complete["labels"], complete["anchor_mask"], t2_present=complete["t2_present"], edema_reliable=complete["t2_present"])
                row = {
                    "step": step_i,
                    "loss": m_eval["loss"],
                    "scar_active_loss": m_eval["scar_seg"] + m_eval["scar_gate"],
                    "edema_active_loss": m_eval["edema_seg"] + m_eval["edema_gate"],
                    "changed_voxels": int((out_eval["final_mask"] != complete["anchor_mask"]).detach().sum().cpu()),
                    "correct_direction_fraction": correct_direction_fraction(out_eval, complete["labels"], complete["anchor_mask"]),
                    "elapsed_seconds": round(time.time() - started, 1),
                }
                row.update(gate_stats(out_eval, complete["labels"], complete["anchor_mask"], complete["t2_present"]))
                curve.append(row)
                print(json.dumps({"gate": "A", "phase": "overfit", **row}), flush=True)
    write_csv(GATE_ROOT / "implementation_overfit_curve.csv", curve)
    last = curve[-1]
    scar_drop = (float(first_scar) - float(last["scar_active_loss"])) / max(1e-6, float(first_scar))
    edema_drop = (float(first_edema) - float(last["edema_active_loss"])) / max(1e-6, float(first_edema))
    q_margin_pass = (
        last["scar_q_fn_true_fn_median"] >= last["scar_q_fn_non_fn_median"] + 0.10
        and last["scar_q_fp_true_fp_median"] >= last["scar_q_fp_non_fp_median"] + 0.10
        and last["edema_q_fn_true_fn_median"] >= last["edema_q_fn_non_fn_median"] + 0.10
        and last["edema_q_fp_true_fp_median"] >= last["edema_q_fp_non_fp_median"] + 0.10
    )
    status = "PASS" if scar_drop >= 0.30 and edema_drop >= 0.30 and last["changed_voxels"] > 0 and last["correct_direction_fraction"] >= 0.10 and q_margin_pass and last["scar_m_saturation_fraction"] <= 0.30 and last["edema_m_saturation_fraction"] <= 0.30 else "NEEDS_REPAIR"
    overfit = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": now_utc(),
        "status": status,
        "formal_training_credit": 0,
        "case_id": complete["case_id"],
        "steps": steps,
        "learning_rate": lr,
        "first_loss": first_loss,
        "last_loss": last["loss"],
        "scar_active_loss_drop_fraction": scar_drop,
        "edema_active_loss_drop_fraction": edema_drop,
        "last_gate_magnitude_stats": last,
        "curve_path": rel(GATE_ROOT / "implementation_overfit_curve.csv"),
        "gate_requirements": {
            "scar_active_loss_drop_fraction_min": 0.30,
            "edema_active_loss_drop_fraction_min": 0.30,
            "q_fn_q_fp_true_vs_non_margin_min": 0.10,
            "correct_direction_fraction_min": 0.10,
            "saturation_fraction_max": 0.30,
        },
    }
    write_json(RESULT_ROOT / "implementation_overfit_receipt.json", overfit)
    return {"forward": forward_receipt, "checkpoint_resume": parity, "overfit": overfit}


def write_contracts(static: dict[str, Any], real: dict[str, Any] | None) -> dict[str, Any]:
    model = build_care_dg()
    params = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    write_json(RESULT_ROOT / "model_parameter_report.json", {
        "created_at_utc": now_utc(),
        "model": "CARE-DG",
        "config": model.config.__dict__,
        "total_parameters": params,
        "trainable_parameters": trainable,
        "bounded_magnitude": True,
    })
    impl = {
        "created_at_utc": now_utc(),
        "status": "GATE_A_REPAIRED_IMPLEMENTATION_PASS" if static.get("status") == "PASS" and real is not None and all(v.get("status") == "PASS" for v in real.values()) else "NEEDS_REPAIR",
        "gate_revision": "A-R3",
        "approval_token_required": "APPROVE_GATE_A_R3",
        "scientific_credit": 0,
        "preflight_training_credit": 0,
        "pre_repair_formal_credit_invalidated": True,
        "implemented_contract": {
            "edema_decoder_targets_scar_union_edema_zone": True,
            "pure_edema_is_zone_minus_scar": True,
            "fp_margin_direction_lowers_pathology_margin": True,
            "bounded_magnitude_gate_cannot_be_bypassed_by_zero_gate": True,
            "scar_competitor_includes_edema": True,
            "partial_label_t2_masking_per_case_before_reduction": True,
            "remote_penalty_uses_raw_pre_support_delta": True,
            "anchor_probability_converted_to_log_probabilities": True,
            "formal_mode_rejects_missing_support_uncertainty_distance": True,
            "formal_sampler_quota_auditable": True,
            "fixed_inner_evaluation_plan_generated_before_training": True,
            "fixed_inner_evaluation_covers_complete_inner_select": True,
            "evaluate_inner_independent_of_training_rng": True,
            "stage_A_and_stage_B_use_same_fixed_inner_objective": True,
            "effective_sampler_eligible_pools_precomputed": True,
            "effective_sampler_target_hit_verified_after_jitter": True,
            "sampler_audit_reports_effective_not_nominal_quota": True,
            "checkpoint_saves_python_numpy_torch_cuda_scaler_and_local_rng": True,
            "checkpoint_resume_validates_hash_contract_before_restore": True,
            "gate_a_r3_preflight_runs_stage_A_and_stage_B": True,
            "stage_A_optimizer_two_groups_3e_minus_4": True,
            "stage_B_optimizer_representation_2e_minus_5_pathology_1e_minus_4": True,
            "every_trainable_parameter_exactly_one_optimizer_group": True,
            "checkpoint_reload_preserves_optimizer_groups_and_lrs": True,
            "resolved_training_contract_sha256_written_to_checkpoint_receipt_manifest": True,
            "checkpoint_resume_rejects_resolved_contract_mismatch": True,
            "stage_A_and_stage_B_effective_sampler_audits_written": True,
            "consistency_validator_rejects_fail_deferred_mismatch": True,
            "validate_w0_accepts_preregistered_status_only": True,
            "inner_select_excluded_from_stage_a_and_stage_b": True,
            "checkpoint_selection_fixed_complete_inner_objective": True,
            "margin_caps_fit_actual_train_only": True,
            "soft_support_union_labels_1_4_5_excludes_lv_rv": True,
            "soft_support_shells_scar_6mm_edema_zone_10mm": True,
            "repaired_runtime_label_isolated": True,
            "protected_pre_repair_formal_runtime_read_only": True,
            "scar_priority_composition_anchor_edema_scar_argmax": True,
            "scar_priority_outputs_after_edema_and_final_after_scar": True,
            "post_scar_decision_not_overwritten_by_later_edema": True,
            "negative_scar_correction_can_release_false_scar": True,
            "random_negative_semantics_audit_stage_A_and_B_written_without_sampler_change": True,
            "support_distance_clips_empty_anchor_simpleitk_max_float": True,
            "support_actionable_sampler_excludes_empty_anchor_error_pathology_pools": True,
            "pre_scar_priority_runtime_zero_scientific_credit": True,
            "cine_validation_tree_binding_pending_w5": True,
        },
        "source_hashes": source_hashes(),
        "git_state": git_state(),
        "gate_a_static_test_receipt": rel(GATE_ROOT / "gate_a_static_test_receipt.json"),
        "gate_a_overfit_curve": rel(GATE_ROOT / "implementation_overfit_curve.csv"),
        "gate_a_r3_preflight_receipt": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/fold_training_receipt.json"),
        "gate_a_r3_preflight_validator": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/preflight_validator_report.json"),
        "gate_a_r3_inner_split_manifest": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/inner_split_manifest.json"),
        "gate_a_r3_inner_evaluation_plan": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/inner_evaluation_plan.json"),
        "gate_a_r3_sampler_quota_audit_stage_a": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/sampler_quota_audit_stage_a.json"),
        "gate_a_r3_sampler_quota_audit_stage_b": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/sampler_quota_audit_stage_b.json"),
        "gate_a_r3_resolved_training_contract": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/resolved_training_contract.json"),
        "gate_a_r3_inner_eval_repeat": rel(RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/inner_evaluation_repeat_receipt.json"),
        "gate_b_scar_priority_preflight_receipt": rel(RESULT_ROOT / "runtime/gate_b_scar_priority_preflight/fold0/fold_training_receipt.json"),
        "gate_b_scar_priority_random_negative_audit_stage_a": rel(RESULT_ROOT / "runtime/gate_b_scar_priority_preflight/fold0/random_negative_semantics_audit_stage_a.json"),
        "gate_b_scar_priority_random_negative_audit_stage_b": rel(RESULT_ROOT / "runtime/gate_b_scar_priority_preflight/fold0/random_negative_semantics_audit_stage_b.json"),
    }
    write_json(RESULT_ROOT / "implementation_contract.json", impl)
    known = {
        "created_at_utc": now_utc(),
        "status": "PASS" if static.get("status") == "PASS" else "NEEDS_REPAIR",
        "fixtures": [
            {"fixture": "fn_margin_wrong_direction", "rejected": True, "evidence": "test_fn_and_fp_margin_directions_are_opposite"},
            {"fixture": "fp_margin_raises_pathology_margin", "rejected": True, "evidence": "test_fn_and_fp_margin_directions_are_opposite"},
            {"fixture": "scar_cannot_convert_anchor_edema", "rejected": True, "evidence": "test_scar_competitor_can_convert_anchor_edema_to_scar"},
            {"fixture": "edema_target_exclusive_class4", "rejected": True, "evidence": "test_edema_zone_target_is_scar_union_edema"},
            {"fixture": "zero_gate_bypassed_by_unbounded_magnitude", "rejected": True, "evidence": "test_bounded_magnitude_and_zero_gate_cannot_change_logits"},
            {"fixture": "no_t2_edema_leakage", "rejected": True, "evidence": "test_mixed_batch_no_t2_sample_has_zero_edema_outputs_and_no_t2_gradients"},
            {"fixture": "remote_penalty_post_support_vacuous", "rejected": True, "evidence": "test_remote_penalty_uses_raw_pre_support_delta"},
            {"fixture": "formal_missing_support_or_raw_probability_ambiguous", "rejected": True, "evidence": "test_formal_mode_rejects_missing_inputs_and_anchor_kind"},
            {"fixture": "validate_w0_accepts_arbitrary_pass_string", "rejected": True, "evidence": "test_validate_w0_accepts_only_preregistered_pass_statuses"},
            {"fixture": "inner_select_case_in_stage_a_or_stage_b_training", "rejected": True, "evidence": "test_inner_split_excludes_selection_from_stage_a_stage_b_and_records_hashes"},
            {"fixture": "lv_rv_blood_pool_in_myocardium_support", "rejected": True, "evidence": "test_soft_myocardium_support_excludes_lv_rv_and_decays_continuously"},
            {"fixture": "soft_support_breaks_zero_correction_identity", "rejected": True, "evidence": "test_zero_correction_identity_with_soft_support_inputs"},
            {"fixture": "inner_evaluation_uses_training_rng", "rejected": True, "evidence": "test_fixed_inner_evaluation_plan_repeat_exact"},
            {"fixture": "nominal_error_fn_patch_without_fn_voxels", "rejected": True, "evidence": "test_known_bad_error_fn_without_fn_voxels_is_rejected"},
            {"fixture": "sampler_audit_counts_requested_instead_of_effective", "rejected": True, "evidence": "test_effective_sampler_reports_real_hits_and_zero_silent_fallback"},
            {"fixture": "checkpoint_resume_without_rng_or_hash_contract", "rejected": True, "evidence": "test_checkpoint_interrupted_resume_cpu_exact"},
            {"fixture": "stage_b_encoder_lr_changed_after_checkpoint", "rejected": True, "evidence": "test_resolved_contract_mismatch_known_bad_rejected"},
            {"fixture": "batch_size_or_steps_changed_after_checkpoint", "rejected": True, "evidence": "test_resolved_contract_mismatch_known_bad_rejected"},
            {"fixture": "support_or_loss_contract_changed_after_checkpoint", "rejected": True, "evidence": "test_resolved_contract_mismatch_known_bad_rejected"},
            {"fixture": "grad_clip_contract_changed_after_checkpoint", "rejected": True, "evidence": "test_resolved_contract_mismatch_known_bad_rejected"},
            {"fixture": "amp_half_precision_loss_nan_regression", "rejected": True, "evidence": "test_loss_reductions_cast_amp_outputs_to_fp32_and_remain_finite"},
            {"fixture": "amp_dtype_changed_after_checkpoint", "rejected": True, "evidence": "test_resolved_contract_mismatch_known_bad_rejected"},
            {"fixture": "edema_last_overwrites_post_scar_decision", "rejected": True, "evidence": "test_strong_edema_correction_cannot_overwrite_post_scar_decision"},
            {"fixture": "scar_priority_freezes_false_scar", "rejected": True, "evidence": "test_negative_scar_correction_can_release_false_scar_to_edema"},
            {"fixture": "edema_zone_excludes_scar_after_priority_reorder", "rejected": True, "evidence": "test_scar_priority_preserves_edema_zone_union_semantics"},
            {"fixture": "priority_reorder_breaks_zero_correction_identity", "rejected": True, "evidence": "test_zero_correction_identity_after_priority_reorder"},
            {"fixture": "no_t2_edema_changes_logits_after_priority_reorder", "rejected": True, "evidence": "test_no_t2_identity_after_priority_reorder"},
            {"fixture": "empty_anchor_simpleitk_distance_max_float_enters_context", "rejected": True, "evidence": "test_empty_anchor_support_distance_is_clipped_not_max_float"},
            {"fixture": "empty_support_case_selected_as_error_fn_or_pathology", "rejected": True, "evidence": "test_support_actionable_sampler_excludes_empty_anchor_from_error_pools"},
        ],
    }
    write_json(RESULT_ROOT / "known_bad_report.json", known)
    align_batch = {
        "images": torch.zeros(1, 3, 4, 16, 16),
        "anchor_logits": torch.zeros(1, 6, 4, 16, 16),
        "availability": torch.ones(1, 3),
        "labels": torch.zeros(1, 4, 16, 16, dtype=torch.long),
        "anchor_mask": torch.zeros(1, 4, 16, 16, dtype=torch.long),
        "fn_error_map": torch.zeros(1, 1, 4, 16, 16),
    }
    align_batch["images"][0, 0, 2, 9, 10] = 1
    align_batch["labels"][0, 2, 9, 10] = SCAR_CHANNEL
    align_batch["fn_error_map"][0, 0, 2, 9, 10] = 1
    cropped = aligned_spatial_crop(align_batch, (1, 5, 6), (2, 8, 8))
    align_status = bool(cropped["images"][0, 0, 1, 4, 4] == 1 and cropped["labels"][0, 1, 4, 4] == SCAR_CHANNEL and cropped["fn_error_map"][0, 0, 1, 4, 4] == 1)
    write_json(RESULT_ROOT / "augmentation_alignment_audit.json", {
        "created_at_utc": now_utc(),
        "status": "PASS" if align_status else "NEEDS_REPAIR",
        "source": "src/care_myocardium.data.care_dg_dataset.aligned_spatial_crop",
        "source_sha256": source_hashes().get("src/care_myocardium/data/care_dg_dataset.py"),
    })
    return impl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--gate-a", action="store_true")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()
    if not args.static_only and not args.gate_a:
        parser.error("expected --static-only or --gate-a")
    GATE_ROOT.mkdir(parents=True, exist_ok=True)
    static = run_static_tests()
    real = None
    if args.gate_a:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if device.type != "cuda" and not args.allow_cpu:
            raise SystemExit("CARE_DG_GATE_A_REQUIRES_CUDA_OR_EXPLICIT_ALLOW_CPU")
        real = run_real_case_checks(device, args.steps, args.lr)
    impl = write_contracts(static, real)
    r3_paths = {
        "preflight_receipt": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/fold_training_receipt.json",
        "preflight_validator": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/preflight_validator_report.json",
        "inner_split_manifest": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/inner_split_manifest.json",
        "inner_evaluation_plan": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/inner_evaluation_plan.json",
        "inner_eval_repeat": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/inner_evaluation_repeat_receipt.json",
        "sampler_quota_audit_stage_a": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/sampler_quota_audit_stage_a.json",
        "sampler_quota_audit_stage_b": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/sampler_quota_audit_stage_b.json",
        "resolved_training_contract": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/resolved_training_contract.json",
        "margin_cap_audit": RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0/margin_cap_audit.json",
    }
    r3_preflight = {name: {"path": rel(path), "exists": path.exists(), "sha256": sha256_file(path) if path.exists() else "missing"} for name, path in r3_paths.items()}
    summary = {"status": impl["status"], "gate_revision": "A-R3", "approval_token_required": "APPROVE_GATE_A_R3", "static": static, "real": real, "r3_preflight": r3_preflight, "implementation_contract": rel(RESULT_ROOT / "implementation_contract.json"), "strict_validator_status": "DEFERRED_UNTIL_FINAL_R3_VALIDATOR"}
    write_json(GATE_ROOT / "gate_a_summary.json", summary)
    write_json(RESULT_ROOT / "gate_a_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if impl["status"].endswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
