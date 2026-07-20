#!/usr/bin/env python3
"""Build the Route B controller packet from current repository evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results" / "route_B"
PHASE_ROOT = RESULT_ROOT / "phases"
LOG_ROOT = REPO_ROOT / "logs" / "route_B"
TOKEN = "ROUTE_B_IMPLEMENTATION_NEEDS_REVISION"


REQUIRED_COMPONENTS = [
    ("myops_modality_stems", "MyoPS", "modality-specific LGE/C0/T2 stems", "missing_route_B_namespace"),
    ("myops_multiscale_encoder", "MyoPS", "multi-scale encoder", "missing_route_B_namespace"),
    ("myops_availability_router", "MyoPS", "availability and image-aware routing", "missing_route_B_gate_evidence"),
    ("myops_semantic_retrieval", "MyoPS", "shared/private/interaction dictionaries", "missing_route_B_trace"),
    ("myops_prototype_bank", "MyoPS", "case/fold-safe train or OOF prototypes", "missing_route_B_provenance"),
    ("myops_anatomy_decoder", "MyoPS", "union/LV/RV anatomy decoder", "missing_route_B_trace"),
    ("myops_scar_proposal", "MyoPS", "LGE-dominant scar proposal", "missing_route_B_intervention"),
    ("myops_edema_proposal", "MyoPS", "T2-conditioned edema proposal", "missing_route_B_intervention"),
    ("myops_soft_roi", "MyoPS", "proposal/anatomy/distance/uncertainty/nnU-Net soft ROI", "missing_route_B_trace"),
    ("myops_scar_refiner", "MyoPS", "small-ROI high-resolution scar refiner", "missing_route_B_intervention"),
    ("myops_edema_refiner", "MyoPS", "large-ROI edema refiner", "missing_route_B_intervention"),
    ("myops_bounded_residual", "MyoPS", "bounded nnU-Net anchored residual", "missing_route_B_anchor_identity"),
    ("myops_export", "MyoPS", "compact-to-raw CARE label export", "missing_route_B_export_qa"),
    ("cine_anatomy_source", "Cine", "CineMA or approved anatomy-source loader", "missing_route_B_runtime_receipt"),
    ("cine_frame_policy", "Cine", "ED/reference and key-frame policy", "missing_route_B_case_receipt"),
    ("cine_registration", "Cine", "actual transforms and warped evidence", "missing_route_B_warp_stats"),
    ("cine_syn_control", "Cine", "real ANTs/SyN or comparable control", "missing_route_B_control_receipt"),
    ("cine_temporal_dictionary", "Cine", "temporal dictionary consuming registered tensors", "missing_route_B_temporal_runtime"),
    ("cine_temporal_refiner", "Cine", "temporal aggregation/refiner", "missing_route_B_intervention"),
    ("checkpoint_resume_export", "Shared", "save/reload/resume/export consistency", "missing_route_B_runtime_receipt"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(args: list[str], check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if check and proc.returncode:
        raise RuntimeError(proc.stderr)
    return proc.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def component_rows() -> list[dict[str, object]]:
    rows = []
    source_map = {
        "MyoPS": "src/care_myocardium/models/srr_propref.py",
        "Cine": "src/care_myocardium/cine/",
        "Shared": "src/care_myocardium/",
    }
    for cid, branch, role, gap in REQUIRED_COMPONENTS:
        rows.append(
            {
                "component_id": cid,
                "branch": branch,
                "required_role": role,
                "route_b_status": "missing",
                "historical_context_status": "partial_or_unverified",
                "source_file_inspected": source_map[branch],
                "symbol_or_entrypoint": "",
                "final_output_dependency_evidence": "missing",
                "gradient_evidence": "missing",
                "intervention_evidence": "missing",
                "checkpoint_export_evidence": "missing" if cid == "checkpoint_resume_export" else "not_applicable",
                "gap_code": gap,
                "controller_decision": TOKEN,
            }
        )
    return rows


def build() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    for phase in ("B1_architecture_gap_inventory", "B2_full_architecture_implementation", "B3_implementation_gate", "B4_freeze", "B5_first_bounded_train_eval", "B6_finalizer_packet"):
        (PHASE_ROOT / phase).mkdir(parents=True, exist_ok=True)

    head = git(["rev-parse", "HEAD"])
    status = git(["status", "--short", "--branch"])
    files_read = [
        "AGENTS.md",
        ".agents/skills/slurm-routing-partition/SKILL.md",
        ".agents/skills/codex-workflow-protocol/SKILL.md",
        ".agents/skills/care-mapper/SKILL.md",
        "prompts/routes/README.md",
        "prompts/routes/route_B.md",
        "prompts/routes/route_B_executor_plan.yaml",
        "configs/routes/partition_routing.yaml",
        "docs/route_watchboard.md",
        "wiki/README.md",
        "wiki/COMPONENTS.csv",
    ]
    context = {
        "task": "RouteB-Controller",
        "route_id": "route_B",
        "status": TOKEN,
        "generated_at_utc": now(),
        "worktree": str(REPO_ROOT),
        "git_head": head,
        "git_status_short": status.splitlines(),
        "critic_token_confirmed": "ROUTE_B_PLANNING_READY_FOR_CONTROLLER",
        "formal_training_submitted": False,
        "slurm_jobs_submitted": [],
        "runtime_paths": {
            "result_root": "results/route_B",
            "runtime_root": "results/route_B/runtime",
            "log_root": "logs/route_B",
            "lock_root": "results/route_B/locks",
        },
        "files_read": files_read,
        "hashes": {path: sha256(REPO_ROOT / path) for path in files_read if (REPO_ROOT / path).is_file()},
        "route_decision_boundaries": {
            "route_promotion_decision": "NOT_REVIEWED",
            "route_negative_decision": "NOT_REVIEWED",
            "scientific_resolution_status": "AWAITING_REVIEW",
        },
    }
    write_json(RESULT_ROOT / "controller_context.json", context)

    write_csv(
        RESULT_ROOT / "controller_ledger.csv",
        [
            {"timestamp_utc": now(), "phase": "B0", "git_head": head, "decision": "critic_token_confirmed", "next_action": "inventory"},
            {"timestamp_utc": now(), "phase": "B1", "git_head": head, "decision": "route_B_namespaces_absent", "next_action": "failure_packet"},
            {"timestamp_utc": now(), "phase": "B3", "git_head": head, "decision": TOKEN, "next_action": "finalizer_packet"},
        ],
    )

    write(
        RESULT_ROOT / "controller_bootstrap_snapshot.md",
        f"""# Route B Controller Bootstrap Snapshot

