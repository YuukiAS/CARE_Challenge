#!/usr/bin/env python3
"""Wave0 binding and clean-checkout audit for CARE Batch10."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260724_care_myops_batch10_deadline_rescue"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
BATCH9_ROOT = REPO_ROOT / "results/20260723_care_myops_batch9_exposed_issues_repair"
REQUIRED_IMPORTS = [
    "src.care_myocardium.data.care_mm_batch9",
    "src.care_myocardium.losses.care_mm_losses",
    "src.care_myocardium.models.care_mm_reliable_distill",
    "src.care_myocardium.training.nnUNetTrainerCAREMMReliableDistill",
    "scripts.evaluation.evaluate_care_mm_batch9",
]
REQUIRED_READ_FILES = [
    "AGENTS.md",
    "START_HERE_FOR_GPT.md",
    "GPT_PLANNER_CARE_PROTOCOL.md",
    "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
    "prompts/AGENT_FLOW_V2_PROTOCOL.md",
    "prompts/HANDOFF_GATE_POLICY.md",
    "prompts/GPT_HARD_GATE_PROMPT.md",
    "prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md",
    "prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md",
    "prompts/routes/handoffs/CURRENT.md",
    "wiki/README.md",
    ".agents/skills/slurm-routing-partition/SKILL.md",
    ".agents/skills/care-mapper/SKILL.md",
    "results/srr_production/code_maturity/batch10_deadline_rescue_planner_decision_20260724.md",
    "configs/care_mm/batch10_deadline_rescue.yaml",
    "prompts/tasks/20260724_care_myops_batch10_deadline_rescue_controller.md",
    "prompts/tasks/20260724_care_myops_batch10_deadline_rescue_executor_plan.yaml",
]


def run(cmd: list[str], *, cwd: Path = REPO_ROOT, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, env=env)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_stdout(*args: str) -> str:
    return run(["git", *args], check=True).stdout.strip()


def is_tracked(path: str) -> bool:
    return bool(run(["git", "ls-files", "--", path]).stdout.strip())


def file_record(path: str) -> dict[str, Any]:
    full = REPO_ROOT / path
    return {"path": path, "exists": full.is_file(), "tracked": is_tracked(path), "sha256": sha256_file(full)}


def collect_job_ids() -> list[str]:
    ids: set[str] = set()
    preflight = read_json(BATCH9_ROOT / "preflight_slurm_jobs.json", {}) or {}
    for job in preflight.get("jobs", []):
        jid = str(job.get("job_id", ""))
        if jid.isdigit():
            ids.add(jid)
    chain = read_json(BATCH9_ROOT / "slurm_formal_chain.json", {}) or {}
    for key in ("finalizer_afterany",):
        jid = str(chain.get(key, ""))
        if jid.isdigit():
            ids.add(jid)
    for seed_key in ("seed20260723", "seed20260724"):
        seed_payload = chain.get(seed_key, {})
        if isinstance(seed_payload, dict):
            for key in ("moddrop_control", "reliable_distill"):
                jid = str(seed_payload.get(key, ""))
                if jid.isdigit():
                    ids.add(jid)
    for path in sorted(BATCH9_ROOT.glob("finalizer_retry_*.json")):
        retry = read_json(path, {}) or {}
        for key in ("job_id", "retry_job_id", "finalizer_job_id"):
            jid = str(retry.get(key, ""))
            if jid.isdigit():
                ids.add(jid)
    log_root = REPO_ROOT / "logs/20260723_care_myops_batch9_exposed_issues_repair"
    if log_root.exists():
        for path in log_root.rglob("*.log"):
            ids.update(re.findall(r"_([0-9]{7,})_", path.name))
    return sorted(ids, key=int)


def sacct_records(job_ids: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"query_job_ids": job_ids, "queried_at_unix": int(time.time()), "status": "NOT_RUN", "records": [], "errors": []}
    if not job_ids:
        payload["status"] = "NO_JOB_IDS"
        return payload
    cmd = ["sacct", "-j", ",".join(job_ids), "--format=JobIDRaw,JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList%40", "-P", "-n"]
    proc = run(cmd)
    payload["command"] = " ".join(cmd)
    payload["returncode"] = proc.returncode
    if proc.returncode != 0:
        payload["status"] = "FAIL"
        payload["errors"].append(proc.stderr.strip() or "sacct failed")
        return payload
    fields = ["JobIDRaw", "JobID", "JobName", "Partition", "State", "ExitCode", "Elapsed", "NodeList"]
    rows = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        values = line.split("|")
        rows.append({fields[i]: values[i] if i < len(values) else "" for i in range(len(fields))})
    payload["records"] = rows
    parent = {row["JobIDRaw"]: row for row in rows if row.get("JobIDRaw") in job_ids}
    missing = [jid for jid in job_ids if jid not in parent]
    nonterminal = [
        {"job_id": jid, "state": row.get("State", "")}
        for jid, row in parent.items()
        if row.get("State", "").split()[0] in {"", "PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "REQUEUED"}
    ]
    if missing:
        payload["errors"].append(f"missing parent sacct records: {missing}")
    if nonterminal:
        payload["errors"].append(f"nonterminal parent jobs: {nonterminal}")
    payload["all_parent_jobs_terminal"] = not missing and not nonterminal
    payload["status"] = "PASS" if payload["all_parent_jobs_terminal"] else "FAIL"
    return payload


def rows_by_seed_variant(path: Path) -> dict[tuple[str, str], list[dict[str, str]]]:
    out: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in read_csv(path):
        out.setdefault((str(row.get("seed", "")), str(row.get("variant", ""))), []).append(row)
    return out


def existing_checkpoint_inventory() -> list[dict[str, Any]]:
    runtime_selected = rows_by_seed_variant(BATCH9_ROOT / "checkpoint_selection.csv")
    direct_selected = rows_by_seed_variant(BATCH9_ROOT / "direct_checkpoint_selection.csv")
    chain = read_json(BATCH9_ROOT / "slurm_formal_chain.json", {}) or {}
    required = [
        ("20260723", "student_direct_reliable", "selected_from_runtime_receipt"),
        ("20260724", "student_direct_reliable", "selected_from_runtime_receipt"),
        ("20260723", "teacher_full_view", "selected_from_runtime_receipt"),
        ("20260724", "teacher_full_view", "selected_from_runtime_receipt"),
        ("20260723", "student_moddrop_control", "epoch25"),
        ("20260724", "student_moddrop_control", "epoch25"),
        ("20260723", "student_reliable_distill", "epoch25"),
        ("20260724", "student_reliable_distill", "epoch25"),
    ]
    rows: list[dict[str, Any]] = []
    for seed, variant, source in required:
        receipts: list[dict[str, str]] = []
        authoritative = ""
        if source == "epoch25":
            authoritative = str(BATCH9_ROOT.relative_to(REPO_ROOT) / Path(f"runtime/seed{seed}/{variant}/checkpoint_epoch25.pt"))
            receipts.append({"receipt": "fixed_epoch25_path", "selected_checkpoint": authoritative, "selection_rule": "batch10_fixed_epoch25_existing_checkpoint"})
        else:
            seed_payload = chain.get(f"seed{seed}", {}) if isinstance(chain, dict) else {}
            chain_key = "direct_selected_checkpoint" if variant == "student_direct_reliable" else "teacher_selected_checkpoint"
            authoritative = str(seed_payload.get(chain_key, "")) if isinstance(seed_payload, dict) else ""
            if authoritative:
                receipts.append({"receipt": "slurm_formal_chain.json", "selected_checkpoint": authoritative, "selection_rule": "authoritative_batch10_runtime_binding"})
            for row in runtime_selected.get((seed, variant), []):
                receipts.append({**row, "receipt": "checkpoint_selection.csv"})
            for row in direct_selected.get((seed, variant), []):
                if row.get("status") == "SELECTED":
                    receipts.append({**row, "receipt": "direct_checkpoint_selection.csv"})
        stale_conflicts = sorted({r.get("selected_checkpoint") or r.get("checkpoint") or "" for r in receipts if (r.get("selected_checkpoint") or r.get("checkpoint")) and (r.get("selected_checkpoint") or r.get("checkpoint")) != authoritative})
        ckpt = authoritative
        full = REPO_ROOT / ckpt if ckpt else REPO_ROOT / "__missing__"
        status = "FOUND" if ckpt and full.is_file() else "MISSING"
        if stale_conflicts and status == "FOUND":
            status = "FOUND_WITH_STALE_RECEIPT_CONFLICT"
        rows.append({
            "seed": seed,
            "variant": variant,
            "required_source": source,
            "candidate_status": status,
            "stale_receipt_conflict_count": len(stale_conflicts),
            "stale_conflict_paths": json.dumps(stale_conflicts, sort_keys=True),
            "checkpoint_path": ckpt,
            "checkpoint_exists": int(full.is_file()),
            "checkpoint_sha256": sha256_file(full),
            "receipts": json.dumps([
                {
                    "receipt": row.get("receipt"),
                    "selected_checkpoint": row.get("selected_checkpoint") or row.get("checkpoint"),
                    "selection_rule": row.get("selection_rule"),
                    "epoch": row.get("epoch") or row.get("checkpoint_epoch"),
                }
                for row in receipts
            ], sort_keys=True),
        })
    return rows


def val_case_fingerprint() -> dict[str, Any]:
    rows = read_csv(BATCH9_ROOT / "fold0_case_manifest.csv")
    val = sorted(row["case_id"] for row in rows if row.get("split") == "val")
    digest = hashlib.sha256("\n".join(val).encode("utf-8")).hexdigest()
    return {"validation_case_count": len(val), "validation_case_sha256": digest, "validation_cases": val}


def preprocessing_fingerprint() -> dict[str, Any]:
    pre_root = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
    fullres = pre_root / "nnUNetPlans_3d_fullres"
    files = [
        "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json",
        "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json",
        "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json",
    ]
    audit = {
        "schema_version": 1,
        "status": "PASS",
        "plans_identifier_expected": "nnUNetResEncUNetMPlans",
        "configuration": "3d_fullres",
        "preprocessed_root": str(fullres.relative_to(REPO_ROOT)),
        "tracked_or_external_fingerprints": [file_record(path) for path in files],
        "case_property_file_count": len(sorted(fullres.glob("*.pkl"))),
        "case_data_file_count": len(sorted(fullres.glob("*.b2nd"))),
        "all_44_case_properties_required": True,
        **val_case_fingerprint(),
    }
    missing_val_props = [case_id for case_id in audit["validation_cases"] if not (fullres / f"{case_id}.pkl").is_file()]
    audit["missing_validation_case_properties"] = missing_val_props
    if missing_val_props or any(not rec["exists"] for rec in audit["tracked_or_external_fingerprints"]):
        audit["status"] = "FAIL"
    return audit


def clean_checkout_import_audit() -> dict[str, Any]:
    dependencies = [
        "src/care_myocardium/data/case_metadata.py",
        "src/care_myocardium/data/care_mm_batch9.py",
        "src/care_myocardium/losses/care_mm_losses.py",
        "src/care_myocardium/models/care_mm_reliable_distill.py",
        "src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py",
        "scripts/evaluation/evaluate_care_mm_batch9.py",
    ]
    tracked = {path: is_tracked(path) for path in dependencies}
    payload: dict[str, Any] = {
        "schema_version": 1,
        "method": "git_archive_to_tmp_then_import_with_current_environment",
        "required_imports": REQUIRED_IMPORTS,
        "tracked_dependency_status": tracked,
        "status": "PASS",
        "imports": [],
    }
    with tempfile.TemporaryDirectory(prefix="care_batch10_clean_") as tmp:
        extract = Path(tmp) / "repo"
        extract.mkdir()
        listed = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
        for raw_name in listed.split(b"\0"):
            if not raw_name:
                continue
            rel = raw_name.decode("utf-8")
            src = REPO_ROOT / rel
            dst = extract / rel
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        env = dict(**os.environ)
        env["PYTHONPATH"] = str(extract)
        for module in REQUIRED_IMPORTS:
            proc = run([sys.executable, "-c", f"import {module}; print('ok')"], cwd=extract, env=env)
            payload["imports"].append({"module": module, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()})
            if proc.returncode != 0:
                payload["status"] = "FAIL"
    if not all(tracked.values()):
        payload["status"] = "FAIL"
        payload.setdefault("errors", []).append("one or more first-party dependencies are not tracked")
    return payload


def runtime_freeze(accounting: dict[str, Any]) -> dict[str, Any]:
    finalizer = read_json(BATCH9_ROOT / "finalizer_state.json", {})
    report_lines = (BATCH9_ROOT / "controller_report.md").read_text(encoding="utf-8", errors="ignore").splitlines()
    inventory = existing_checkpoint_inventory()
    missing = [row for row in inventory if not row.get("checkpoint_exists")]
    conflicts = [row for row in inventory if row.get("stale_receipt_conflict_count") or row.get("selection_conflict")]
    if missing:
        freeze_status = "FROZEN_WITH_REPAIR_REQUIRED"
    elif conflicts:
        freeze_status = "FROZEN_WITH_STALE_RECEIPT_CONFLICTS_RECORDED"
    else:
        freeze_status = "FROZEN"
    return {
        "schema_version": 1,
        "status": freeze_status,
        "human_stopped_wave6_after_epoch25": True,
        "resume_old_wave6_to_epoch100_forbidden": True,
        "batch9_result_root": str(BATCH9_ROOT.relative_to(REPO_ROOT)),
        "batch9_finalizer_status": finalizer.get("status"),
        "batch9_controller_verification_decision": finalizer.get("controller_verification_decision"),
        "batch9_controller_report_first_lines": report_lines[:5],
        "job_ids": accounting.get("query_job_ids", []),
        "slurm_accounting_status": accounting.get("status"),
        "slurm_all_parent_jobs_terminal": accounting.get("all_parent_jobs_terminal"),
        "checkpoint_inventory_status": {"row_count": len(inventory), "missing_rows": len(missing), "selection_conflict_rows": len(conflicts)},
        "screenshot_is_human_supplied_not_terminal_packet": True,
        "epoch25_control_distill_is_input_only_not_completion": True,
    }


def controller_context() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "B10_W0_BIND_FREEZE_AND_CLEAN_CHECKOUT",
        "task_key": TASK_KEY,
        "cwd": str(REPO_ROOT),
        "git_head": git_stdout("rev-parse", "HEAD"),
        "git_branch": git_stdout("branch", "--show-current"),
        "git_status_short": run(["git", "status", "--short", "--branch"]).stdout.splitlines(),
        "task_prompt_path": "prompts/tasks/20260724_care_myops_batch10_deadline_rescue_controller.md",
        "task_prompt_sha256": sha256_file(REPO_ROOT / "prompts/tasks/20260724_care_myops_batch10_deadline_rescue_controller.md"),
        "executor_plan_path": "prompts/tasks/20260724_care_myops_batch10_deadline_rescue_executor_plan.yaml",
        "executor_plan_sha256": sha256_file(REPO_ROOT / "prompts/tasks/20260724_care_myops_batch10_deadline_rescue_executor_plan.yaml"),
        "AGENTS_sha256": sha256_file(REPO_ROOT / "AGENTS.md"),
        "slurm_skill_sha256": sha256_file(REPO_ROOT / ".agents/skills/slurm-routing-partition/SKILL.md"),
        "care_mapper_skill_sha256": sha256_file(REPO_ROOT / ".agents/skills/care-mapper/SKILL.md"),
        "files_read": [file_record(path) for path in REQUIRED_READ_FILES],
    }


def write_bootstrap_snapshot(context: dict[str, Any], freeze: dict[str, Any]) -> None:
    text = "\n".join([
        "# Batch10 Wave0 Bootstrap Snapshot",
        "",
        f"task_key: {TASK_KEY}",
        f"git_head: {context['git_head']}",
        f"git_branch: {context['git_branch']}",
        f"batch9_freeze_status: {freeze['status']}",
        f"batch9_controller_verification_decision: {freeze.get('batch9_controller_verification_decision')}",
        "human_stopped_wave6_after_epoch25: true",
        "resume_old_wave6_to_epoch100_forbidden: true",
        "",
    ])
    (RESULT_ROOT / "controller_bootstrap_snapshot.md").write_text(text, encoding="utf-8")


def main() -> int:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    context = controller_context()
    accounting = sacct_records(collect_job_ids())
    inventory = existing_checkpoint_inventory()
    clean = clean_checkout_import_audit()
    preproc = preprocessing_fingerprint()
    freeze = runtime_freeze(accounting)
    write_json(RESULT_ROOT / "controller_context.json", context)
    write_json(RESULT_ROOT / "batch9_runtime_freeze.json", freeze)
    write_json(RESULT_ROOT / "clean_checkout_import_audit.json", clean)
    write_json(RESULT_ROOT / "preprocessing_fingerprint_audit.json", preproc)
    write_json(RESULT_ROOT / "batch9_slurm_accounting_freeze.json", accounting)
    write_csv(RESULT_ROOT / "existing_checkpoint_inventory.csv", inventory)
    decision = "NEEDS_REPAIR" if clean["status"] != "PASS" or preproc["status"] != "PASS" else "W0_AUDIT_WRITTEN"
    write_csv(RESULT_ROOT / "controller_ledger.csv", [{
        "timestamp_unix": int(time.time()),
        "phase": "B10_W0_BIND_FREEZE_AND_CLEAN_CHECKOUT",
        "git_head": context["git_head"],
        "task_hash": context["task_prompt_sha256"],
        "job_states": accounting.get("status"),
        "decision": decision,
        "next_action": "repair clean checkout/import issues before inference" if decision == "NEEDS_REPAIR" else "controller inspect W0 receipts",
    }])
    write_bootstrap_snapshot(context, freeze)
    summary = {
        "clean_checkout_status": clean["status"],
        "preprocessing_status": preproc["status"],
        "checkpoint_inventory_rows": len(inventory),
        "slurm_accounting_status": accounting["status"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if clean["status"] == "PASS" and preproc["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
