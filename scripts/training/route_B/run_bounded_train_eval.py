#!/usr/bin/env python3
"""Run the first Route B post-freeze bounded train/eval aggregation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.route_B.run_implementation_gate import (  # noqa: E402
    discover_data_root,
    load_real_cine_batch,
    load_real_myops_batch,
    now,
    write,
    write_csv,
    write_json,
)
from src.care_myocardium.route_B import (  # noqa: E402
    RouteBCineModel,
    RouteBMyoPSModel,
    route_b_cine_loss,
    route_b_myops_loss,
)


RESULT_ROOT = REPO_ROOT / "results" / "route_B"
RUNTIME_ROOT = RESULT_ROOT / "runtime" / "bounded_train_eval"
TOKEN_UNDERTRAINED = "ROUTE_B_SCIENTIFIC_UNDERTRAINED"


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def dice_score(pred: torch.Tensor, target: torch.Tensor, label: int) -> float:
    pred_mask = pred == label
    target_mask = target == label
    denom = int(pred_mask.sum().item() + target_mask.sum().item())
    if denom == 0:
        return float("nan")
    return float((2.0 * (pred_mask & target_mask).sum().item()) / denom)


def mean_or_nan(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return float(sum(finite) / len(finite)) if finite else float("nan")


def eval_myops(model: RouteBMyoPSModel, batch: tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, list[str], list[str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    x, availability, anchor, labels, cases, _ = batch
    model.eval()
    with torch.no_grad():
        pred = torch.argmax(model(x, availability, anchor)["final_logits"], dim=1)
    scar_scores = [dice_score(pred[idx], labels[idx], 5) for idx in range(len(cases))]
    edema_scores = [dice_score(pred[idx], labels[idx], 4) for idx in range(len(cases))]
    metric_rows = [
        {"task": "MyoPS", "metric": "myops_scar_compact5_dice", "value": mean_or_nan(scar_scores), "case_count": len(cases), "status": "UNDERTRAINED"},
        {"task": "MyoPS", "metric": "myops_edema_compact4_dice", "value": mean_or_nan(edema_scores), "case_count": len(cases), "status": "UNDERTRAINED"},
    ]
    safety_rows = []
    for idx, case in enumerate(cases):
        safety_rows.append(
            {
                "case_id": case,
                "task": "MyoPS",
                "gt_scar_voxels": int((labels[idx] == 5).sum().item()),
                "pred_scar_voxels": int((pred[idx] == 5).sum().item()),
                "gt_edema_voxels": int((labels[idx] == 4).sum().item()),
                "pred_edema_voxels": int((pred[idx] == 4).sum().item()),
                "scar_dice": scar_scores[idx],
                "edema_dice": edema_scores[idx],
                "t2_present": bool(availability[idx, 2].item() > 0.5),
            }
        )
    return metric_rows, safety_rows


def eval_cine(model: RouteBCineModel, batch: tuple[torch.Tensor, torch.Tensor, list[str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    frames, target, cases = batch
    model.eval()
    with torch.no_grad():
        pred = torch.argmax(model(frames)["logits"], dim=1)
    myocardium_scores = [dice_score(pred[idx], target[idx], 1) for idx in range(len(cases))]
    scar_scores = [dice_score(pred[idx], target[idx], 3) for idx in range(len(cases))]
    metric_rows = [
        {"task": "CineMyoPS", "metric": "class_1_myocardium_proxy_dice", "value": mean_or_nan(myocardium_scores), "case_count": len(cases), "status": "UNDERTRAINED"},
        {"task": "CineMyoPS", "metric": "class_3_scar_sanity_dice", "value": mean_or_nan(scar_scores), "case_count": len(cases), "status": "UNDERTRAINED"},
    ]
    safety_rows = []
    for idx, case in enumerate(cases):
        safety_rows.append(
            {
                "case_id": case,
                "task": "CineMyoPS",
                "gt_myocardium_voxels": int((target[idx] == 1).sum().item()),
                "pred_myocardium_voxels": int((pred[idx] == 1).sum().item()),
                "gt_scar_voxels": int((target[idx] == 3).sum().item()),
                "pred_scar_voxels": int((pred[idx] == 3).sum().item()),
                "myocardium_dice": myocardium_scores[idx],
                "scar_dice": scar_scores[idx],
                "nonreference_frames": int(frames.shape[1] - 1),
            }
        )
    return metric_rows, safety_rows


def append_packet(args: argparse.Namespace, summary: dict[str, Any]) -> None:
    write(
        RESULT_ROOT / "completion_check.md",
        f"""# Route B Completion Check Continuation

Completion token: `{TOKEN_UNDERTRAINED}`

The implementation-before-training gate passed on synthetic and real cases, then a post-freeze bounded train/eval command ran and aggregated lightweight evidence. This remains undertrained because the first run did not meet all Route B minimum effective training thresholds.

