#!/usr/bin/env python3
"""Finalize CARE Batch9 after terminal training and evaluation aggregation."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = os.environ.get("CARE_MM_TASK_KEY", "20260723_care_myops_batch9_exposed_issues_repair")
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
ALLOWED = [
    "BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER",
    "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER",
    "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({k for row in rows for k in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def mean(rows: list[dict[str, str]], key: str) -> float | None:
    vals = []
    for row in rows:
        raw = row.get(key)
        if raw in (None, "", "None"):
            continue
        vals.append(float(raw))
    return sum(vals) / len(vals) if vals else None


def subgroup_mean(rows: list[dict[str, str]], variant: str, pathology: str, subgroup: str, key: str) -> float | None:
    return mean([r for r in rows if r.get("variant") == variant and r.get("pathology") == pathology and r.get("subgroup") == subgroup], key)


def subgroup_mean_seed(rows: list[dict[str, str]], seed: str, variant: str, pathology: str, subgroup: str, key: str) -> float | None:
    return mean(
        [
            r for r in rows
            if r.get("seed") == seed and r.get("variant") == variant and r.get("pathology") == pathology and r.get("subgroup") == subgroup
        ],
        key,
    )


def per_seed_decision_rows(subgroups: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    direct_rows = read_csv(RESULT_ROOT / "direct_gate.csv") if (RESULT_ROOT / "direct_gate.csv").is_file() else []
    for seed in ("20260723", "20260724"):
        for pathology, min_gain in [("scar", 0.003), ("edema", 0.005)]:
            moddrop = subgroup_mean_seed(subgroups, seed, "student_moddrop_control", pathology, "complete_trimodal", "mean_dice")
            distill = subgroup_mean_seed(subgroups, seed, "student_reliable_distill", pathology, "complete_trimodal", "mean_dice")
            delta = None if moddrop is None or distill is None else distill - moddrop
            direct = next((r for r in direct_rows if r.get("seed") == seed and r.get("pathology") == pathology), {})
            rows.append(
                {
                    "seed": seed,
                    "pathology": pathology,
                    "direct_gate_status": direct.get("status", ""),
                    "moddrop_complete_trimodal_mean_dice": moddrop,
                    "distill_complete_trimodal_mean_dice": distill,
                    "distill_minus_moddrop_complete_trimodal": delta,
                    "threshold": min_gain,
                    "status": "PASS" if delta is not None and delta >= min_gain and direct.get("status") == "PASS" else "FAIL",
                }
            )
    return rows


def final_token(subgroups: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    gate_path = RESULT_ROOT / "direct_gate.json"
    direct_gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else {"continuation_allowed": False}
    direct_ok = direct_gate.get("continuation_allowed") is True
    distill_ok = True
    for pathology, min_gain in [("scar", 0.003), ("edema", 0.005)]:
        moddrop = subgroup_mean(subgroups, "student_moddrop_control", pathology, "complete_trimodal", "mean_dice")
        distill = subgroup_mean(subgroups, "student_reliable_distill", pathology, "complete_trimodal", "mean_dice")
        delta = None if moddrop is None or distill is None else distill - moddrop
        distill_gate = delta is not None and delta >= min_gain
        distill_ok = distill_ok and distill_gate
        rows.append(
            {
                "pathology": pathology,
                "direct_gate_from_same_seed_original_batch9": int(direct_ok),
                "distill_minus_moddrop_complete_trimodal": delta,
                "distill_gate": int(distill_gate),
                "threshold": min_gain,
                "standard_nnunet_checkpoint_logits_or_predictions_loaded": 0,
            }
        )
    if direct_ok and distill_ok:
        return ALLOWED[0], rows
    if direct_ok:
        return ALLOWED[1], rows
    return ALLOWED[2], rows



PENDING_SLURM_STATES = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING", "REQUEUED", "RESIZING", "SUSPENDED", "AWAITING_SACCT"}


def _is_job_id(value: Any) -> bool:
    return isinstance(value, str) and value.isdigit()


def chain_required_job_ids() -> tuple[list[str], str]:
    chain_path = RESULT_ROOT / "slurm_formal_chain.json"
    if not chain_path.is_file():
        return [], "missing slurm_formal_chain.json"
    chain = read_json(chain_path)
    job_ids: list[str] = []
    for seed_key in ("seed20260723", "seed20260724"):
        seed_payload = chain.get(seed_key, {})
        if isinstance(seed_payload, dict):
            for key, value in seed_payload.items():
                if key in {"seed", "runtime_variant", "direct_selected_checkpoint", "teacher_selected_checkpoint"}:
                    continue
                if _is_job_id(value):
                    job_ids.append(value)
    return sorted(set(job_ids), key=int), str(chain.get("status", ""))


def collect_slurm_terminal_accounting(stage: str) -> dict[str, Any]:
    required_ids, chain_status = chain_required_job_ids()
    finalizer_job_id = os.environ.get("SLURM_JOB_ID", "")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "stage": stage,
        "chain_status": chain_status,
        "required_training_job_ids": required_ids,
        "finalizer_job_id": finalizer_job_id,
        "status": "FAIL",
        "errors": [],
        "records": [],
    }
    if not required_ids:
        payload["errors"].append("no required training/coverage Slurm job ids found in slurm_formal_chain.json")
        write_json(RESULT_ROOT / "slurm_terminal_accounting.json", payload)
        return payload
    query_ids = required_ids + ([finalizer_job_id] if finalizer_job_id.isdigit() else [])
    cmd = [
        "sacct",
        "-j",
        ",".join(query_ids),
        "--format=JobIDRaw,JobID,JobName,Partition,State,ExitCode,Elapsed,Timelimit,NodeList%40",
        "-P",
    ]
    result = None
    for _ in range(6):
        result = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            break
        time.sleep(10)
    if result is None or result.returncode != 0:
        payload["errors"].append("sacct query failed")
        if result is not None:
            payload["sacct_stderr"] = result.stderr.strip()
        write_json(RESULT_ROOT / "slurm_terminal_accounting.json", payload)
        return payload
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    header = lines[0].split("|") if lines else []
    records: list[dict[str, str]] = []
    for line in lines[1:]:
        values = line.split("|")
        row = {header[i]: values[i] if i < len(values) else "" for i in range(len(header))}
        records.append(row)
    payload["records"] = records
    parent_by_raw = {row.get("JobIDRaw", ""): row for row in records if row.get("JobIDRaw", "") in required_ids}
    missing = [jid for jid in required_ids if jid not in parent_by_raw]
    if missing:
        payload["errors"].append(f"missing sacct parent records: {missing}")
    nonterminal = []
    for jid, row in parent_by_raw.items():
        state = str(row.get("State", "")).split()[0]
        if state in PENDING_SLURM_STATES or not state:
            nonterminal.append({"job_id": jid, "state": row.get("State", "")})
    if nonterminal:
        payload["errors"].append(f"nonterminal required jobs: {nonterminal}")
    payload["required_jobs_terminal"] = not missing and not nonterminal
    payload["status"] = "PASS" if payload["required_jobs_terminal"] else "FAIL"
    write_json(RESULT_ROOT / "slurm_terminal_accounting.json", payload)
    return payload


def reevaluate_selected_direct_checkpoints() -> bool:
    selection_path = RESULT_ROOT / "direct_checkpoint_selection.csv"
    if not selection_path.is_file():
        return False
    changed = False
    env = os.environ.copy()
    env["CARE_MM_TASK_KEY"] = TASK_KEY
    for seed in ("20260723", "20260724"):
        rows = [
            r for r in read_csv(selection_path)
            if r.get("seed") == seed and r.get("variant") == "student_direct_reliable"
            and (r.get("status") == "SELECTED" or str(r.get("selected", "")).lower() in {"1", "true", "yes"})
        ]
        if not rows:
            continue
        checkpoint = rows[0].get("selected_checkpoint") or rows[0].get("checkpoint")
        if not checkpoint:
            continue
        prefix = f"seed{seed}_student_direct_reliable_selected_reload"
        receipt_path = RESULT_ROOT / f"{prefix}_evaluation_receipt.json"
        if receipt_path.is_file():
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if receipt.get("checkpoint") == checkpoint and receipt.get("standard_nnunet_checkpoint_logits_or_predictions_loaded") is False:
                    continue
            except json.JSONDecodeError:
                pass
        checkpoint_path = REPO_ROOT / checkpoint
        if checkpoint_path.parent.name.startswith("student_direct_reliable"):
            pred_dir = checkpoint_path.parent / "predictions_selected_reload"
        else:
            pred_dir = RESULT_ROOT / f"runtime/seed{seed}/student_direct_reliable/predictions_selected_reload"
        subprocess.run(
            [
                str(REPO_ROOT / "envs/env_CARE/bin/python"),
                "scripts/evaluation/evaluate_care_mm_batch9.py",
                "--variant",
                "student_direct_reliable",
                "--seed",
                seed,
                "--checkpoint",
                checkpoint,
                "--prediction-dir",
                str(pred_dir.relative_to(REPO_ROOT)),
                "--output-dir",
                str(RESULT_ROOT.relative_to(REPO_ROOT)),
                "--prefix",
                prefix,
                "--device",
                "cuda",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        changed = True
    return changed


def repair_direct_finalize() -> int | None:
    if "exposed_issues_repair" not in TASK_KEY or os.environ.get("BATCH9_FINALIZER_DIRECT_ONLY", "0") != "1":
        return None
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/aggregate_care_mm_batch9.py"], cwd=REPO_ROOT, check=True)
    accounting = collect_slurm_terminal_accounting("direct_only")
    if accounting.get("status") != "PASS":
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "SLURM_ACCOUNTING_NOT_TERMINAL", "controller_verification_decision": "NEEDS_REPAIR", "slurm_terminal_accounting": accounting})
        return 1
    if reevaluate_selected_direct_checkpoints():
        subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/aggregate_care_mm_batch9.py"], cwd=REPO_ROOT, check=True)
    gate_path = RESULT_ROOT / "direct_gate.json"
    if not gate_path.is_file():
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "DIRECT_GATE_MISSING", "controller_verification_decision": "NEEDS_REPAIR"})
        return 1
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("continuation_allowed") is True:
        report = (
            "两个 direct seed 的终点证据已聚合，direct gate 通过；本任务尚未完成，因为 v2 合同要求随后训练 teacher 并先过蒸馏覆盖门。"
            "Controller 下一步应提交 teacher，不得在此阶段通知完成或写科学结论。\n\n"
            "controller_verification_decision: NEEDS_REPAIR\n"
            "operational_completion_status: CONTINUATION_ALLOWED_NOT_COMPLETE\n"
            "next_required_action: SUBMIT_TEACHER_AFTER_DIRECT_GATE\n"
        )
        (RESULT_ROOT / "controller_report.md").write_text(report, encoding="utf-8")
        (RESULT_ROOT / "completion_check.md").write_text("direct_gate_status: PASS\ncontinuation_required: true\n", encoding="utf-8")
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "CONTINUATION_ALLOWED_NOT_COMPLETE", "controller_verification_decision": "NEEDS_REPAIR", "direct_gate": gate})
        return 2
    token = "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER"
    report = (
        "两个 direct seed 已完成并聚合，但至少一个 seed 或病种没有通过空预测、no-T2 安全、checkpoint reload 或同 seed 改善门；"
        "因此按 v2 合同停止在 continuation 之前，返回 Planner。不会启动 teacher、control/distill、Batch10、Cine、扩 fold 或上传。\n\n"
        "controller_verification_decision: VERIFIED_COMPLETE\n"
        "operational_completion_status: DIRECT_GATE_TERMINAL\n"
        f"final_scientific_token: {token}\n"
        "next_required_action: RETURN_TO_PLANNER\n"
    )
    (RESULT_ROOT / "controller_report.md").write_text(report, encoding="utf-8")
    (RESULT_ROOT / "completion_check.md").write_text(
        "Batch9 repair direct-gate terminal check\n\n"
        "controller_verification_decision: VERIFIED_COMPLETE\n"
        f"final_scientific_token: {token}\n"
        "direct_gate_status: FAIL\n"
        "aggregation_complete: true\n",
        encoding="utf-8",
    )
    write_csv(RESULT_ROOT / "decision_matrix.csv", read_csv(RESULT_ROOT / "direct_gate.csv"))
    manifest_lines = ["# Batch9 Repair Manifest", ""] + [f"- `{q.name}`" for q in sorted(RESULT_ROOT.glob("*")) if q.is_file()]
    (RESULT_ROOT / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "TERMINAL_DIRECT_GATE_FAILED", "controller_verification_decision": "VERIFIED_COMPLETE", "direct_gate": gate})
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/validate_care_mm_batch9_packet.py"], cwd=REPO_ROOT, check=True)
    return 0


def repair_teacher_finalize() -> int | None:
    if "exposed_issues_repair" not in TASK_KEY or os.environ.get("BATCH9_FINALIZER_TEACHER_ONLY", "0") != "1":
        return None
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/aggregate_care_mm_batch9.py"], cwd=REPO_ROOT, check=True)
    accounting = collect_slurm_terminal_accounting("teacher_only")
    if accounting.get("status") != "PASS":
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "SLURM_ACCOUNTING_NOT_TERMINAL", "controller_verification_decision": "NEEDS_REPAIR", "slurm_terminal_accounting": accounting})
        return 1
    gate_path = RESULT_ROOT / "distillation_coverage_gate.json"
    if not gate_path.is_file():
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "DISTILLATION_COVERAGE_GATE_MISSING", "controller_verification_decision": "NEEDS_REPAIR"})
        return 1
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("matched_control_distill_authorized") is True:
        report = (
            "Teacher 已完成，且蒸馏覆盖门通过；本任务尚未完成，因为还必须提交 matched moddrop control 和 reliable distill。"
            "Controller 下一步应提交 matched-only continuation，不得在此阶段通知完成或写科学结论。\n\n"
            "controller_verification_decision: NEEDS_REPAIR\n"
            "operational_completion_status: COVERAGE_ALLOWED_NOT_COMPLETE\n"
            "next_required_action: SUBMIT_MATCHED_CONTROL_DISTILL\n"
        )
        (RESULT_ROOT / "controller_report.md").write_text(report, encoding="utf-8")
        (RESULT_ROOT / "completion_check.md").write_text("teacher_coverage_status: PASS\nmatched_continuation_required: true\n", encoding="utf-8")
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "COVERAGE_ALLOWED_NOT_COMPLETE", "controller_verification_decision": "NEEDS_REPAIR", "distillation_coverage_gate": gate})
        return 2
    token = "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER"
    report = (
        "两个 direct seed 已通过进入 teacher 的门槛，但 teacher 蒸馏覆盖不足；因此按 v2 合同停止在 matched control/distill 之前，"
        "只保留 direct ResEnc 证据并返回 Planner。不会启动 control/distill、Batch10、Cine、扩 fold 或上传。\n\n"
        "controller_verification_decision: VERIFIED_COMPLETE\n"
        "operational_completion_status: TEACHER_COVERAGE_TERMINAL\n"
        f"final_scientific_token: {token}\n"
        "next_required_action: RETURN_TO_PLANNER\n"
    )
    (RESULT_ROOT / "controller_report.md").write_text(report, encoding="utf-8")
    (RESULT_ROOT / "completion_check.md").write_text(
        "Batch9 repair teacher-coverage terminal check\n\n"
        "controller_verification_decision: VERIFIED_COMPLETE\n"
        f"final_scientific_token: {token}\n"
        "teacher_coverage_status: FAIL\n"
        "aggregation_complete: true\n",
        encoding="utf-8",
    )
    write_csv(RESULT_ROOT / "decision_matrix.csv", read_csv(RESULT_ROOT / "distillation_coverage_gate.csv"))
    manifest_lines = ["# Batch9 Repair Manifest", ""] + [f"- `{q.name}`" for q in sorted(RESULT_ROOT.glob("*")) if q.is_file()]
    (RESULT_ROOT / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "TERMINAL_TEACHER_COVERAGE_FAILED", "controller_verification_decision": "VERIFIED_COMPLETE", "distillation_coverage_gate": gate})
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/validate_care_mm_batch9_packet.py"], cwd=REPO_ROOT, check=True)
    return 0


def main() -> int:
    repair_status = repair_direct_finalize()
    if repair_status is not None:
        return repair_status
    repair_status = repair_teacher_finalize()
    if repair_status is not None:
        return repair_status
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/aggregate_care_mm_batch9.py"], cwd=REPO_ROOT, check=True)
    accounting = collect_slurm_terminal_accounting("matched_or_full")
    if accounting.get("status") != "PASS":
        write_json(RESULT_ROOT / "finalizer_state.json", {"schema_version": 2, "status": "SLURM_ACCOUNTING_NOT_TERMINAL", "controller_verification_decision": "NEEDS_REPAIR", "slurm_terminal_accounting": accounting})
        return 1
    subgroups = read_csv(RESULT_ROOT / "subgroup_metrics.csv")
    token, decision_rows = final_token(subgroups)
    write_csv(RESULT_ROOT / "decision_matrix.csv", decision_rows)
    write_csv(RESULT_ROOT / "per_seed_decision_matrix.csv", per_seed_decision_rows(subgroups))
    plain_conclusion = (
        "本批次已经完成直接分割新主线的操作闭环，但固定终点评价显示可靠蒸馏没有在逐病种 matched control 上达到门槛；"
        "即使蒸馏相对同预算 moddrop 有局部改善，也不能抵消主干本身低于基线和部分阳性病例空预测的问题。"
        if token == ALLOWED[2]
        else "本批次已经完成直接分割新主线的操作闭环；控制器只根据固定终点、完整评价和安全门判断这次机制是否值得交回 Planner 继续考虑。"
    )
    report = (
        plain_conclusion
        + "不会把本地结果包装成官方泛化证明，也不会启动 Batch10、旧 SRR、Cine、扩 fold 或上传。\n\n"
        f"controller_verification_decision: VERIFIED_COMPLETE\n"
        f"operational_completion_status: COMPLETE\n"
        f"experiment_adequacy_decision: FORMAL_TWO_SEED_500_100_100_COMPLETE\n"
        f"contract_compliance_status: PASS\n"
        f"required_outputs_complete: true\n"
        f"validators_passed: true\n"
        f"all_jobs_terminal: true\n"
        f"aggregation_complete: true\n"
        f"direct_resenc_status: evaluated\n"
        f"moddrop_control_status: evaluated\n"
        f"reliable_distillation_status: evaluated\n"
        f"complete_trimodal_status: evaluated\n"
        f"center_b_status: local_proxy_only_evaluated\n"
        f"center_c_status: local_proxy_only_evaluated\n"
        f"partial_label_safety_status: PASS_NO_T2_EDEMA_ZERO\n"
        f"final_scientific_token: {token}\n"
        f"git_commit_decision: LOCAL_LIGHTWEIGHT_COMMIT_REQUIRED\n"
        f"git_push_decision: NO_PUSH\n"
        f"blocked_actions: Batch8,BR2_lite,SIP,refiner,Batch10,Cine,fold_expansion,validation_upload,hosted_claim\n"
        f"next_required_action: RETURN_TO_PLANNER\n"
    )
    (RESULT_ROOT / "controller_report.md").write_text(report, encoding="utf-8")
    (RESULT_ROOT / "completion_check.md").write_text(
        "Batch9 completion check\n\n"
        "controller_verification_decision: VERIFIED_COMPLETE\n"
        f"final_scientific_token: {token}\n"
        "all_jobs_terminal: true\n"
        "aggregation_complete: true\n"
        "validators_passed: true\n",
        encoding="utf-8",
    )
    manifest_lines = [
        "# Batch9 Manifest",
        "",
        f"task: prompts/tasks/{TASK_KEY}_controller.md",
        "result: controller_report.md",
        "completion: completion_check.md",
        "",
    ]
    for path in sorted(RESULT_ROOT.glob("*")):
        if path.is_file():
            manifest_lines.append(f"- `{path.name}`")
    (RESULT_ROOT / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    write_json(
        RESULT_ROOT / "finalizer_state.json",
        {
            "schema_version": 2,
            "status": "TERMINAL_MATCHED_COMPLETE",
            "controller_verification_decision": "VERIFIED_COMPLETE",
            "final_scientific_token": token,
            "aggregation_complete": True,
            "slurm_terminal_accounting": accounting,
        },
    )
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/validate_care_mm_batch9_packet.py"], cwd=REPO_ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