- route: `route_B`
- worktree: `{REPO_ROOT}`
- git_head_at_bootstrap: `{head}`
- critic_token: `ROUTE_B_PLANNING_READY_FOR_CONTROLLER`
- executor_plan_validation: `PASS`
- formal_training_submitted: `false`
- validation_upload_performed: `false`
- review_md_written: `false`

Route B implementation-before-training gate is mandatory for complete MyoPS and Cine. Current route_B-specific implementation namespaces were absent at bootstrap, so the controller cannot submit formal training.
""",
    )

    rows = component_rows()
    write_csv(RESULT_ROOT / "architecture_component_trace.csv", rows)
    write(
        RESULT_ROOT / "implementation_gap_inventory.md",
        "# Route B Implementation Gap Inventory\n\n"
        "Current controller state: `ROUTE_B_IMPLEMENTATION_NEEDS_REVISION`.\n\n"
        "The route_B-specific source, script, config, job, test, result, log, and lock namespaces were absent before this controller run. Historical SRR/Cine files exist outside the route_B namespace and are useful context, but they do not satisfy Route B's implementation-before-training gate by themselves.\n\n"
        "| component | branch | gap |\n| --- | --- | --- |\n"
        + "\n".join(f"| `{row['component_id']}` | {row['branch']} | {row['gap_code']} |" for row in rows)
        + "\n",
    )
    write(
        RESULT_ROOT / "implementation_snapshot.md",
        f"""# Route B Implementation Snapshot

