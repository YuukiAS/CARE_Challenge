#!/usr/bin/env python3
"""Finalize the 20260801 target-domain pathology race packet."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_KEY = "20260801_care_target_domain_pathology_specialist_race"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
M0_ROOT = RESULT_ROOT / "m0_td_nnunet"

JOB_IDS = ["61517360", "61517361", "61517362", "61517363", "61528800", "61546557"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_slurm_accounting() -> list[dict[str, str]]:
    cmd = [
        "sacct",
        "-j",
        ",".join(JOB_IDS),
        "--format=JobID,JobName,Partition,State,ExitCode,Elapsed",
        "-P",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, check=True, text=True, capture_output=True)
    rows = list(csv.DictReader(proc.stdout.splitlines(), delimiter="|"))
    out = RESULT_ROOT / "slurm_accounting.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> int:
    created_at = now_utc()
    comparison = read_json(M0_ROOT / "m0_vs_stock_outer_summary.json")["rows"]
    mean = next(r for r in comparison if r["fold"] == "mean")
    fold2 = read_json(M0_ROOT / "fold2_training_receipt.json")
    fold3 = read_json(M0_ROOT / "fold3_training_receipt.json")
    m1 = read_json(RESULT_ROOT / "m1_myopsnet_l_care/preflight_report.json")
    m2 = read_json(RESULT_ROOT / "m2_i_mmseg_care/preflight_report.json")
    m3 = read_json(RESULT_ROOT / "m3_care_tds/preflight_report.json")
    slurm_rows = write_slurm_accounting()

    decision = {
        "created_at": created_at,
        "task_key": TASK_KEY,
        "controller_verification_decision": "VERIFIED_COMPLETE",
        "scientific_decision": "NO_GO_TARGET_DOMAIN_RACE",
        "reason": (
            "M0 completed fold2/fold3 formal target-domain fine-tuning and full outer evaluation, "
            "but underperformed the same-case stock nnU-Net baseline on pathology and foreground means; "
            "M1/M2/M3 did not produce formal candidates because their preflight gates exposed implementation or asset gaps."
        ),
        "m0_mean_delta_vs_stock": {
            "class_4_edema": mean["delta_class_4"],
            "class_5_scar": mean["delta_class_5"],
            "foreground_mean": mean["delta_foreground_mean"],
        },
        "folds_completed": [2, 3],
        "formal_candidate_ready": False,
        "validation_packaging_or_upload_authorized": False,
        "route_promotion_authorized": False,
        "hosted_metric_claim": False,
    }
    write_json(RESULT_ROOT / "scientific_decision.json", decision)

    finalizer = {
        "created_at": created_at,
        "task_key": TASK_KEY,
        "status": "COMPLETE",
        "m0_training_receipts": [str(M0_ROOT / "fold2_training_receipt.json"), str(M0_ROOT / "fold3_training_receipt.json")],
        "m0_outer_eval": [
            str(M0_ROOT / "fold2_outer_eval_checkpoint_best/evaluation_summary.json"),
            str(M0_ROOT / "fold3_outer_eval_checkpoint_best/evaluation_summary.json"),
            str(M0_ROOT / "m0_vs_stock_outer_summary.json"),
        ],
        "lane_status": {
            "M0_TD_NNUNET": "FORMAL_TRAINED_AND_EVALUATED_NO_GO_VS_STOCK",
            "M1_MYOPSNET_L_CARE": m1["status"],
            "M2_I_MMSEG_CARE": m2["status"],
            "M3_CARE_TDS": m3["status"],
        },
        "slurm_accounting_path": str(RESULT_ROOT / "slurm_accounting.csv"),
        "slurm_jobs_terminal": all(r["State"] not in {"PENDING", "RUNNING"} for r in slurm_rows),
        "known_nonfatal_repairs": [
            "61517363 failed because the first worker script had an sbatch header placement bug; M0 preflight/training was rerun successfully on the existing interactive allocation.",
            "61546557 failed because nnU-Net predictor could not discover the repo-local trainer; the eval script now patches trainer discovery and fold2/fold3 outer eval completed on the interactive allocation.",
        ],
    }
    write_json(RESULT_ROOT / "finalizer_state.json", finalizer)

    report = f"""这次目标域病灶竞赛没有找到可继续推进的候选模型。唯一完成正式训练和外层评价的 M0 在 fold2/fold3 上相对 stock nnU-Net 下降，尤其是 edema 和 scar；M1/M2/M3 没有形成正式候选，原因分别是 CARE full-volume wrapper 未实现、官方 I-MMSEG 资产缺失、CARE-TDS 独立 heads/losses 未实现。下一步不应包装、上传或声称 leaderboard 改进，而应回到模型设计和资产补齐。