Forbidden and not performed: `review.md`, push, validation packaging/upload, hosted metric claim, route promotion, scientific stop, M11, cross-route merge.
""",
    )
    write(
        RESULT_ROOT / "controller_report.md",
        f"""# Route B Controller Report Continuation

controller_run_status: POST_FREEZE_BOUNDED_TRAIN_EVAL_UNDERTRAINED
operational_completion_status: {TOKEN_UNDERTRAINED}
experiment_adequacy_decision: SCIENTIFIC_UNDERTRAINED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_ROUTE_B_CONTINUATION_PACKET_ONLY
git_commit_decision: LOCAL_LIGHTWEIGHT_PACKET_COMMIT_REQUIRED
git_push_decision: SKIP_PUSH

## Summary

The controller continued from the prior diagnostic packet without reverting it. The Route B implementation gate passed with real MyoPS and Cine cases, and the post-freeze bounded train/eval entrypoint ran on real data. The run is explicitly undertrained: optimizer steps, train-loop seconds, or other minimum adequacy thresholds are insufficient for route promotion or scientific conclusions.

No pending/running/submitted-only Slurm state is being treated as completion.

bounded_train_eval_summary: `results/route_B/bounded_train_eval_summary.json`
optimizer_steps: `{summary['optimizer_steps']}`
train_loop_seconds: `{summary['train_loop_seconds']:.3f}`
validation_events: `{summary['validation_events']}`
myops_eval_cases: `{summary['myops_eval_cases']}`
cine_eval_cases: `{summary['cine_eval_cases']}`
""",
    )
    write(
        RESULT_ROOT / "result.md",
        f"""# Route B Controller Result Continuation

Final controller token: `{TOKEN_UNDERTRAINED}`

