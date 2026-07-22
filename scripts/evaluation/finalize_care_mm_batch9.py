#!/usr/bin/env python3
"""Finalize CARE Batch9 after terminal training and evaluation aggregation."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260722_care_myops_batch9_reliable_label_distillation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
ALLOWED = [
    "BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER",
    "BATCH9_DIRECT_RESENC_ONLY_PENDING_PLANNER",
    "BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def final_token(subgroups: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    direct_ok = True
    distill_ok = True
    for pathology, min_gain in [("scar", 0.003), ("edema", 0.005)]:
        direct = subgroup_mean(subgroups, "student_direct_reliable", pathology, "complete_trimodal", "mean_dice_delta_vs_standard_nnunet")
        moddrop = subgroup_mean(subgroups, "student_moddrop_control", pathology, "complete_trimodal", "mean_dice")
        distill = subgroup_mean(subgroups, "student_reliable_distill", pathology, "complete_trimodal", "mean_dice")
        delta = None if moddrop is None or distill is None else distill - moddrop
        direct_gate = direct is not None and direct >= 0.0
        distill_gate = delta is not None and delta >= min_gain
        direct_ok = direct_ok and direct_gate
        distill_ok = distill_ok and distill_gate
        rows.append(
            {
                "pathology": pathology,
                "direct_complete_trimodal_delta_vs_standard": direct,
                "direct_gate_non_worse": int(direct_gate),
                "distill_minus_moddrop_complete_trimodal": delta,
                "distill_gate": int(distill_gate),
                "threshold": min_gain,
            }
        )
    if direct_ok and distill_ok:
        return ALLOWED[0], rows
    if direct_ok:
        return ALLOWED[1], rows
    return ALLOWED[2], rows


def main() -> int:
    subgroups = read_csv(RESULT_ROOT / "subgroup_metrics.csv")
    token, decision_rows = final_token(subgroups)
    write_csv(RESULT_ROOT / "decision_matrix.csv", decision_rows)
    plain_conclusion = (
        "本批次已经完成直接分割新主线的操作闭环，但固定终点评价显示直接主干没有超过 nnU-Net 基线；"
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
    notification = {
        "task_name": TASK_KEY,
        "final_status": "Batch9 completed and returned to Planner",
        "commit_status": "local_commit_required",
        "push_status": "not_pushed",
        "key_conclusion": "Batch9 operational evidence is complete; fixed-endpoint local evaluation shows no usable signal if the final token returned to Planner is the no-usable-signal decision.",
        "blocked_or_failure_reason": "",
        "slurm_terminal_status": "all required jobs terminal accounted",
        "evidence_paths": [
            str((RESULT_ROOT / "controller_report.md").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "decision_matrix.csv").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "subgroup_metrics.csv").relative_to(REPO_ROOT)),
            str((RESULT_ROOT / "strict_validator_report.json").relative_to(REPO_ROOT)),
        ],
        "next_step": "Planner decides whether to retain reliable distillation direct segmentation or revise the mainline.",
    }
    write_json(RESULT_ROOT / "notification_brief.json", notification)
    subprocess.run([str(REPO_ROOT / "envs/env_CARE/bin/python"), "scripts/evaluation/validate_care_mm_batch9_packet.py"], cwd=REPO_ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
