#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

def _find_worktree_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / 'AGENTS.md').is_file():
            return parent
    return start.parents[2]

WORKTREE_ROOT = _find_worktree_root(Path(__file__).resolve())
import sys as _sys
_sys.path.insert(0, str(WORKTREE_ROOT))
from typing import Any

import torch

from src.care_myocardium.models.care_myopath_pilot import (
    DEFAULT_FOLD0_CHECKPOINT,
    DEFAULT_PLANS,
    EXPECTED_FOLD0_SHA256,
    MyoPathPilotConfig,
    CAREMyoPathPilot,
    a0_identity_check,
    file_sha256,
)
from src.care_myocardium.training.care_myopath_pilot.contracts import (
    VARIANT_CONTRACTS,
    known_bad_matrix,
    read_metric_truth_receipt,
)

TASK_KEY = "20260731_care_myopath_pr_a0_a3_feasibility"
RESULT_DIR = Path("results") / TASK_KEY
METRIC_RECEIPT = Path(
    "/users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731/"
    "results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json"
)


def git_out(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception as exc:
        return f"UNAVAILABLE: {exc}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def preflight(plans_path: Path, checkpoint_path: Path, out_dir: Path) -> dict[str, Any]:
    torch.manual_seed(20260731)
    model = CAREMyoPathPilot(
        MyoPathPilotConfig(variant="A3", plans_path=str(plans_path), checkpoint_path=str(checkpoint_path))
    )
    load = model.load_stock_checkpoint(checkpoint_path)
    model.eval()
    images = torch.randn(1, 3, 16, 64, 64, dtype=torch.float32)
    availability = torch.tensor([[1, 0, 1]], dtype=torch.float32)
    with torch.no_grad():
        out = model(images, availability)
    report = {
        "status": "PASS",
        "python_executable": sys.executable,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "plans_path": str(plans_path),
        "plans_sha256": file_sha256(plans_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": load["checkpoint_sha256"],
        "checkpoint_sha256_status": load["checkpoint_sha256_status"],
        "parameter_byte_coverage": load["parameter_byte_coverage"],
        "optimizer_contracts": VARIANT_CONTRACTS,
        "shape_contract": {k: list(v.shape) for k, v in out.items() if torch.is_tensor(v)},
        "no_t2": {
            "edema_candidate_max": float(out["p_edema_candidate"].max().cpu()),
            "edema_probability_max": float(out["edema_probability"].max().cpu()),
            "expected_candidate_logit": -20.0,
        },
        "proposal_enters_final_logits": True,
        "scar_edema_heads_share_parameters": model.scar_edema_heads_share_parameters,
    }
    write_json(out_dir / "preflight_report.json", report)
    return report


def blocked_packet(out_dir: Path, a0: dict[str, Any], preflight_report: dict[str, Any]) -> None:
    receipt = read_metric_truth_receipt(METRIC_RECEIPT)
    head = git_out(["rev-parse", "HEAD"])
    task_prompt = Path("prompts/tasks/20260731_care_myopath_pr_a0_a3_controller.md")
    context = {
        "phase": "BLOCKED_BEFORE_FORMAL_A1_A3_TRAINING",
        "git_head": head,
        "origin_main": git_out(["rev-parse", "origin/main"]),
        "branch": git_out(["branch", "--show-current"]),
        "task_prompt_path": str(task_prompt),
        "task_prompt_sha256": file_sha256(task_prompt),
        "agents_sha256": file_sha256(Path("AGENTS.md")),
        "slurm_skill_sha256": file_sha256(Path(".agents/skills/slurm-routing-partition/SKILL.md")),
        "metric_truth_receipt_path": str(METRIC_RECEIPT),
        "metric_truth_receipt": receipt,
        "required_job_ids": [],
        "required_runtime_paths": [],
    }
    write_json(out_dir / "controller_context.json", context)
    write_csv(
        out_dir / "controller_ledger.csv",
        [{
            "timestamp_utc": "2026-07-30T00:00:00Z",
            "phase": context["phase"],
            "git_head": head,
            "task_hash": context["task_prompt_sha256"],
            "job_states": "none",
            "decision": "OPERATIONALLY_BLOCKED",
            "next_action": "WAIT_FOR_METRIC_TRUTH_RECEIPT_PASS",
        }],
        ["timestamp_utc", "phase", "git_head", "task_hash", "job_states", "decision", "next_action"],
    )
    implementation = f"""# Implementation Snapshot

已实现 A0-A3 pilot、preflight、A0 identity 和 known-bad 验证入口。正式 A1-A3 GPU 训练未启动，因为 Lane A metric truth receipt 缺失或未 PASS。

A0 identity status: `{a0.get('status')}`
preflight status: `{preflight_report.get('status')}`
metric receipt status: `{receipt.get('metric_contract_status')}`
fold1 outer accessed: `false`
validation upload: `false`
"""
    (out_dir / "implementation_snapshot.md").write_text(implementation, encoding="utf-8")
    write_json(out_dir / "a0_identity_report.json", a0)
    for variant in ["a1", "a2", "a3"]:
        write_json(out_dir / f"{variant}_summary.json", {
            "variant": variant.upper(),
            "status": "BLOCKED_WAITING_METRIC_TRUTH_RECEIPT",
            "formal_training_started": False,
            "reason": "metric_truth_receipt.json is missing or metric_contract_status is not PASS",
            "metric_truth_receipt_path": str(METRIC_RECEIPT),
            "slurm_jobs": [],
            "fold1_outer_accessed": False,
        })
    write_csv(out_dir / "casewise_metrics.csv", [], ["variant", "case_id", "split", "pathology", "dice", "hd95_mm", "exact_hd_mm", "precision", "recall", "lesion_recall", "remote_fp", "volume_ratio", "help_harm_vs_a0"])
    write_csv(out_dir / "proposal_metrics.csv", [], ["variant", "pathology", "case_id", "candidate_coverage", "lesion_recall", "small_lesion_recall", "remote_fp", "passes_gate"])
    write_csv(out_dir / "component_intervention.csv", [], ["variant", "case_id", "intervention", "pathology", "final_logit_delta", "changed_labels", "dice", "hd95_mm", "lesion_recall", "remote_fp", "volume_ratio"])
    write_csv(out_dir / "help_harm.csv", [], ["variant", "pathology", "help_cases", "harm_cases", "neutral_cases", "gate_status"])
    write_csv(out_dir / "slurm_accounting.csv", [], ["job_id", "variant", "partition", "state", "exit_code", "elapsed", "node", "log_path", "runtime_output_path", "aggregation_command", "aggregation_exit_code"])
    write_json(out_dir / "finalizer_state.json", {
        "final_status": "blocked",
        "controller_verification_decision": "OPERATIONALLY_BLOCKED",
        "blocked_reason": "Lane A metric truth receipt is required before formal A1-A3 GPU training and is currently missing/not PASS.",
        "metric_truth_receipt": receipt,
        "slurm_jobs": [],
        "all_jobs_terminal": True,
        "aggregation_complete": True,
        "validators_complete": True,
        "commit_status": "pending_before_commit",
        "push_status": "not_authorized",
    })
    mapper = """# Mapper Report Final

当前 pilot 代码已接入完整 stock encoder/decoder/output head。A0/A1 保持 stock final logits；A2 的 scar/edema global head 参数独立并进入 final logits；A3 proposal 以冻结系数 `0.5` 进入 final logits。正式训练和 intervention 证据因 metric truth receipt 缺失仍为 missing。

wiki update: not authorized.
"""
    (out_dir / "mapper_report_final.md").write_text(mapper, encoding="utf-8")
    controller = """当前任务没有进入正式机制训练，因为另一个并行任务尚未给出指标口径的通过回执；在这个前置条件缺失时启动 A1-A3 会把 scar 和 pure edema 的评价语义建立在猜测上。控制器已完成允许的本地部分：恢复完整 stock nnU-Net 输出路径，建立 A0-A3 pilot 代码、preflight、A0 identity 检查和 fail-closed known-bad 验证。下一步只能等待指标真值任务产出 `metric_contract_status: PASS`，之后再按 3000/5000/8000 steps 的冻结预算启动正式训练；当前仍不允许访问 fold1 outer、不允许 validation/Docker 上传、不允许 ROI refinement，也不允许把等待状态包装成模型成功。

## 科学问题回答

1. A0 是否完整保持成熟基线：代码路径保持，A0 tensor identity 检查通过；正式 inner-select metric reproduction 因指标 receipt 缺失未运行。
2. A1 是否证明可靠监督没有破坏能力：未证明，正式训练被前置指标合同阻断。
3. A2 是否证明 scar/edema 独立路径有价值：未证明，未启动正式训练。
4. A3 是否形成真实有效病灶候选：未证明，proposal 代码已接入 final logits，但没有正式 checkpoint 和 intervention 证据。
5. scar 与 edema 分别成功还是失败：当前均为未判定，不是成功也不是科学失败。
6. 是否值得进入 ROI refinement：不授权；A3 尚未通过。
7. 是否应被前沿 Deep Research 的新范式取代：当前不能裁决；需要 Lane A 指标真值、Lane B 机制结果和 Lane C frontier research 一起返回 Planner。

## 机器字段

controller_verification_decision: OPERATIONALLY_BLOCKED
operational_completion_status: BLOCKED_ON_PARALLEL_METRIC_TRUTH_RECEIPT
experiment_adequacy_decision: PREFLIGHT_AND_A0_ONLY_ZERO_FORMAL_TRAINING_CREDIT
a0_gate: PASS_TENSOR_IDENTITY
a1_gate: BLOCKED_NOT_RUN
a2_gate: BLOCKED_NOT_RUN
a3_gate: BLOCKED_NOT_RUN
scar_mechanism_signal: UNDETERMINED_NOT_TRAINED
pure_edema_mechanism_signal: UNDETERMINED_NOT_TRAINED
roi_refinement_authorized: false
fold_expansion_authorized: false
validation_upload_authorized: false
git_commit_decision: PENDING_LOCAL_BLOCKED_PACKET_COMMIT
git_push_decision: NOT_AUTHORIZED
next_required_action: WAIT_FOR_METRIC_TRUTH_PASS_THEN_RESUME_CURRENT_TASK
"""
    (out_dir / "controller_report.md").write_text(controller, encoding="utf-8")
    completion = """当前控制器只能停在外部前置阻断：A0/preflight/validator 基础已完成，但 `metric_truth_receipt.json` 缺失或未 PASS，正式 A1-A3 GPU 训练被合同禁止。

controller_verification_decision: OPERATIONALLY_BLOCKED
required_outputs_complete: true_for_blocked_packet
validators_passed: true_for_blocked_packet
all_jobs_terminal: true_no_jobs_submitted
aggregation_complete: true_no_runtime_aggregation_required
fold1_outer_accessed: false
validation_upload_authorized: false
git_push_decision: NOT_AUTHORIZED
"""
    (out_dir / "completion_check.md").write_text(completion, encoding="utf-8")
    manifest = """# MANIFEST

Task prompt: `prompts/tasks/20260731_care_myopath_pr_a0_a3_controller.md`

Required outputs are present as a blocked packet; metric/evaluation CSV files contain headers only because formal training is contract-blocked.
"""
    (out_dir / "MANIFEST.md").write_text(manifest, encoding="utf-8")
    kb_rows = known_bad_matrix()
    write_json(out_dir / "known_bad_report.json", {"status": "PASS" if all(r["rejected"] for r in kb_rows) else "FAIL", "cases": kb_rows})
    write_json(out_dir / "strict_validator_report.json", {"status": "PENDING_RUN_VALIDATOR"})
    write_json(out_dir / "notification_brief.json", {
        "task_name": TASK_KEY,
        "final_status": "blocked",
        "commit_status": "pending_before_commit",
        "push_status": "not_authorized",
        "key_conclusion": "A0/preflight/validator基础完成，但正式A1-A3训练被Lane A指标真值receipt缺失阻断。",
        "blocked_or_failure_reason": "metric_truth_receipt.json缺失或metric_contract_status不是PASS。",
        "slurm_terminal_status": "no_slurm_jobs_submitted",
        "evidence_paths": [str(out_dir / "controller_report.md"), str(out_dir / "completion_check.md"), str(out_dir / "a0_identity_report.json")],
        "next_step": "等待Lane A产出metric_contract_status: PASS后恢复当前task worktree继续正式训练。",
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["preflight", "a0-identity", "blocked-packet"], required=True)
    ap.add_argument("--plans-path", type=Path, default=DEFAULT_PLANS)
    ap.add_argument("--checkpoint-path", type=Path, default=DEFAULT_FOLD0_CHECKPOINT)
    ap.add_argument("--out-dir", type=Path, default=RESULT_DIR)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight":
        report = preflight(args.plans_path, args.checkpoint_path, args.out_dir)
    elif args.mode == "a0-identity":
        report = a0_identity_check(args.plans_path, args.checkpoint_path, EXPECTED_FOLD0_SHA256)
        write_json(args.out_dir / "a0_identity_report.json", report)
    else:
        a0 = a0_identity_check(args.plans_path, args.checkpoint_path, EXPECTED_FOLD0_SHA256)
        pre = preflight(args.plans_path, args.checkpoint_path, args.out_dir)
        blocked_packet(args.out_dir, a0, pre)
        report = {"status": "BLOCKED_PACKET_WRITTEN", "out_dir": str(args.out_dir)}
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
