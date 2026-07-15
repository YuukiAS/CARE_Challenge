#!/usr/bin/env python3
"""Fresh M10 follow-up2 Wave 2 checkpoint replay.

This entrypoint is evaluation-only.  It reloads inherited M10 MyoPS
checkpoints and writes all follow-up2 evidence under the 20260715 result root.
Historical candidate metrics are never copied or used for selection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training import run_srr_v3_m10_complete_repair as m10  # noqa: E402


TASK_KEY = "20260715_srr_v3_m10_followup2_wave2_evidence_repair"
OUT_DIR = REPO_ROOT / "results/20260715_srr_v3_m10_followup2_wave2_evidence_repair"
OUT_RUNTIME = OUT_DIR / "runtime"
OLD_RUNTIME_D0 = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry4/htzhulab"
OLD_RUNTIME_RETRY11 = REPO_ROOT / "results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_myops_training_executor/partition_race_retry11/htzhulab"

PHASE_RUNTIME_ROOTS = {
    "d0_control": OLD_RUNTIME_D0,
    "d1_spatial_br2": OLD_RUNTIME_RETRY11,
    "d2_hierarchical_psip": OLD_RUNTIME_RETRY11,
    "d3_full_propref": OLD_RUNTIME_RETRY11,
    "hard_negative_refresh": OLD_RUNTIME_RETRY11,
    "no_context_control": OLD_RUNTIME_RETRY11,
    "alignment_control": OLD_RUNTIME_RETRY11,
}

EXPECTED_CASES = 44


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def state_dict_sha256(state: dict[str, Any]) -> str:
    import torch

    digest = hashlib.sha256()
    model_state = state.get("model_state_dict", {})
    if not isinstance(model_state, dict):
        return "MISSING_MODEL_STATE_DICT"
    for key in sorted(model_state):
        tensor = model_state[key]
        digest.update(str(key).encode("utf-8"))
        if hasattr(tensor, "detach"):
            arr = tensor.detach().cpu().contiguous()
            digest.update(str(tuple(arr.shape)).encode("utf-8"))
            digest.update(str(arr.dtype).encode("utf-8"))
            digest.update(arr.numpy().tobytes())
        else:
            digest.update(repr(tensor).encode("utf-8"))
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
    return digest.hexdigest()


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


def append_jsonl(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


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
            target_metrics = followup_variant_dir(phase) / f"component_hd_by_case_{name}.csv"
            rows.append(
                {
                    "phase": phase,
                    "design": spec.design,
                    "variant": spec.run_label,
                    "checkpoint_name": name,
                    "checkpoint_path": str(path),
                    "checkpoint_sha256": sha256_file(path) if path.is_file() else "",
                    "checkpoint_step": checkpoint_step(path) if checkpoint_step(path) < 10**11 else "",
                    "recoverable": path.is_file(),
                    "old_candidate_metrics_path": str(vdir / f"component_hd_by_case_{name}.csv"),
                    "old_candidate_metrics_used": "false",
                    "followup2_metrics_present": target_metrics.is_file(),
                    "summary_path": str(vdir / "summary.json"),
                    "legacy_checkpoint_selection_mode": summary.get("checkpoint_selection_mode", "EVIDENCE_NOT_FOUND"),
                    "legacy_checkpoint_selection_status": summary.get("checkpoint_selection_status", "EVIDENCE_NOT_FOUND"),
                }
            )
    write_csv(OUT_DIR / "checkpoint_inventory.csv", rows)
    return rows


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
    eval_ids = list(explicit or full_val_ids)
    invalid = [case_id for case_id in eval_ids if case_id not in full_val_ids]
    if invalid:
        raise ValueError(f"invalid eval ids: {','.join(invalid)}")
    max_eval_cases = int(getattr(args, "max_eval_cases", 0) or 0)
    if max_eval_cases > 0:
        eval_ids = eval_ids[:max_eval_cases]
    metadata = legacy.load_myops_case_metadata()
    anchor_root = legacy._anchor_root(getattr(args, "nnunet_anchor_root", str(legacy.DEFAULT_NNUNET_ANCHOR_ROOT)))
    return [legacy.read_anchored_case(case_id, metadata, anchor_root) for case_id in eval_ids]


def case_ids(cases: list[object]) -> list[str]:
    ids: list[str] = []
    for item in cases:
        ids.append(str(getattr(item, "case_id", getattr(item, "key", ""))))
    return ids


def output_manifest(phase: str, checkpoint: str) -> dict[str, object]:
    target = followup_variant_dir(phase)
    files = []
    for pattern in (
        f"component_hd_by_case_{checkpoint}.csv",
        f"subgroup_metrics_{checkpoint}.csv",
        f"prediction_sanity_{checkpoint}.csv",
        f"proposal_pr_sweep_{checkpoint}.csv",
        f"roi_coverage_{checkpoint}.csv",
        f"crop_bounds_{checkpoint}.csv",
    ):
        item = target / pattern
        files.append(
            {
                "phase": phase,
                "checkpoint_name": checkpoint,
                "artifact_kind": "metric_or_qc",
                "path": str(item),
                "present": item.is_file(),
                "sha256": sha256_file(item) if item.is_file() else "",
                "bytes": item.stat().st_size if item.is_file() else 0,
            }
        )
    prediction_root = target / "predictions/fold_0" / checkpoint
    for item in sorted(prediction_root.glob("*/*.nii.gz")):
        files.append(
            {
                "phase": phase,
                "checkpoint_name": checkpoint,
                "artifact_kind": "raw_prediction",
                "decode_mode": item.parent.name,
                "case_id": item.name.removesuffix(".nii.gz"),
                "path": str(item),
                "present": item.is_file(),
                "sha256": sha256_file(item),
                "bytes": item.stat().st_size,
            }
        )
    present = [row for row in files if row["present"]]
    raw_predictions = [row for row in present if row.get("artifact_kind") == "raw_prediction"]
    status = "RAW_PREDICTION_MANIFEST_PRESENT" if raw_predictions else "RAW_PREDICTION_MANIFEST_MISSING"
    manifest = {
        "phase": phase,
        "checkpoint_name": checkpoint,
        "manifest_kind": "followup2_metric_artifacts",
        "status": status,
        "files": files,
        "present_file_count": len(present),
        "raw_prediction_file_count": len(raw_predictions),
        "sha256": sha256_text(json.dumps(files, sort_keys=True)),
    }
    manifest_path = OUT_DIR / "runtime_manifests" / f"{phase}__{checkpoint}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    raw_manifest_rows = [
        row
        for row in files
        if row.get("artifact_kind") == "raw_prediction"
    ]
    raw_manifest_path = OUT_DIR / "checkpoint_raw_output_manifest.csv"
    existing = read_csv(raw_manifest_path)
    existing = [
        row
        for row in existing
        if not (row.get("phase") == phase and row.get("checkpoint_name") == checkpoint)
    ]
    write_csv(raw_manifest_path, [*existing, *raw_manifest_rows])
    return manifest


def evaluate_checkpoint(phase: str, checkpoint_path: Path, device_name: str, argv: list[str]) -> dict[str, object]:
    import torch

    start = time.time()
    legacy = m10.legacy
    spec = m10.PHASES[phase]
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state_hash = state_dict_sha256(state)
    args = base_legacy_args(phase, state)
    device = torch.device("cuda" if device_name == "cuda" and torch.cuda.is_available() else "cpu")
    model = legacy.SRRProposeRefineMyoPS(**legacy.model_kwargs_from_args(args)).to(device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    cases = eval_cases_for_args(args)
    ids = case_ids(cases)
    name = checkpoint_name(checkpoint_path)
    target = followup_variant_dir(phase)
    target.mkdir(parents=True, exist_ok=True)
    proposal_thresholds = legacy.parse_float_list(getattr(args, "proposal_thresholds", legacy.DEFAULT_PROPOSAL_THRESHOLDS))
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
    manifest = output_manifest(phase, name)
    end = time.time()
    receipt = {
        "evaluation_source": "fresh_checkpoint_reload",
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", ""),
        "slurm_job_name": os.environ.get("SLURM_JOB_NAME", ""),
        "slurm_partition": os.environ.get("SLURM_JOB_PARTITION", ""),
        "attempt_id": os.environ.get("M10_FOLLOWUP2_ATTEMPT_ID", os.environ.get("SLURM_JOB_ID", "local")),
        "replacement_for_attempt": os.environ.get("M10_FOLLOWUP2_REPLACEMENT_FOR", ""),
        "replacement_reason": os.environ.get("M10_FOLLOWUP2_REPLACEMENT_REASON", ""),
        "phase": phase,
        "checkpoint_name": name,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "loaded_state_dict_sha256": state_hash,
        "checkpoint_step": checkpoint_step(checkpoint_path) if checkpoint_step(checkpoint_path) < 10**11 else "",
        "argv": argv,
        "start_epoch_seconds": start,
        "end_epoch_seconds": end,
        "exit_code": 0,
        "device": str(device),
        "code_hash": sha256_file(Path(__file__)),
        "config_hash": sha256_text(json.dumps(vars(args), sort_keys=True, default=str)),
        "split_hash": sha256_text(json.dumps(ids, sort_keys=True)),
        "exact_case_ids": ids,
        "inference_call_count": len(cases),
        "new_runtime_output_root": str(target),
        "raw_output_manifest_status": manifest["status"],
        "raw_output_manifest_sha256": manifest["sha256"],
        "case_metric_csv": str(target / f"component_hd_by_case_{name}.csv"),
        "case_metric_csv_sha256": sha256_file(target / f"component_hd_by_case_{name}.csv") if (target / f"component_hd_by_case_{name}.csv").is_file() else "",
        "historical_candidate_metric_source_path": "",
        "status": "EVALUATED_WITH_FRESH_RELOAD_AND_RAW_PREDICTION_MANIFEST"
        if manifest["status"] == "RAW_PREDICTION_MANIFEST_PRESENT"
        else "EVALUATED_WITH_FRESH_RELOAD_BUT_RAW_PREDICTION_MANIFEST_MISSING",
    }
    append_jsonl(OUT_DIR / "checkpoint_replay_receipts.jsonl", receipt)
    return receipt


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
                            "status": "FRESH_FOLLOWUP2_RUNTIME_METRICS" if subset else "EVIDENCE_NOT_FOUND",
                        }
                    )
    write_csv(OUT_DIR / "all_checkpoint_case_metrics.csv", rows)
    write_csv(OUT_DIR / "all_checkpoint_subgroup_metrics.csv", [])
    return rows


def anchor_relative_score(scar: dict[str, object], edema: dict[str, object]) -> tuple[float | None, str]:
    # The immutable nnU-Net anchor must be wired in a later pass with path and
    # SHA256.  Until then, the reviewed formula cannot be scored honestly.
    if not scar or not edema:
        return None, "missing_scar_or_edema_metric"
    return None, "immutable_anchor_metrics_not_bound_with_sha256"


def eligibility_rows(inventory: list[dict[str, object]], metrics: list[dict[str, object]]) -> list[dict[str, object]]:
    metric_index = {(row["phase"], row["checkpoint_name"], row["decode_mode"], row["metric_name"]): row for row in metrics}
    rows: list[dict[str, object]] = []
    for item in inventory:
        phase = str(item["phase"])
        name = str(item["checkpoint_name"])
        scar = metric_index.get((phase, name, "pathology_aware", "myops_scar"), {})
        edema = metric_index.get((phase, name, "pathology_aware", "myops_edema"), {})
        manifest = load_json(OUT_DIR / "runtime_manifests" / f"{phase}__{name}.json")
        case_count = min(int(scar.get("case_count") or 0), int(edema.get("case_count") or 0))
        reasons = []
        if case_count != EXPECTED_CASES:
            reasons.append(f"case_count_{case_count}_not_{EXPECTED_CASES}")
        if not manifest:
            reasons.append("fresh_runtime_manifest_missing")
        elif manifest.get("status") != "RAW_PREDICTION_MANIFEST_PRESENT":
            reasons.append("raw_prediction_manifest_missing")
        if not (OUT_DIR / "calibration_freeze_receipt.json").is_file():
            reasons.append("calibration_freeze_receipt_missing")
        for row, label in ((scar, "scar"), (edema, "edema")):
            if row.get("dice_mean") in {"", None}:
                reasons.append(f"{label}_finite_dice_missing")
            if row.get("hd95_mean") in {"", None}:
                reasons.append(f"{label}_hd95_missing")
        rows.append(
            {
                "phase": phase,
                "checkpoint_name": name,
                "eligible": not reasons,
                "case_count": case_count,
                "raw_output_manifest_status": manifest.get("status", "MISSING"),
                "exclusion_reason": ";".join(reasons),
            }
        )
    write_csv(OUT_DIR / "checkpoint_eligibility.csv", rows)
    return rows


def selected_checkpoints(metrics: list[dict[str, object]], eligibility: list[dict[str, object]]) -> dict[str, object]:
    eligible = {(row["phase"], row["checkpoint_name"]) for row in eligibility if str(row.get("eligible")).lower() == "true"}
    by_key: dict[tuple[str, str], dict[str, dict[str, object]]] = {}
    for row in metrics:
        if row.get("decode_mode") != "pathology_aware":
            continue
        key = (str(row["phase"]), str(row["checkpoint_name"]))
        by_key.setdefault(key, {})[str(row["metric_name"])] = row
    selected: dict[str, object] = {
        "selector": "anchor_relative_dice_hd95_remote_fp_formula",
        "status": "NEEDS_EVIDENCE",
        "phases": {},
    }
    selector_rows: list[dict[str, object]] = []
    for phase in m10.PHASES:
        candidates = []
        for (p, name), by_metric in by_key.items():
            if p != phase or (p, name) not in eligible:
                continue
            score, reason = anchor_relative_score(by_metric.get("myops_scar", {}), by_metric.get("myops_edema", {}))
            selector_rows.append({"phase": phase, "checkpoint_name": name, "score": score if score is not None else "", "status": "SCORED" if score is not None else "NEEDS_EVIDENCE", "reason": reason})
            if score is not None:
                worst = max(as_float(by_metric.get("myops_scar", {}).get("hd95_worst")) or 0.0, as_float(by_metric.get("myops_edema", {}).get("hd95_worst")) or 0.0)
                candidates.append((score, -worst, -checkpoint_step(Path(name)), name))
        if candidates:
            best = sorted(candidates, reverse=True)[0]
            selected["phases"][phase] = {"checkpoint_name": best[3], "score": best[0], "status": "SELECTED_REQUIRES_CLEAN_RELOAD"}
        else:
            selected["phases"][phase] = {"checkpoint_name": "", "status": "NEEDS_EVIDENCE"}
    write_csv(OUT_DIR / "checkpoint_selector_recalculation.csv", selector_rows)
    (OUT_DIR / "selected_checkpoints.json").write_text(json.dumps(selected, indent=2, sort_keys=True), encoding="utf-8")
    return selected


def write_static_receipts(argv: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    freeze = {
        "task_key": TASK_KEY,
        "status": "CALIBRATION_FREEZE_PARTIAL_NEEDS_ANCHOR_SHA_BINDING",
        "argv": argv,
        "code_hash": sha256_file(Path(__file__)),
        "created_epoch_seconds": time.time(),
    }
    (OUT_DIR / "calibration_freeze_receipt.json").write_text(json.dumps(freeze, indent=2, sort_keys=True), encoding="utf-8")
    (OUT_DIR / "inherited_runtime_fingerprint_ledger.csv").write_text(
        "artifact,path,sha256,status\n"
        f"evaluator,{Path(__file__)},{sha256_file(Path(__file__))},PRESENT\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace, argv: list[str]) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.print_contract:
        print(
            json.dumps(
                {
                    "task_key": TASK_KEY,
                    "mode": "fresh_checkpoint_reload_followup2_no_training",
                    "formal_flags_required": ["--evaluate", "--force"],
                    "phases": {key: asdict(value) for key, value in m10.PHASES.items()},
                    "old_runtime_roots": {key: str(value) for key, value in PHASE_RUNTIME_ROOTS.items()},
                    "output_runtime_root": str(OUT_RUNTIME),
                    "copies_historical_candidate_metrics": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not args.evaluate or not args.force:
        print("formal followup2 replay requires both --evaluate and --force", file=sys.stderr)
        return 2
    write_static_receipts(argv)
    inventory = inventory_rows()
    selected_phases = args.phase or sorted(m10.PHASES)
    receipts: list[dict[str, object]] = []
    for item in inventory:
        phase = str(item["phase"])
        if phase not in selected_phases:
            continue
        name = str(item["checkpoint_name"])
        if args.checkpoint and name != args.checkpoint:
            continue
        checkpoint = Path(str(item["checkpoint_path"]))
        receipts.append(evaluate_checkpoint(phase, checkpoint, args.device, argv))
        if args.max_checkpoints and len(receipts) >= args.max_checkpoints:
            break
    write_csv(OUT_DIR / "checkpoint_replay_ledger.csv", receipts or [{"status": "NO_CHECKPOINTS_EVALUATED"}])
    inventory = inventory_rows()
    metrics = summarize_metrics()
    eligibility = eligibility_rows(inventory, metrics)
    selected_checkpoints(metrics, eligibility)
    manifest = {
        "task_key": TASK_KEY,
        "status": "FRESH_REPLAY_PARTIAL_NEEDS_CONTRACT_COMPLETION",
        "inventory_count": len(inventory),
        "new_evaluations": len(receipts),
        "metrics_rows": len(metrics),
        "output_dir": str(OUT_DIR),
        "output_runtime_root": str(OUT_RUNTIME),
    }
    (OUT_DIR / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--phase", action="append", choices=sorted(m10.PHASES))
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--max-checkpoints", type=int, default=0)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    raise SystemExit(run(parser.parse_args(), sys.argv))


if __name__ == "__main__":
    main()