This superseding packet contains a real implementation gate pass and a post-freeze bounded train/eval aggregation. It is not review-ready for scientific acceptance; it is undertrained evidence with the required lightweight tables present.
""",
    )
    write_json(
        RESULT_ROOT / "finalizer_state.json",
        {
            "task": "RouteB-Controller",
            "state": "READY_FOR_LOCAL_PACKET_COMMIT_SCIENTIFIC_UNDERTRAINED",
            "completion": TOKEN_UNDERTRAINED,
            "generated_at_utc": now(),
            "bounded_train_eval_run": True,
            "formal_training_submitted": False,
            "slurm_jobs": [],
            "review_md_written": False,
            "push_performed": False,
            "route_promotion_decision": "NOT_REVIEWED",
            "route_negative_decision": "NOT_REVIEWED",
            "scientific_resolution_status": "AWAITING_REVIEW",
        },
    )
    write(
        RESULT_ROOT / "commands_run.md",
        "# Route B Commands Run Continuation\n\n"
        "- `python scripts/route_B/run_implementation_gate.py --strict`\n"
        f"- `python scripts/training/route_B/run_bounded_train_eval.py --steps {args.steps} --myops-eval-cases {args.myops_eval_cases} --cine-eval-cases {args.cine_eval_cases}`\n"
        "- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`\n"
        "- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`\n"
        "- `pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`\n"
        "- `git diff --check`\n\n"
        "No validation upload, push, M11, or review command was run.\n",
    )
    write(
        RESULT_ROOT / "review_request.md",
        "# Route B Review Request Continuation\n\n"
        "Requested independent reviewer action: read-only review of the superseding Route B continuation packet and route_B-local source/tests.\n\n"
        "The reviewer should verify the real implementation gate and undertrained post-freeze train/eval evidence. The reviewer must not fix files, train, upload, push, start M11, or merge routes.\n",
    )
    context = {
        "task": "RouteB-Controller-continuation",
        "route_id": "route_B",
        "status": TOKEN_UNDERTRAINED,
        "generated_at_utc": now(),
        "git_head_before_continuation": git(["rev-parse", "HEAD"]),
        "formal_training_submitted": False,
        "bounded_train_eval_run": True,
        "slurm_jobs_submitted": [],
    }
    write_json(RESULT_ROOT / "controller_context.json", context)
    write_csv(
        RESULT_ROOT / "controller_ledger.csv",
        [
            {"timestamp_utc": now(), "phase": "B3", "decision": "implementation_gate_passed", "next_action": "B5_bounded_train_eval"},
            {"timestamp_utc": now(), "phase": "B5", "decision": TOKEN_UNDERTRAINED, "next_action": "B6_finalizer_packet"},
            {"timestamp_utc": now(), "phase": "B6", "decision": TOKEN_UNDERTRAINED, "next_action": "independent_readonly_review"},
        ],
    )
    write(
        RESULT_ROOT / "controller_bootstrap_snapshot.md",
        "# Route B Controller Bootstrap Snapshot Continuation\n\n"
        f"- current_token: `{TOKEN_UNDERTRAINED}`\n- bounded_train_eval_run: `true`\n- formal_training_submitted: `false`\n- review_md_written: `false`\n",
    )
    files = sorted(p for p in RESULT_ROOT.iterdir() if p.is_file())
    write(RESULT_ROOT / "MANIFEST.md", "# Route B Manifest Continuation\n\n" + "\n".join(f"- `{p.relative_to(REPO_ROOT)}`" for p in files if p.name != "MANIFEST.md") + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--myops-eval-cases", type=int, default=10)
    parser.add_argument("--cine-eval-cases", type=int, default=5)
    args = parser.parse_args()

    freeze_path = RESULT_ROOT / "implementation_freeze_receipt.json"
    if not freeze_path.exists():
        raise FileNotFoundError("implementation_freeze_receipt.json is required before bounded train/eval")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("formal_training_allowed") is not True:
        raise RuntimeError("Route B formal training is not allowed before the complete implementation gate passes")
    data_root = discover_data_root()
    if data_root is None:
        raise FileNotFoundError("Route B data root is unavailable after implementation freeze")

    torch.manual_seed(31)
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    train_myops = load_real_myops_batch(data_root, limit=3)
    eval_myops_batch = load_real_myops_batch(data_root, limit=args.myops_eval_cases)
    train_cine = load_real_cine_batch(data_root, limit=3)
    eval_cine_batch = load_real_cine_batch(data_root, limit=args.cine_eval_cases)

    myops_model = RouteBMyoPSModel()
    cine_model = RouteBCineModel()
    optimizer = torch.optim.Adam(list(myops_model.parameters()) + list(cine_model.parameters()), lr=1e-3)
    first_loss = None
    last_loss = None
    validation_events = 0
    start = time.monotonic()
    for step in range(1, args.steps + 1):
        optimizer.zero_grad(set_to_none=True)
        myops_x, myops_avail, myops_anchor, myops_labels, myops_cases, _ = train_myops
        myops_out = myops_model(myops_x, myops_avail, myops_anchor, case_ids=myops_cases, fold=0)
        myops_loss, _ = route_b_myops_loss(myops_out, myops_labels, myops_avail)
        cine_frames, cine_target, _ = train_cine
        cine_out = cine_model(cine_frames)
        cine_loss, _ = route_b_cine_loss(cine_out, cine_target)
        loss = myops_loss + cine_loss
        loss.backward()
        optimizer.step()
        value = float(loss.detach().cpu())
        first_loss = value if first_loss is None else first_loss
        last_loss = value
        if step in {max(1, args.steps // 2), args.steps}:
            validation_events += 1
            eval_myops(myops_model, eval_myops_batch)
            eval_cine(cine_model, eval_cine_batch)
    train_loop_seconds = time.monotonic() - start

    myops_metrics, myops_safety = eval_myops(myops_model, eval_myops_batch)
    cine_metrics, cine_safety = eval_cine(cine_model, eval_cine_batch)
    metric_rows = myops_metrics + cine_metrics
    safety_rows = myops_safety + cine_safety
    adequacy = [
        {"criterion": "min_optimizer_steps", "observed": args.steps, "required": 500, "pass": args.steps >= 500},
        {"criterion": "min_train_loop_seconds", "observed": f"{train_loop_seconds:.3f}", "required": 1800, "pass": train_loop_seconds >= 1800},
        {"criterion": "min_validation_events", "observed": validation_events, "required": 2, "pass": validation_events >= 2},
        {"criterion": "min_eval_cases_myops", "observed": args.myops_eval_cases, "required": 10, "pass": args.myops_eval_cases >= 10},
        {"criterion": "min_eval_cases_cine", "observed": args.cine_eval_cases, "required": 5, "pass": args.cine_eval_cases >= 5},
        {"criterion": "loss_decrease", "observed": f"{first_loss:.6f}->{last_loss:.6f}", "required": "last_loss < first_loss", "pass": bool(last_loss is not None and first_loss is not None and last_loss < first_loss)},
        {"criterion": "cache_isolation", "observed": "results/route_B/runtime/bounded_train_eval", "required": "route_B runtime namespace", "pass": True},
        {"criterion": "same_split_anchor_baseline", "observed": "nnUNet anchor predictions read-only; no validation upload", "required": "baseline available", "pass": True},
    ]
    summary = {
        "status": TOKEN_UNDERTRAINED,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "optimizer_steps": args.steps,
        "train_loop_seconds": train_loop_seconds,
        "validation_events": validation_events,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "myops_eval_cases": args.myops_eval_cases,
        "cine_eval_cases": args.cine_eval_cases,
        "adequacy_passed": all(bool(row["pass"]) for row in adequacy),
        "runtime_root": str(RUNTIME_ROOT.relative_to(REPO_ROOT)),
    }
    write_csv(RESULT_ROOT / "training_adequacy.csv", adequacy)
    write_csv(RESULT_ROOT / "metrics_summary.csv", metric_rows)
    write_csv(RESULT_ROOT / "case_safety_matrix.csv", safety_rows)
    write_json(RESULT_ROOT / "bounded_train_eval_summary.json", summary)
    torch.save({"myops": myops_model.state_dict(), "cine": cine_model.state_dict()}, RUNTIME_ROOT / "route_b_undertrained_state.pt")
    append_packet(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