Status: `{TOKEN}`

No formal Route B implementation was completed. The controller found historical partial MyoPS and Cine implementation context in `src/care_myocardium/models/` and `src/care_myocardium/cine/`, but no route_B-owned implementation entrypoints existed at bootstrap. Because the contract requires complete MyoPS and Cine implementation fidelity before formal training, this packet stops before Slurm training.

Important inherited context:

- `src/care_myocardium/models/srr_propref.py` includes prior SRR propose/refine modules, residual gating, decode helpers, and no-T2 safety logic.
- `src/care_myocardium/cine/` includes prior M10 Cine adapter, registration, and temporal modules.
- `results/20260714_srr_v3_m10_continuation_reconciliation/` remains `NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE`; it is not Route B completion evidence.

Route B-specific missing evidence:

- real-case forward over required MyoPS modality groups;
- three-case Cine temporal gate with non-reference frames;
- finite/nonzero losses and gradients to every required module;
- on/off interventions changing final logits or labels;
- save/reload/resume/export consistency;
- implementation freeze receipt.
""",
    )

    gate_payload = {
        "status": TOKEN,
        "success_token": "ROUTE_B_IMPLEMENTATION_GATE_PASSED",
        "gate_passed": False,
        "formal_training_allowed": False,
        "formal_training_submitted": False,
        "reason": "Route B-owned implementation paths and runtime gate evidence are missing; inherited partial code cannot satisfy complete MyoPS+Cine implementation gate.",
        "myops": {row["component_id"]: False for row in rows if row["branch"] == "MyoPS"},
        "cine": {row["component_id"]: False for row in rows if row["branch"] == "Cine"},
        "shared": {row["component_id"]: False for row in rows if row["branch"] == "Shared"},
        "monitor_state": False,
        "submitted_only_state": False,
    }
    write_json(RESULT_ROOT / "implementation_gate.json", gate_payload)
    write(
        RESULT_ROOT / "implementation_gate.md",
        f"""# Route B Implementation Gate

Completion token: `{TOKEN}`

Gate passed: `false`

Formal training allowed: `false`

This is an implementation failure packet, not a monitor packet and not a ready-for-review packet. The complete SRR-v3 MyoPS+Cine gate did not pass because route_B-owned implementation paths and current runtime evidence are missing.
""",
    )
    write_csv(
        RESULT_ROOT / "gradient_and_intervention_report.csv",
        [
            {
                "area": row["component_id"],
                "gradient_reaches_required_module": "missing",
                "intervention_changes_final_logits_or_labels": "missing",
                "evidence_path": "",
                "decision": TOKEN,
            }
            for row in rows
        ],
    )
    write_csv(
        RESULT_ROOT / "cine_registration_temporal_report.csv",
        [
            {
                "check": "three_real_cases_three_nonreference_frames",
                "status": "missing",
                "evidence_path": "",
                "decision": TOKEN,
            },
            {
                "check": "registration_warp_statistics",
                "status": "missing",
                "evidence_path": "",
                "decision": TOKEN,
            },
            {
                "check": "temporal_registered_vs_unregistered_intervention",
                "status": "missing",
                "evidence_path": "",
                "decision": TOKEN,
            },
        ],
    )
    write_json(
        RESULT_ROOT / "save_reload_export_report.json",
        {
            "status": TOKEN,
            "save_reload_consistency": "missing",
            "resume_consistency": "missing",
            "myops_official_label_export_qa": "missing",
            "cine_official_layout_export_qa": "missing",
            "heavy_artifacts_written": False,
        },
    )
    write_json(
        RESULT_ROOT / "implementation_freeze_receipt.json",
        {
            "status": "NOT_FROZEN",
            "reason": "Implementation gate failed before freeze.",
            "code_config_data_hashes": {},
            "formal_training_allowed": False,
        },
    )
    mapper_common = f"""Route-local mapper status: `{TOKEN}`.

