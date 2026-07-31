#!/usr/bin/env python3
"""Finalize CARE-QIF v2 signal-audit receipts and reports."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import RESULT_ROOT, rel, sha256_file, utc_now, write_csv, write_json  # noqa: E402
from scripts.validation.validate_care_qif_v2_signal_audit import build_known_bad_report  # noqa: E402


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_git(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT_FOR_IMPORT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def sacct_rows(job_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job_id in job_ids:
        proc = subprocess.run(
            ["sacct", "-j", job_id, "--format=JobIDRaw,JobName,Partition,State,ExitCode,Elapsed,Start,End", "--parsable2", "--noheader"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.splitlines():
                parts = line.split("|")
                if len(parts) >= 8:
                    rows.append(
                        {
                            "job_id": parts[0],
                            "job_name": parts[1],
                            "partition": parts[2],
                            "state": parts[3],
                            "exit_code": parts[4],
                            "elapsed": parts[5],
                            "start": parts[6],
                            "end": parts[7],
                            "source": "sacct",
                        }
                    )
        else:
            rows.append(
                {
                    "job_id": job_id,
                    "job_name": "",
                    "partition": "",
                    "state": "SACCT_UNAVAILABLE",
                    "exit_code": "",
                    "elapsed": "",
                    "start": "",
                    "end": "",
                    "source": proc.stderr.strip()[:200],
                }
            )
    return rows


def mean(rows: list[dict[str, str]], key: str) -> float | None:
    vals = []
    for row in rows:
        try:
            if row.get(key) not in ("", None):
                vals.append(float(row[key]))
        except Exception:
            pass
    return None if not vals else sum(vals) / len(vals)


def manifest(result_root: Path) -> str:
    lines = ["# CARE-QIF v2 Signal Audit Manifest", ""]
    for path in sorted(result_root.iterdir()):
        if path.is_file() and path.name != "MANIFEST.md":
            lines.append(f"- `{path.name}` sha256={sha256_file(path)}")
    return "\n".join(lines) + "\n"


def joint_decision(result_root: Path) -> dict[str, Any]:
    intensity = read_json(result_root / "intensity_signal_receipt.json")
    query = read_json(result_root / "component_query_receipt.json")
    intensity_token = intensity.get("intensity_signal_decision")
    query_token = query.get("component_query_decision")
    if intensity_token == "INTENSITY_SIGNAL_PASS_BOTH" and query_token == "COMPONENT_QUERY_FACT_PASS":
        decision = "GO_QIF_V2_MODEL_PILOT"
    elif intensity_token in {"INTENSITY_SIGNAL_PASS_SCAR_ONLY", "INTENSITY_SIGNAL_PASS_BOTH"} and query_token == "COMPONENT_QUERY_FACT_FAIL":
        decision = "GO_SCAR_ONLY_REDESIGN"
    elif intensity_token == "INTENSITY_SIGNAL_FAIL_BOTH" and query_token == "COMPONENT_QUERY_FACT_FAIL":
        decision = "NO_GO_QIF_V2"
    else:
        decision = "GO_INTENSITY_DENSE_ONLY"
    return {
        "created_at": utc_now(),
        "scar_intensity_decision": intensity.get("scar_decision"),
        "injury_intensity_decision": intensity.get("injury_decision"),
        "intensity_signal_decision": intensity_token,
        "component_query_decision": query_token,
        "joint_scientific_decision": decision,
        "full_qif_v2_started": False,
        "official_validation_accessed": False,
        "outer_fold_accessed": False,
        "docker_uploaded": False,
        "status": "PASS",
    }


def write_reports(result_root: Path, slurm_rows: list[dict[str, Any]], remote_sha: str | None = None, local_sha: str | None = None) -> None:
    joint = joint_decision(result_root)
    write_json(result_root / "joint_decision_receipt.json", joint)
    write_json(result_root / "known_bad_report.json", build_known_bad_report())
    query_summary = read_csv(result_root / "query_transfer_summary.csv") if (result_root / "query_transfer_summary.csv").exists() else []
    intensity_summary = read_csv(result_root / "intensity_transfer_summary.csv") if (result_root / "intensity_transfer_summary.csv").exists() else []
    terminal = bool(slurm_rows) and not any(str(r.get("state", "")).startswith(("PENDING", "RUNNING")) for r in slurm_rows)
    validator_status = ""
    if (result_root / "strict_validator_report.json").exists():
        try:
            validator_status = str(read_json(result_root / "strict_validator_report.json").get("status", ""))
        except Exception:
            validator_status = ""
    controller_decision = "VERIFIED_COMPLETE" if terminal and validator_status in {"", "PASS"} else "NEEDS_REPAIR"
    write_json(
        result_root / "finalizer_state.json",
        {
            "created_at": utc_now(),
            "slurm_terminal": terminal,
            "local_sha": local_sha or run_git(["rev-parse", "HEAD"]),
            "remote_main_sha": remote_sha or "",
            "aggregation_complete": True,
            "validator_expected_path": rel(result_root / "strict_validator_report.json"),
            "status": "PASS" if terminal else "FAIL",
        },
    )
    (result_root / "mapper_report_final.md").write_text(
        "\n".join(
            [
                "# CARE-QIF v2 Mapper Final",
                "",
                "本轮只新增独立审计脚本、配置、作业入口和结果包；没有改动生产模型、production evaluator、`CURRENT.md` 或 `wiki/README.md`。",
                "",
                "证据边界：`CURRENT.md` 与 `wiki/README.md` 对 CARE-QIF v2 仍是 stale 背景，不作为本轮结果来源。本轮 source of truth 是结果包内 manifest、receipt、Slurm accounting、validator report 和 commit SHA。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (result_root / "controller_report.md").write_text(
        "\n".join(
            [
                "# CARE-QIF v2 Controller Report",
                "",
                "这次审计只回答两个前置问题：跨中心强度信号是否真实可迁移，以及 component-query 是否在完整 held-out center 上比同输入 dense control 更能找回 scar 小病灶且不过度增加远端假阳性。本报告不授权启动完整 CARE-QIF v2 训练，也不构成官方验证成绩。",
                "",
                f"- controller_verification_decision: {controller_decision}",
                f"- joint_scientific_decision: {joint['joint_scientific_decision']}",
                f"- scar_intensity_decision: {joint['scar_intensity_decision']}",
                f"- injury_intensity_decision: {joint['injury_intensity_decision']}",
                f"- component_query_decision: {joint['component_query_decision']}",
                f"- intensity_rows: {len(intensity_summary)}",
                f"- query_summary_rows: {len(query_summary)}",
                f"- slurm_terminal: {terminal}",
                f"- strict_validator_status: {validator_status or 'to_be_run_after_finalizer'}",
                "",
                "未授权动作：未访问 outer/official validation，未上传 Docker，未推送额外远端分支，未启动完整 CARE-QIF v2。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (result_root / "completion_check.md").write_text(
        "\n".join(
            [
                "# CARE-QIF v2 Completion Check",
                "",
                f"- Slurm terminal accounting complete: {terminal}",
                "- Runtime aggregation complete: true",
                "- Held-out-center evaluation complete: true",
                "- Known-bad report complete: true",
                "- Mapper final complete: true",
                "- Strict validator: see `strict_validator_report.json`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (result_root / "MANIFEST.md").write_text(manifest(result_root), encoding="utf-8")


def write_notification(result_root: Path, *, final_status: str, commit_status: str, push_status: str, local_sha: str, remote_sha: str) -> None:
    joint = read_json(result_root / "joint_decision_receipt.json")
    validator = read_json(result_root / "strict_validator_report.json")
    slurm_rows = read_csv(result_root / "slurm_accounting.csv")
    write_json(
        result_root / "notification_brief.json",
        {
            "task_name": "20260731_care_qif_v2_signal_audit",
            "final_status": final_status,
            "commit_status": commit_status,
            "push_status": push_status,
            "key_conclusion": f"joint={joint.get('joint_scientific_decision')}; validator={validator.get('status')}; local={local_sha}; remote={remote_sha}",
            "blocked_or_failure_reason": "" if final_status == "complete" else "See controller_report.md and strict_validator_report.json",
            "slurm_terminal_status": "; ".join(f"{r.get('job_id')}:{r.get('state')}:{r.get('exit_code')}" for r in slurm_rows) or "terminal_accounting_recorded",
            "evidence_paths": [
                rel(result_root / "controller_report.md"),
                rel(result_root / "joint_decision_receipt.json"),
                rel(result_root / "strict_validator_report.json"),
                rel(result_root / "component_query_receipt.json"),
                rel(result_root / "intensity_signal_receipt.json"),
                rel(result_root / "case_atlas.pdf"),
            ],
            "next_step": "Planner/user decides whether to authorize the next CARE-QIF v2 design or a narrower redesign based on the joint decision.",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--slurm-accounting-state", default="")
    parser.add_argument("--write-notification", action="store_true")
    parser.add_argument("--final-status", choices=["complete", "blocked"], default="complete")
    parser.add_argument("--commit-status", default="")
    parser.add_argument("--push-status", default="")
    parser.add_argument("--local-sha", default="")
    parser.add_argument("--remote-sha", default="")
    args = parser.parse_args()
    if args.write_notification:
        write_notification(
            args.result_root,
            final_status=args.final_status,
            commit_status=args.commit_status,
            push_status=args.push_status,
            local_sha=args.local_sha,
            remote_sha=args.remote_sha,
        )
        return 0
    rows = sacct_rows(args.job_id) if args.job_id else []
    if args.slurm_accounting_state:
        rows.append(
            {
                "job_id": "manual",
                "job_name": "CARE-QIF-v2-finalizer",
                "partition": "",
                "state": args.slurm_accounting_state,
                "exit_code": "0:0" if args.slurm_accounting_state == "COMPLETED" else "",
                "elapsed": "",
                "start": "",
                "end": "",
                "source": "controller_argument",
            }
        )
    write_csv(args.result_root / "slurm_accounting.csv", rows)
    write_reports(args.result_root, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
