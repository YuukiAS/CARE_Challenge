#!/usr/bin/env python3
"""Audit completion state for the 20260629 rescue goal.

This helper is intentionally conservative: it writes a completion audit every
time, but writes final_status.md only when the current artifacts prove that all
required rescue-goal evidence exists.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_ROOT = REPO_ROOT / "results/20260629_rescue_goal"

MYOPS_ROUTES = {
    "repaired_proposal": {
        "task": "prompts/tasks/20260629_repaired_proposal_repeat.md",
        "root": "results/20260629_repaired_proposal_repeat",
        "variants": [
            "repaired_uncertainty_hardneg",
            "repaired_posneg_scar_hardneg",
            "repaired_joint_calibrated_proposal",
        ],
    },
    "srr_v2": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": "results/20260629_srr_v2_unet_core",
        "source_roots": [
            "results/20260629_srr_v2_unet_core_htzhulab_fallback",
        ],
        "variants": [
            "srr_v2_multiscale_private_basic",
            "srr_v2_multiscale_private_proposal",
            "srr_v2_proposal_uncertainty_hardneg",
        ],
    },
    "cascade_teacher": {
        "task": "prompts/tasks/20260629_cascade_teacher_route.md",
        "root": "results/20260629_cascade_teacher_route",
        "variants": [
            "nnunet_anatomy_prior_refiner",
            "nnunet_pathology_teacher_srr_refiner",
            "coarse_to_fine_srr_roi",
        ],
    },
}

CINE_ROUTES = {
    "cine_motion_alignment": {
        "task": "prompts/tasks/20260629_cine_motion_alignment.md",
        "root": "results/20260629_cine_motion_alignment",
    },
    "cine_motion_pathology": {
        "task": "prompts/tasks/20260629_cine_motion_pathology.md",
        "root": "results/20260629_cine_motion_pathology",
    },
}

FINAL_STATUSES = {
    "REPAIRED_PROPOSAL_SELECTED",
    "SRR_V2_SELECTED",
    "CASCADE_TEACHER_SELECTED",
    "MULTI_ROUTE_REVISE_REPEAT",
    "STOP_PIPELINE_BUG",
    "STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL",
}

CINE_FINAL_STATUSES = {
    "CINE_MOTION_ALIGNMENT_SELECTED",
    "CINE_MOTION_DESCRIPTOR_SELECTED",
    "CINE_REFERENCE_ONLY",
    "CINE_REVISE",
    "CINE_STOP",
}

BLOCKING_STATUSES = {"MISSING", "INCOMPLETE", "ACTION_REQUIRED"}


@dataclass
class EvidenceRow:
    requirement: str
    status: str
    evidence: str
    detail: str


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def first_status(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("status:"):
            return stripped.split(":", 1)[1].strip().strip("`")
    return ""


def variant_ready(root: Path, variant: str) -> tuple[bool, str]:
    vdir = root / "variants" / variant
    summary = vdir / "summary.json"
    pred_dir = vdir / "predictions/fold_0/checkpoint_best"
    subgroup = vdir / "subgroup_metrics.csv"
    missing = []
    if not summary.is_file():
        missing.append(rel(summary))
    if not pred_dir.is_dir():
        missing.append(rel(pred_dir))
    if not subgroup.is_file():
        missing.append(rel(subgroup))
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, f"ready under {rel(vdir)}"


def variant_ready_any(roots: list[Path], variant: str) -> tuple[bool, str]:
    details = []
    for root in roots:
        ready, detail = variant_ready(root, variant)
        details.append(f"{rel(root)}: {detail}")
        if ready:
            return True, detail
    return False, "not ready in any source root (" + " | ".join(details) + ")"


def cascade_variant_ready(root: Path, variant: str) -> tuple[bool, str]:
    vdir = root / "variants" / variant
    summary = vdir / "summary.json"
    prediction_dir = ""
    if summary.is_file():
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
            prediction_dir = str(payload.get("prediction_dir", ""))
        except json.JSONDecodeError:
            prediction_dir = ""
    pred_dir = Path(prediction_dir) if prediction_dir else vdir / "predictions" / f"{variant}_oof_refiner" / "validation"
    comparison = vdir / "baseline_vs_refiner_by_subset.csv"
    metrics = vdir / "round10_fold0_very_short_metrics.csv"
    missing = []
    if not summary.is_file():
        missing.append(rel(summary))
    pred_count = len(list(pred_dir.glob("*.nii.gz"))) if pred_dir.is_dir() else 0
    if pred_count < 44:
        missing.append(f"{rel(pred_dir)} ({pred_count}/44 predictions)")
    if not comparison.is_file():
        missing.append(rel(comparison))
    if not metrics.is_file():
        missing.append(rel(metrics))
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, f"ready under {rel(vdir)} with {pred_count}/44 validation predictions"


def audit_myops_route(route: str, cfg: dict[str, object]) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    root = REPO_ROOT / str(cfg["root"])
    result = root / "result.md"
    selection = root / "selection.md"
    metrics = root / "metrics_summary.md"
    status = first_status(selection)
    rows.append(
        EvidenceRow(
            requirement=f"{route}: result/selection/metrics artifacts",
            status="PASS" if result.is_file() and selection.is_file() and metrics.is_file() else "MISSING",
            evidence=", ".join(rel(p) for p in [result, selection, metrics]),
            detail=f"selection_status={status or 'missing'}",
        )
    )
    variants = list(cfg["variants"])  # type: ignore[arg-type]
    source_roots = [root]
    for item in cfg.get("source_roots", []):  # type: ignore[union-attr]
        source_roots.append(REPO_ROOT / str(item))
    ready_count = 0
    details = []
    for variant in variants:
        if route == "cascade_teacher":
            ready, detail = cascade_variant_ready(root, variant)
        else:
            ready, detail = variant_ready_any(source_roots, variant)
        ready_count += int(ready)
        details.append(f"{variant}: {detail}")
    rows.append(
        EvidenceRow(
            requirement=f"{route}: all formal variants ready",
            status="PASS" if ready_count == len(variants) else "INCOMPLETE",
            evidence=f"{ready_count}/{len(variants)} variants ready",
            detail="; ".join(details),
        )
    )
    return rows


def audit_cine_route(route: str, cfg: dict[str, str]) -> list[EvidenceRow]:
    root = REPO_ROOT / cfg["root"]
    result = root / "result.md"
    selection = root / "selection.md"
    metrics = root / "metrics_summary.md"
    status = first_status(selection)
    return [
        EvidenceRow(
            requirement=f"{route}: result/selection artifacts",
            status="PASS" if result.is_file() and selection.is_file() else "MISSING",
            evidence=", ".join(rel(p) for p in [result, selection, metrics]),
            detail=f"selection_status={status or 'missing'}",
        )
    ]


def audit_goal_artifacts() -> list[EvidenceRow]:
    required = [
        GOAL_ROOT / "result.md",
        GOAL_ROOT / "MANIFEST.md",
        GOAL_ROOT / "progress.md",
        GOAL_ROOT / "route_status.csv",
        GOAL_ROOT / "pending_status.md",
        GOAL_ROOT / "gpu_action_status.csv",
        GOAL_ROOT / "gpu_action_status.md",
        GOAL_ROOT / "gpu_partition_status.csv",
        GOAL_ROOT / "gpu_partition_status.md",
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    rows = [
        EvidenceRow(
            requirement="goal: required non-final artifacts",
            status="PASS" if not missing else "MISSING",
            evidence=", ".join(rel(path) for path in required),
            detail="all present" if not missing else "missing " + ", ".join(missing),
        )
    ]
    final_status = GOAL_ROOT / "final_status.md"
    rows.append(
        EvidenceRow(
            requirement="goal: final_status.md only after all evidence is complete",
            status="PENDING" if not final_status.is_file() else "PRESENT",
            evidence=rel(final_status),
            detail="not written yet" if not final_status.is_file() else "existing final status requires review",
        )
    )
    return rows


def audit_gpu_action_ledger() -> list[EvidenceRow]:
    csv_path = GOAL_ROOT / "gpu_action_status.csv"
    md_path = GOAL_ROOT / "gpu_action_status.md"
    if not csv_path.is_file() or not md_path.is_file():
        return [
            EvidenceRow(
                requirement="operational: GPU action ledger",
                status="MISSING",
                evidence=", ".join(rel(path) for path in [csv_path, md_path]),
                detail="run scripts/evaluation/report_rescue_gpu_action_status.py",
            )
        ]
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    open_rows = [row for row in rows if row.get("status") in {"QUEUED_OR_RUNNING", "ACTION_REQUIRED"}]
    detail_parts = []
    for row in open_rows:
        fields = [
            row.get("item", ""),
            row.get("status", ""),
            row.get("required_action", ""),
        ]
        if row.get("wait_policy_status"):
            fields.append(f"wait={row.get('wait_policy_status', '')}")
        if row.get("pending_hours"):
            fields.append(f"pending_hours={row.get('pending_hours', '')}")
        if row.get("recheck_windows_elapsed"):
            fields.append(f"rechecks={row.get('recheck_windows_elapsed', '')}/12")
        if row.get("next_recheck_after"):
            fields.append(f"next={row.get('next_recheck_after', '')}")
        detail_parts.append(":".join(fields))
    detail = "; ".join(detail_parts)
    return [
        EvidenceRow(
            requirement="operational: GPU action ledger",
            status="PASS",
            evidence=", ".join(rel(path) for path in [csv_path, md_path]),
            detail=f"rows={len(rows)}, open_actions={len(open_rows)}" + (f"; {detail}" if detail else ""),
        )
    ]


def audit_gpu_partition_snapshot() -> list[EvidenceRow]:
    csv_path = GOAL_ROOT / "gpu_partition_status.csv"
    md_path = GOAL_ROOT / "gpu_partition_status.md"
    if not csv_path.is_file() or not md_path.is_file():
        return [
            EvidenceRow(
                requirement="operational: GPU partition snapshot",
                status="MISSING",
                evidence=", ".join(rel(path) for path in [csv_path, md_path]),
                detail="run scripts/evaluation/report_rescue_gpu_action_status.py",
            )
        ]
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    detail = "; ".join(
        f"{row.get('partition', '')}:pending={row.get('pending_jobs', '')}:running={row.get('running_jobs', '')}:reasons={row.get('pending_reasons', '')}"
        for row in rows
    )
    return [
        EvidenceRow(
            requirement="operational: GPU partition snapshot",
            status="PASS" if len(rows) >= 3 else "MISSING",
            evidence=", ".join(rel(path) for path in [csv_path, md_path]),
            detail=f"rows={len(rows)}" + (f"; {detail}" if detail else ""),
        )
    ]


def gpu_action_row(item: str) -> dict[str, str]:
    csv_path = GOAL_ROOT / "gpu_action_status.csv"
    if not csv_path.is_file():
        return {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("item") == item:
                return row
    return {}


def audit_operational_readiness() -> list[EvidenceRow]:
    srr_wrapper = REPO_ROOT / "jobs/src/run_srr_v2_unet_core.sh"
    srr_finalizer = REPO_ROOT / "scripts/evaluation/finalize_rescue_srr_route.py"
    cascade_wrapper = REPO_ROOT / "jobs/src/run_cascade_oof_refiner.sh"
    cascade_root = REPO_ROOT / MYOPS_ROUTES["cascade_teacher"]["root"]
    cascade_variants = list(MYOPS_ROUTES["cascade_teacher"]["variants"])
    wrapper_text = srr_wrapper.read_text(encoding="utf-8", errors="replace") if srr_wrapper.is_file() else ""
    finalizer_text = srr_finalizer.read_text(encoding="utf-8", errors="replace") if srr_finalizer.is_file() else ""
    isolated_ready = all(
        [
            srr_wrapper.is_file(),
            "OUT_ROOT" in wrapper_text,
            "PREFLIGHT_OUT_ROOT" in wrapper_text,
            srr_finalizer.is_file(),
            "--root" in finalizer_text,
        ]
    )
    cascade_ready = 0
    cascade_details = []
    for variant in cascade_variants:
        ready, detail = cascade_variant_ready(cascade_root, variant)
        cascade_ready += int(ready)
        cascade_details.append(f"{variant}: {detail}")
    cascade_complete = cascade_ready == len(cascade_variants)
    cascade_action = gpu_action_row("cascade_formal_array")
    cascade_status = cascade_action.get("status", "")
    cascade_scheduler = cascade_action.get("scheduler_state", "")
    cascade_job = cascade_action.get("job_id", "")
    cascade_submitted = cascade_status in {"QUEUED_OR_RUNNING", "DONE", "DONE_RECOVERED"} or cascade_scheduler in {
        "PENDING",
        "RUNNING",
        "CONFIGURING",
        "COMPLETING",
        "COMPLETED",
    }
    if cascade_complete:
        cascade_action_status = "PASS"
        cascade_detail = f"formal cascade variants ready {cascade_ready}/{len(cascade_variants)}; no GPU action required"
    elif cascade_submitted:
        cascade_action_status = "IN_PROGRESS"
        cascade_detail = (
            f"formal cascade variants ready {cascade_ready}/{len(cascade_variants)}; "
            f"submitted job {cascade_job or 'unknown'} is {cascade_scheduler or cascade_status}; "
            + "; ".join(cascade_details)
        )
    else:
        cascade_action_status = "ACTION_REQUIRED"
        cascade_detail = (
            f"formal cascade variants ready {cascade_ready}/{len(cascade_variants)}; "
            "formal command is `sbatch --array=0-2 jobs/src/run_cascade_oof_refiner.sh`; "
            "prior command approval review rejected it as three 7.5-hour shared-GPU jobs requiring explicit approval; "
            + "; ".join(cascade_details)
        )
    return [
        EvidenceRow(
            requirement="operational: cascade formal GPU action",
            status=cascade_action_status,
            evidence=rel(cascade_wrapper),
            detail=cascade_detail,
        ),
        EvidenceRow(
            requirement="operational: SRR-v2 isolated fallback readiness",
            status="PASS" if isolated_ready else "MISSING",
            evidence=", ".join(rel(path) for path in [srr_wrapper, srr_finalizer]),
            detail=(
                "OUT_ROOT/PREFLIGHT_OUT_ROOT and aggregation --root are available; new duplicate fallback GPU launches still require explicit approval if command review rejects them"
                if isolated_ready
                else "missing wrapper/finalizer support for isolated fallback roots"
            ),
        ),
    ]


def build_audit() -> list[EvidenceRow]:
    rows = audit_goal_artifacts()
    rows.extend(audit_gpu_action_ledger())
    rows.extend(audit_gpu_partition_snapshot())
    rows.extend(audit_operational_readiness())
    for route, cfg in MYOPS_ROUTES.items():
        rows.extend(audit_myops_route(route, cfg))
    for route, cfg in CINE_ROUTES.items():
        rows.extend(audit_cine_route(route, cfg))
    return rows


def write_csv(path: Path, rows: list[EvidenceRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["requirement", "status", "evidence", "detail"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_markdown(path: Path, rows: list[EvidenceRow]) -> None:
    blockers = [row for row in rows if row.status in BLOCKING_STATUSES]
    lines = [
        "# 20260629 Rescue Goal Completion Audit",
        "",
        "This audit is evidence-gated. It does not redefine the goal around partial outputs.",
        "",
        f"- completion_proven: `{not blockers}`",
        f"- blocking_requirements: `{len(blockers)}`",
        "",
        "| requirement | status | evidence | detail |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row.requirement} | {row.status} | `{row.evidence}` | {row.detail} |")
    if blockers:
        lines.extend(
            [
                "",
                "## Conclusion",
                "",
                "The rescue goal is not complete. Do not write `final_status.md` until every MyoPS route has formal variant evidence and the final route decision can be justified against the nnU-Net reference.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def infer_final_status(rows: list[EvidenceRow]) -> tuple[str, str]:
    blockers = [row for row in rows if row.status in BLOCKING_STATUSES]
    if blockers:
        return "", "completion audit has blocking requirements"
    repaired_status = first_status(REPO_ROOT / "results/20260629_repaired_proposal_repeat/selection.md")
    srr_status = first_status(REPO_ROOT / "results/20260629_srr_v2_unet_core/selection.md")
    cascade_status = first_status(REPO_ROOT / "results/20260629_cascade_teacher_route/selection.md")
    if repaired_status == "SELECT_REPAIRED_PROPOSAL_ROUTE":
        return "REPAIRED_PROPOSAL_SELECTED", repaired_status
    if srr_status in {"SELECT_SRR_V2_CORE", "SELECT_SRR_V2_PROPOSAL"}:
        return "SRR_V2_SELECTED", srr_status
    if cascade_status in {"SELECT_CASCADE_TEACHER_ROUTE", "SELECT_NNUNET_PLUS_REFINER"}:
        return "CASCADE_TEACHER_SELECTED", cascade_status
    if any(status.startswith("STOP_") for status in [repaired_status, srr_status, cascade_status]):
        return "STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL", "one or more route selections stopped"
    return "MULTI_ROUTE_REVISE_REPEAT", "all routes complete but no route selected"


def infer_cine_status() -> tuple[str, str]:
    align = first_status(REPO_ROOT / "results/20260629_cine_motion_alignment/selection.md")
    pathology = first_status(REPO_ROOT / "results/20260629_cine_motion_pathology/selection.md")
    if pathology == "SELECT_MOTION_DESCRIPTOR_ROUTE":
        return "CINE_MOTION_DESCRIPTOR_SELECTED", pathology
    if pathology == "SELECT_REFERENCE_CONTROL_ONLY":
        return "CINE_REFERENCE_ONLY", pathology
    if align == "SELECT_MOTION_ALIGNMENT":
        return "CINE_MOTION_ALIGNMENT_SELECTED", align
    if pathology in {"REVISE_CINE_MOTION"} or align == "REVISE_ALIGNMENT_AND_REPEAT":
        return "CINE_REVISE", f"{align}; {pathology}"
    return "CINE_STOP", f"{align}; {pathology}"


def write_final_status(path: Path, final_status: str, cine_status: str, reason: str, cine_reason: str) -> None:
    if final_status not in FINAL_STATUSES:
        raise ValueError(f"invalid final status: {final_status}")
    if cine_status not in CINE_FINAL_STATUSES:
        raise ValueError(f"invalid cine status: {cine_status}")
    lines = [
        "# 20260629 Rescue Goal Final Status",
        "",
        f"status: `{final_status}`",
        f"cine_status: `{cine_status}`",
        "",
        "## Basis",
        "",
        f"- MyoPS decision basis: {reason}",
        f"- Cine decision basis: {cine_reason}",
        "- Detailed requirement audit: `results/20260629_rescue_goal/completion_audit.md`",
        "",
        "No validation upload or upload-ready package was generated by this finalizer.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-final", action="store_true", help="Write final_status.md only if all evidence is complete.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_audit()
    write_csv(GOAL_ROOT / "completion_audit.csv", rows)
    write_markdown(GOAL_ROOT / "completion_audit.md", rows)
    final_status, reason = infer_final_status(rows)
    cine_status, cine_reason = infer_cine_status()
    if args.write_final:
        if not final_status:
            print({"final_written": False, "reason": reason, "audit": rel(GOAL_ROOT / "completion_audit.md")})
            return 1
        write_final_status(GOAL_ROOT / "final_status.md", final_status, cine_status, reason, cine_reason)
        print({"final_written": True, "status": final_status, "cine_status": cine_status})
        return 0
    print(
        {
            "completion_proven": bool(final_status),
            "final_status_candidate": final_status,
            "cine_status_candidate": cine_status,
            "audit": rel(GOAL_ROOT / "completion_audit.md"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