Root wiki mutation is deferred by route portfolio policy. Current code/evidence mapping remains route-local under `results/route_B/`.

Mapped source context:

- `src/care_myocardium/models/srr_propref.py`: historical MyoPS SRR context, not Route B gate completion.
- `src/care_myocardium/cine/`: historical Cine M10 context, not Route B gate completion.
- `wiki/COMPONENTS.csv`: current reviewed root state is M9/M10 diagnostic/NOT_REVIEWED.

Mapper conclusion: required Route B component final-output dependency, gradient, intervention, save/reload, export, and Cine temporal evidence are missing.
"""
    write(RESULT_ROOT / "mapper_report_draft.md", "# Route B Mapper Report Draft\n\n" + mapper_common)
    write(RESULT_ROOT / "mapper_report_final.md", "# Route B Mapper Report Final\n\n" + mapper_common)
    write(
        RESULT_ROOT / "architecture_delta_final.md",
        f"""# Route B Architecture Delta Final

Status: `{TOKEN}`

No root wiki update was performed. No route promotion, hosted metric claim, validation upload, M11 authorization, or cross-route merge is made.

Route-local delta: new controller packet, preflight, validators, and known-bad fixtures document that the complete SRR-v3 MyoPS+Cine implementation gate is not satisfied in this worktree.
""",
    )
    write_json(
        RESULT_ROOT / "finalizer_state.json",
        {
            "task": "RouteB-Controller",
            "state": "READY_FOR_LOCAL_PACKET_COMMIT_NEEDS_REVISION",
            "completion": TOKEN,
            "generated_at_utc": now(),
            "terminal_accounting_required": False,
            "slurm_jobs": [],
            "post_completion_aggregation_required": False,
            "mapper_final_status": TOKEN,
            "validator_reports": [
                "results/route_B/validator_implementation_report.json",
                "results/route_B/validator_packet_report.json",
            ],
            "route_promotion_decision": "NOT_REVIEWED",
            "route_negative_decision": "NOT_REVIEWED",
            "scientific_resolution_status": "AWAITING_REVIEW",
            "review_md_written": False,
            "push_performed": False,
        },
    )
    write(
        RESULT_ROOT / "result.md",
        f"""# Route B Controller Result

Final controller token: `{TOKEN}`

The controller did not start formal training. It confirmed the Critic token and executor-plan validity, then found that the route_B implementation namespace and current runtime gate evidence required by the contract were absent. Historical MyoPS/Cine code exists, but Route B requires a complete current MyoPS+Cine implementation-before-training gate.

This packet is ready for independent review as a failure/revision packet, not as a completed implementation packet.
""",
    )
    write(
        RESULT_ROOT / "completion_check.md",
        f"""# Route B Completion Check

Completion token: `{TOKEN}`

This is a failure/revision completion check, not a ready-for-review completion check. Formal training did not run and no Slurm job was submitted. The implementation-before-training gate failed before freeze because required Route B MyoPS and Cine implementation evidence is missing.

Forbidden and not performed: `review.md`, push, validation packaging/upload, hosted metric claim, route promotion, scientific stop, M11, cross-route merge.
""",
    )
    write(
        RESULT_ROOT / "review_request.md",
        f"""# Route B Review Request

Requested independent reviewer action: read-only review of `results/route_B/` as a controller failure/revision packet.

Expected reviewer decision class: `ROUTE_B_REVIEW_NEEDS_REVISION` or `ROUTE_B_REVIEW_NEEDS_EVIDENCE`, unless the reviewer finds packet construction errors requiring a different allowed review token.