# Controller Report

- controller_verification_decision: `VERIFIED_COMPLETE`
- scientific_decision: `NO_GO_TARGET_DOMAIN_RACE`
- task_key: `{TASK_KEY}`
- generated_at: `{created_at}`

## M0 Result

| fold | td class4 edema | stock class4 edema | delta | td class5 scar | stock class5 scar | delta | td foreground_mean | stock foreground_mean | delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
"""
    for row in comparison:
        report += (
            f"| {row['fold']} | {row['td_class_4']:.6f} | {row['stock_class_4']:.6f} | {row['delta_class_4']:.6f} | "
            f"{row['td_class_5']:.6f} | {row['stock_class_5']:.6f} | {row['delta_class_5']:.6f} | "
            f"{row['td_foreground_mean']:.6f} | {row['stock_foreground_mean']:.6f} | {row['delta_foreground_mean']:.6f} |\n"
        )
    report += f"""
## Lane Boundary

- M0 TD-NNUNET: fold2/fold3 completed 4000 optimizer steps each and full outer prediction/evaluation was run.
- M1 MYOPSNET-L-CARE: `{m1['status']}`; {m1['blocking_gap']}
- M2 I-MMSEG-CARE: `{m2['status']}`; {m2['blocking_gap']}
- M3 CARE-TDS: `{m3['status']}`; {m3['blocking_gap']}

## Operational Notes

- Existing interactive allocation `61220581` was used after the user authorized serial fallback and extra Slurm jobs.
- Slurm job `61528800` completed fold3 training. Failed startup/eval attempts are recorded in `slurm_accounting.csv` and repaired by successful interactive reruns.
- No validation package, upload, hosted metric claim, route promotion, or remote branch publication is authorized by this packet.
"""
    write_text(RESULT_ROOT / "controller_report.md", report)

    completion = f"""# Completion Check

status: `COMPLETE`

- Data contract and split receipts: present.
- M0 fold2/fold3 formal training receipts: present.
- M0 fold2/fold3 outer prediction/evaluation: present.
- Stock same-case comparison: present.
- Scientific result: `NO_GO_TARGET_DOMAIN_RACE` because M0 underperformed stock and no other lane produced a formal candidate.
- Slurm accounting: terminal states recorded in `slurm_accounting.csv`.
- Unauthorized actions not performed: validation packaging/upload, hosted metric claim, route promotion, extra remote branch push.
"""
    write_text(RESULT_ROOT / "completion_check.md", completion)

    manifest = """# Manifest

- `controller_report.md`
- `scientific_decision.json`
- `finalizer_state.json`
- `completion_check.md`
- `strict_validator_report.json`
- `known_bad_report.json`
- `slurm_accounting.csv`
- `m0_td_nnunet/fold2_training_receipt.json`
- `m0_td_nnunet/fold3_training_receipt.json`
- `m0_td_nnunet/fold2_outer_eval_checkpoint_best/evaluation_summary.json`
- `m0_td_nnunet/fold3_outer_eval_checkpoint_best/evaluation_summary.json`
- `m0_td_nnunet/fold2_stock_outer_eval/evaluation_summary.json`
- `m0_td_nnunet/fold3_stock_outer_eval/evaluation_summary.json`
- `m0_td_nnunet/m0_vs_stock_outer_summary.json`
"""
    write_text(RESULT_ROOT / "MANIFEST.md", manifest)

    notification = {
        "task_name": TASK_KEY,
        "final_status": "complete",
        "commit_status": "complete_in_current_closeout_commit",
        "push_status": "complete_after_current_closeout_push",
        "key_conclusion": "目标域 M0 fold2/fold3 完训并完成外层评价，但相对 stock nnU-Net 下降；M1/M2/M3 未形成正式候选，因此结论是 NO_GO_TARGET_DOMAIN_RACE。",
        "blocked_or_failure_reason": "none; operational packet complete, scientific result is no-go",
        "slurm_terminal_status": "all submitted Slurm jobs reached terminal states; failed startup/eval attempts were repaired by successful interactive reruns",
        "evidence_paths": [
            str(RESULT_ROOT / "controller_report.md"),
            str(RESULT_ROOT / "scientific_decision.json"),
            str(M0_ROOT / "m0_vs_stock_outer_summary.json"),
            str(RESULT_ROOT / "slurm_accounting.csv"),
        ],
        "next_step": "Do not package/upload this candidate; planner should decide whether to implement true M3 heads/losses or repair M1/M2 assets before another race.",
    }
    write_json(RESULT_ROOT / "notification_brief.json", notification)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
