#!/usr/bin/env python3
"""Evaluate inherited M10 Wave 2 scheduled checkpoints for the follow-up.

This script never trains.  It reads immutable old M10 Wave 2 checkpoints,
replays selected checkpoints through the legacy full-case evaluator, and writes
all new evidence under the M10 follow-up result directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training import run_srr_v3_m10_complete_repair as m10  # noqa: E402


TASK_KEY = "20260714_srr_v3_m10_followup_wave2_reconciliation"
OUT_DIR = REPO_ROOT / "results/20260714_srr_v3_m10_followup_wave2_reconciliation"
OUT_RUNTIME = OUT_DIR / "runtime"
OLD_RUNTIME_D0 = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry4/htzhulab"
OLD_RUNTIME_RETRY11 = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab"
OLD_FINALIZATION = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_partition_race_retry11_finalization.json"
OLD_RETRY11_LEDGER = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/wave2_partition_race_retry11_job_ledger.csv"

PHASE_RUNTIME_ROOTS = {
    "d0_control": OLD_RUNTIME_D0,
    "d1_spatial_br2": OLD_RUNTIME_RETRY11,
    "d2_hierarchical_psip": OLD_RUNTIME_RETRY11,
    "d3_full_propref": OLD_RUNTIME_RETRY11,
    "hard_negative_refresh": OLD_RUNTIME_RETRY11,
    "no_context_control": OLD_RUNTIME_RETRY11,
    "alignment_control": OLD_RUNTIME_RETRY11,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def phase_variant_dir(phase: str) -> Path:
    spec = m10.PHASES[phase]
    return PHASE_RUNTIME_ROOTS[phase] / "variants" / spec.run_label


def followup_variant_dir(phase: str) -> Path:
    spec = m10.PHASES[phase]
    return OUT_RUNTIME / "variants" / spec.run_label


def checkpoint_step(path: Path) -> int:
    stem = path.stem
    if stem == "checkpoint_final":
        return 10**12
    if stem == "checkpoint_best":
        return 10**12 - 1
    try:
        return int(stem.rsplit("_", 1)[-1])
    except ValueError:
        return 10**12 - 2


def checkpoint_name(path: Path) -> str:
    return path.stem


def inventory_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for phase, spec in m10.PHASES.items():
        vdir = phase_variant_dir(phase)
        summary = load_json(vdir / "summary.json")
        ckpt_dir = vdir / "checkpoints/fold_0/propref_config"
        checkpoints = sorted(ckpt_dir.glob("*.pt"), key=lambda p: (checkpoint_step(p), p.name))
        for path in checkpoints:
            name = checkpoint_name(path)
            existing_old_metrics = vdir / f"component_hd_by_case_{name}.csv"
            existing_followup_metrics = followup_variant_dir(phase) / f"component_hd_by_case_{name}.csv"
            rows.append(
                {
                    "phase": phase,
                    "design": spec.design,
                    "variant": spec.run_label,
                    "checkpoint_name": name,
                    "checkpoint_path": str(path),
                    "checkpoint_step": checkpoint_step(path) if checkpoint_step(path) < 10**11 else "",
                    "recoverable": path.is_file(),
                    "old_metrics_present": existing_old_metrics.is_file(),
                    "followup_metrics_present": existing_followup_metrics.is_file(),
                    "summary_path": str(vdir / "summary.json"),
                    "legacy_checkpoint_selection_mode": summary.get("checkpoint_selection_mode", "EVIDENCE_NOT_FOUND"),
                    "legacy_checkpoint_selection_status": summary.get("checkpoint_selection_status", "EVIDENCE_NOT_FOUND"),
                }
            )
    write_csv(OUT_DIR / "checkpoint_inventory.csv", rows)
    return rows


def copy_existing_best_final_artifacts() -> None:
    for phase, spec in m10.PHASES.items():
        source = phase_variant_dir(phase)
        target = followup_variant_dir(phase)
        target.mkdir(parents=True, exist_ok=True)
        for pattern in (
            "component_hd_by_case_checkpoint_*.csv",
            "subgroup_metrics_checkpoint_*.csv",
            "prediction_sanity_checkpoint_*.csv",
            "proposal_pr_sweep_checkpoint_*.csv",
            "roi_coverage_checkpoint_*.csv",
            "crop_bounds_checkpoint_*.csv",
            "summary.json",
            "training_log.csv",
            "validation_events.csv",
            "loss_component_gradient_sanity.csv",
            "retrieval_usage.csv",
            "prototype_bank_summary.json",
        ):
            for item in source.glob(pattern):
                shutil.copyfile(item, target / item.name)


def base_legacy_args(phase: str, checkpoint_payload: dict[str, object]) -> SimpleNamespace:
    saved = checkpoint_payload.get("args")
    if isinstance(saved, dict):
        args = dict(saved)
    else:
        parser = m10.build_parser()
        defaults = parser.parse_args(["--phase", phase, "--skip-export"])
        args = vars(m10.make_legacy_args(defaults, m10.PHASES[phase]))
    args["out_root"] = str(OUT_RUNTIME)
    args["run_label"] = m10.PHASES[phase].run_label
    return SimpleNamespace(**args)


def eval_cases_for_args(args: SimpleNamespace) -> list[object]:
    legacy = m10.legacy
    _, full_val_ids = legacy.load_split(int(getattr(args, "fold", 0)))
    explicit = legacy.parse_case_id_list(getattr(args, "eval_case_ids", ""))
    if explicit:
        invalid = [case_id for case_id in explicit if case_id not in full_val_ids]
        if invalid:
            raise ValueError(f"invalid eval ids: {','.join(invalid)}")
        eval_ids = explicit
    else:
        eval_ids = list(full_val_ids)
    max_eval_cases = int(getattr(args, "max_eval_cases", 0) or 0)
    if max_eval_cases > 0:
        eval_ids = eval_ids[:max_eval_cases]
    metadata = legacy.load_myops_case_metadata()
    anchor_root = legacy._anchor_root(getattr(args, "nnunet_anchor_root", str(legacy.DEFAULT_NNUNET_ANCHOR_ROOT)))
    return [legacy.read_anchored_case(case_id, metadata, anchor_root) for case_id in eval_ids]


def evaluate_checkpoint(phase: str, checkpoint_path: Path, device_name: str) -> dict[str, object]:
    import torch

    legacy = m10.legacy
    spec = m10.PHASES[phase]
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    args = base_legacy_args(phase, state)
    device = torch.device("cuda" if device_name == "cuda" and torch.cuda.is_available() else "cpu")
    model = legacy.SRRProposeRefineMyoPS(**legacy.model_kwargs_from_args(args)).to(device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    cases = eval_cases_for_args(args)
    name = checkpoint_name(checkpoint_path)
    proposal_thresholds = legacy.parse_float_list(getattr(args, "proposal_thresholds", legacy.DEFAULT_PROPOSAL_THRESHOLDS))
    target = followup_variant_dir(phase)
    target.mkdir(parents=True, exist_ok=True)
    legacy.evaluate(
        model,
        cases,
        target,
        spec.run_label,
        device,
        disable_nnunet_anchor=bool(getattr(args, "disable_nnunet_anchor", False) or spec.disable_nnunet_anchor),
        checkpoint_name=name,
        proposal_thresholds=proposal_thresholds,
        scar_decode_threshold=float(getattr(args, "scar_decode_threshold", 0.50)),
        edema_decode_threshold=float(getattr(args, "edema_decode_threshold", 0.50)),
    )
    return {
        "phase": phase,
        "checkpoint_name": name,
        "checkpoint_path": str(checkpoint_path),
        "eval_cases": len(cases),
        "device": str(device),
        "metrics_path": str(target / f"component_hd_by_case_{name}.csv"),
        "status": "EVALUATED",
    }


def as_float(value: object) -> float | None:
    try:
        if value in {"", None}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_metrics() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for phase, spec in m10.PHASES.items():
        vdir = followup_variant_dir(phase)
        for metrics_path in sorted(vdir.glob("component_hd_by_case_*.csv")):
            name = metrics_path.name.removeprefix("component_hd_by_case_").removesuffix(".csv")
            metric_rows = read_csv(metrics_path)
            for decode_mode in ("argmax", "pathology_aware"):
                for metric_name in ("myops_scar", "myops_edema"):
                    subset = [
                        row
                        for row in metric_rows
                        if row.get("metric_name") == metric_name
                        and f"__{name}__{decode_mode}" in row.get("variant", "")
                    ]
                    dice = [as_float(row.get("dice")) for row in subset]
                    hd95 = [as_float(row.get("hd95")) for row in subset]
                    remote = [as_float(row.get("remote_fp_count")) for row in subset]
                    dice = [x for x in dice if x is not None]
                    hd95 = [x for x in hd95 if x is not None]
                    remote = [x for x in remote if x is not None]
                    rows.append(
                        {
                            "phase": phase,
                            "variant": spec.run_label,
                            "checkpoint_name": name,
                            "decode_mode": decode_mode,
                            "metric_name": metric_name,
                            "case_metric_rows": len(subset),
                            "case_count": len({row.get("case_id") for row in subset}),
                            "dice_mean": sum(dice) / len(dice) if dice else "",
                            "hd95_mean": sum(hd95) / len(hd95) if hd95 else "",
                            "hd95_worst": max(hd95) if hd95 else "",
                            "remote_fp_mean": sum(remote) / len(remote) if remote else "",
                            "status": "RUNTIME_METRICS" if subset else "EVIDENCE_NOT_FOUND",
                        }
                    )
    write_csv(OUT_DIR / "all_checkpoint_challenge_metrics.csv", rows)
    return rows


def eligibility_rows(inventory: list[dict[str, object]], metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    metric_index = {
        (row["phase"], row["checkpoint_name"], row["decode_mode"], row["metric_name"]): row for row in metrics
    }
    rows: list[dict[str, object]] = []
    for item in inventory:
        phase = str(item["phase"])
        name = str(item["checkpoint_name"])
        present = bool(item.get("followup_metrics_present")) or bool(item.get("old_metrics_present"))
        scar = metric_index.get((phase, name, "pathology_aware", "myops_scar"), {})
        edema = metric_index.get((phase, name, "pathology_aware", "myops_edema"), {})
        case_count = min(int(scar.get("case_count") or 0), int(edema.get("case_count") or 0))
        reasons = []
        if case_count != 44:
            reasons.append(f"case_count_{case_count}_not_44")
        for row, label in ((scar, "scar"), (edema, "edema")):
            if row.get("dice_mean") in {"", None}:
                reasons.append(f"{label}_finite_metrics_missing")
            if row.get("hd95_mean") in {"", None}:
                reasons.append(f"{label}_hd95_missing")
        if not present:
            reasons.append("checkpoint_not_evaluated_in_followup")
        rows.append(
            {
                "phase": phase,
                "checkpoint_name": name,
                "eligible": not reasons,
                "case_count": case_count,
                "exclusion_reason": ";".join(reasons),
            }
        )
    write_csv(OUT_DIR / "checkpoint_eligibility.csv", rows)
    return rows


def selected_checkpoints(metrics: list[dict[str, object]], eligibility: list[dict[str, object]]) -> dict[str, object]:
    eligible = {(row["phase"], row["checkpoint_name"]) for row in eligibility if str(row.get("eligible")).lower() == "true"}
    selected: dict[str, object] = {"selector": "challenge_facing_score", "status": "NEEDS_EVIDENCE", "phases": {}}
    by_key: dict[tuple[str, str], dict[str, dict[str, object]]] = {}
    for row in metrics:
        key = (str(row["phase"]), str(row["checkpoint_name"]))
        by_key.setdefault(key, {})[str(row["metric_name"])] = row
    for phase in m10.PHASES:
        candidates = []
        for (p, name), by_metric in by_key.items():
            if p != phase or (p, name) not in eligible:
                continue
            scar = by_metric.get("myops_scar", {})
            edema = by_metric.get("myops_edema", {})
            scar_dice = as_float(scar.get("dice_mean"))
            edema_dice = as_float(edema.get("dice_mean"))
            scar_hd95 = as_float(scar.get("hd95_mean")) or 0.0
            edema_hd95 = as_float(edema.get("hd95_mean")) or 0.0
            if scar_dice is None or edema_dice is None:
                continue
            score = min(scar_dice, edema_dice) + 0.25 * (scar_dice + edema_dice) - 0.001 * (scar_hd95 + edema_hd95)
            candidates.append((score, -(as_float(scar.get("hd95_worst")) or 0.0), -checkpoint_step(Path(name)), name))
        if candidates:
            best = sorted(candidates, reverse=True)[0]
            selected["phases"][phase] = {"checkpoint_name": best[3], "score": best[0], "status": "SELECTED_PRELIMINARY"}
        else:
            selected["phases"][phase] = {"checkpoint_name": "", "status": "NEEDS_EVIDENCE"}
    if all(v.get("status") == "SELECTED_PRELIMINARY" for v in selected["phases"].values() if isinstance(v, dict)):
        selected["status"] = "SELECTED_PRELIMINARY_PENDING_VALIDATOR"
    (OUT_DIR / "selected_checkpoints.json").write_text(json.dumps(selected, indent=2, sort_keys=True), encoding="utf-8")
    return selected


def run(args: argparse.Namespace) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.print_contract:
        print(
            json.dumps(
                {
                    "task_key": TASK_KEY,
                    "mode": "inherited_m10_wave2_all_checkpoint_evaluation_no_training",
                    "phases": {k: asdict(v) for k, v in m10.PHASES.items()},
                    "old_runtime_roots": {k: str(v) for k, v in PHASE_RUNTIME_ROOTS.items()},
                    "output_runtime_root": str(OUT_RUNTIME),
                    "writes_old_runtime": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    copy_existing_best_final_artifacts()
    inventory = inventory_rows()
    selected_phases = args.phase or sorted(m10.PHASES)
    eval_rows: list[dict[str, object]] = []
    if args.evaluate:
        for item in inventory:
            phase = str(item["phase"])
            if phase not in selected_phases:
                continue
            name = str(item["checkpoint_name"])
            if args.checkpoint and name != args.checkpoint:
                continue
            target_metrics = followup_variant_dir(phase) / f"component_hd_by_case_{name}.csv"
            if target_metrics.is_file() and not args.force:
                continue
            eval_rows.append(evaluate_checkpoint(phase, Path(str(item["checkpoint_path"])), args.device))
            if args.max_checkpoints and len(eval_rows) >= args.max_checkpoints:
                break
    write_csv(OUT_DIR / "evaluation_run_ledger.csv", eval_rows or [{"status": "NO_NEW_EVALUATION_RUN", "reason": "evaluate flag not set or all requested metrics already present"}])
    inventory = inventory_rows()
    metrics = summarize_metrics()
    eligibility = eligibility_rows(inventory, metrics)
    selected_checkpoints(metrics, eligibility)
    manifest = {
        "task_key": TASK_KEY,
        "status": "RUNTIME_EVALUATION_PARTIAL" if eval_rows else "INVENTORY_AND_EXISTING_METRICS_ONLY",
        "inventory_count": len(inventory),
        "new_evaluations": len(eval_rows),
        "metrics_rows": len(metrics),
        "output_dir": str(OUT_DIR),
        "output_runtime_root": str(OUT_RUNTIME),
    }
    (OUT_DIR / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--evaluate", action="store_true", help="Replay missing checkpoint metrics. This is GPU-suitable.")
    parser.add_argument("--phase", action="append", choices=sorted(m10.PHASES))
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--max-checkpoints", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    raise SystemExit(run(parser.parse_args()))


if __name__ == "__main__":
    main()