The reviewer must not fix files, train, package validation, upload, push, start M11, merge routes, or write outside `results/route_B/review.md`.
""",
    )
    write(
        RESULT_ROOT / "controller_report.md",
        f"""# Route B Controller Report

controller_run_status: INCOMPLETE
operational_completion_status: {TOKEN}
experiment_adequacy_decision: FORMAL_TRAINING_NOT_STARTED_IMPLEMENTATION_GATE_FAILED
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_ROUTE_B_PACKET_ONLY
git_commit_decision: LOCAL_LIGHTWEIGHT_PACKET_COMMIT_REQUIRED
git_push_decision: SKIP_PUSH

## Summary

Route B was authorized by Critic token `ROUTE_B_PLANNING_READY_FOR_CONTROLLER`. The controller validated the executor plan and enforced the complete MyoPS+Cine implementation-before-training gate. The gate failed before formal runtime because route_B-owned implementation paths and current runtime evidence were missing.

No Slurm training job was submitted, so there is no monitor packet and no pending/running/submitted-only state being treated as completion.

## Published Files

Only route_B-local source helpers, validators, tests, Markdown, CSV, and JSON packet files are intended for local lightweight commit.

## Blocked Actions

- formal training remains blocked until complete MyoPS+Cine implementation gate passes
- validation packaging/upload remains blocked
- hosted metric claims remain blocked
- route promotion remains blocked
- scientific stop remains blocked
- M11 remains blocked
- cross-route merge remains blocked
- push remains blocked

next_required_action: independent read-only reviewer inspects this failure/revision packet.
reason_if_not_published: not applicable after local lightweight commit.
reason_if_no_route_promotion: implementation gate failed and independent review has not run.
""",
    )

    commands = [
        "python scripts/ops/validate_executor_plan.py prompts/routes/route_B_executor_plan.yaml",
        "python scripts/route_B/run_preflight.py --strict --print-contract",
        "AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit python scripts/architecture/run_toolkit_healthcheck.py --check",
        "python scripts/route_B/build_controller_packet.py",
        "python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json",
        "python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json",
        "pytest -q tests/route_B",
        "git diff --check",
    ]
    write(
        RESULT_ROOT / "commands_run.md",
        "# Route B Commands Run\n\n"
        "## Commands\n\n"
        + "\n".join(f"- `{cmd}`" for cmd in commands)
        + "\n\n## Outcomes\n\n"
        "- `python scripts/ops/validate_executor_plan.py prompts/routes/route_B_executor_plan.yaml`: exit 0, executor plan validation passed.\n"
        "- First `python scripts/route_B/run_preflight.py --strict --print-contract`: exit 1 due repo-local import path packaging; no training credit and no Slurm submission.\n"
        "- Replacement same-contract preflight after adding repo root to `sys.path`: exit 0, wrote `results/route_B/preflight_receipt.json`.\n"
        "- Toolkit healthcheck: exit 0; wrapper updated `wiki/toolkit_healthcheck.json`, then that out-of-scope root-wiki change was restored and not included in the route_B packet.\n"
        "- `python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`: exit 0, `PASS_FAILURE_STATE_CONSISTENT` with 20 missing/unverified required components.\n"
        "- `python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`: exit 0, packet structure `PASS`.\n"
        "- `pytest -q tests/route_B`: exit 0, 1 known-bad fixture test passed.\n"
        "- `git diff --check`: exit 0.\n\n"
        "No `sbatch`, `srun`, validation upload, push, or M11 command was run.\n",
    )

    files = sorted(p for p in RESULT_ROOT.iterdir() if p.is_file())
    write(
        RESULT_ROOT / "MANIFEST.md",
        "# Route B Manifest\n\n"
        + "\n".join(f"- `{rel(path)}`" for path in files if path.name != "MANIFEST.md")
        + "\n",
    )


if __name__ == "__main__":
    build()
