#!/usr/bin/env python3
"""Build the V1 gap audit required by the V2 forensic completion contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


GAP_TOKENS = [
    "NOT_RUN",
    "REQUIRES_",
    "MISSING",
    "UNRESOLVED",
    "PARTIAL",
    "STALE",
    "PLACEHOLDER",
    "VISUAL_HUMAN_CONFIRMATION_PENDING",
    "GPU_DIAGNOSTICS_NOT_TERMINAL",
    "UNBOUND_CHECKPOINT",
    "UNBOUND_PREDICTION",
    "UNBOUND_RECIPE",
    "NEEDS_REPAIR",
    "NEEDS_FEATURE_BINDING",
    "NEEDS_RECIPE_BINDING",
    "NEEDS_CINE_BINDING",
]

V2_REQUIRED_OUTPUTS = [
    "v2_gap_completion_manifest.json",
    "v2_task_status.csv",
    "v2_gpu_job_manifest.csv",
    "v2_evidence_claim_ledger.csv",
    "v2_source_manifest.csv",
    "v2_hash_manifest.csv",
    "historical_model_inventory.csv",
    "historical_experiment_inventory.csv",
    "historical_commit_lineage.csv",
    "historical_checkpoint_binding.csv",
    "historical_prediction_binding.csv",
    "batch0_7_design_evidence_matrix.csv",
    "batch0_7_casewise_results.csv",
    "batch0_7_component_survival_ledger.csv",
    "batch7_mechanism_trace.md",
    "mmrd_forensics_report.md",
    "cascade_dg_dpr_forensics_report.md",
    "arc_forensics_report.md",
    "prism_forensics_report.md",
    "mosaic_gap_forensics_report.md",
    "standardized_casewise_metrics.csv",
    "standardized_model_summary.csv",
    "standardized_subgroup_summary.csv",
    "standardized_help_harm.csv",
    "case_oracle_summary.csv",
    "voxel_error_overlap_matrix.csv",
    "selector_nested_cv_results.csv",
    "feature_probe_summary.csv",
    "decoder_reset_comparison.csv",
    "alignment_error_correlation.csv",
    "cine_temporal_signal_probe.csv",
    "historical_component_survival_ledger.csv",
    "large_gain_feasibility_analysis.csv",
    "deep_research_design_constraints_evidence.csv",
    "historical_component_survival_report.md",
    "large_gain_feasibility_report.md",
    "deep_research_design_brief.md",
    "external_deep_research_question_bank.md",
    "deep_research_prompt_seed.md",
    "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v2.pdf",
    "v2_pdf_validation_report.json",
    "v2_known_bad_report.json",
    "v2_strict_validator_report.json",
    "v2_completion_check.md",
    "v2_controller_report.md",
    "v2_MANIFEST.md",
    "notification_brief.json",
]

V2_REQUIRED_SECTIONS = [
    "当前 V1 为什么不完整",
    "Batch 0",
    "Batch7 深入复盘",
    "MMRD",
    "Cascade",
    "DG/DR/DPR",
    "ARC",
    "PRISM",
    "MoSAIC source/weight/recipe",
    "统一病例级指标",
    "视觉病例图册",
    "error overlap",
    "oracle",
    "selector",
    "feature probes",
    "decoder-reset",
    "alignment",
    "Cine",
    "历史组件生存清单",
    "约 0.1 Dice 上限分析",
    "Deep Research 设计约束证据",
]

REQUIRED_GPU_TASKS = {
    "G1_NNUNET_IDENTITY_REPRODUCTION": [
        "D0_FULL_PRETRAINED_IDENTITY",
        "nnU-Net identity",
    ],
    "G2_PRISM_13_CHECKPOINT_REPLAY": [
        "PRISM 13",
        "checkpoint_count: 13",
        "checkpoint_count\": 13",
    ],
    "G3_DECODER_RESET_D0_D3_REAL_NNUNET": [
        "D1_DECODER_RESET_ENCODER_FROZEN",
        "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE",
        "D3_FULL_MODEL_SHORT_FINETUNE",
    ],
    "G4_MOSAIC_RECIPE_DECOMPOSITION": [
        "M0 clean",
        "M10 exact",
        "mosaic_recipe_decomposition",
    ],
    "G5_FROZEN_FEATURE_PROBES": [
        "feature_probe_summary.csv",
        "feature_probe_full_results.csv",
    ],
    "G6_MODEL_COMPLEMENTARITY": [
        "case_oracle_summary.csv",
        "voxel_error_overlap_matrix.csv",
    ],
    "G7_SELECTOR_FEASIBILITY": [
        "selector_nested_cv_results.csv",
    ],
    "G8_ALIGNMENT_DIAGNOSTICS": [
        "alignment_error_correlation.csv",
    ],
    "G9_CINE_ED_ONLY_VS_TEMPORAL": [
        "cine_temporal_signal_probe.csv",
    ],
    "G10_OLD_MODEL_REPLAY": [
        "Batch7",
        "MMRD",
        "Cascade",
        "ARC",
        "DG/DR/DPR",
    ],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(root: Path, rev: str) -> str:
    return subprocess.check_output(["git", "rev-parse", rev], cwd=root, text=True).strip()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(read_text(path))
    except Exception as exc:
        return {"_error": str(exc)}


def iter_text_files(packet: Path) -> list[Path]:
    suffixes = {".csv", ".json", ".jsonl", ".md", ".tex", ".txt", ".log"}
    excluded_parts = {
        "runtime",
        "pdf_pages",
        "chromium_preview",
        "xelatex_final_preview",
        "figures",
        "feature_probe_pca_figures",
        "feature_probe_umap_figures",
    }
    paths: list[Path] = []
    for path in packet.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in excluded_parts for part in path.relative_to(packet).parts):
            continue
        paths.append(path)
    return sorted(paths)


def csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open(newline="", encoding="utf-8", errors="ignore") as f:
            return max(0, sum(1 for _ in csv.DictReader(f)))
    except Exception:
        return 0


def status_from_file(path: Path, text: str) -> tuple[str, str]:
    rel = path.name
    if path.suffix == ".csv":
        rows = csv_row_count(path)
        if rows == 0:
            return "MISSING_OR_EMPTY", "CSV has no data rows."
        if any(token in text for token in ["NOT_RUN", "REQUIRES_", "PLACEHOLDER", "UNBOUND_", "NEEDS_"]):
            return "INCOMPLETE_OR_PLACEHOLDER", "CSV contains gap/status tokens."
        if rel in {
            "feature_probe_summary.csv",
            "mosaic_recipe_decomposition_casewise.csv",
            "mosaic_recipe_decomposition_summary.csv",
            "selector_nested_cv_results.csv",
            "case_oracle_summary.csv",
            "voxel_error_overlap_matrix.csv",
            "cine_temporal_signal_probe.csv",
        } and rows <= 1:
            return "TOO_SHALLOW_FOR_V2", "V2 requires executed evidence, not one-row placeholders."
        return "PRESENT_NEEDS_CONTENT_REVIEW", f"CSV rows: {rows}."
    if path.suffix == ".json":
        payload = read_json(path)
        if isinstance(payload, dict):
            status = str(payload.get("status") or payload.get("controller_verification_decision") or "")
        elif isinstance(payload, list):
            status = f"list[{len(payload)}]"
        else:
            status = type(payload).__name__
        if status in {"FAIL", "NEEDS_REPAIR", "NOT_RUN"}:
            return "INCOMPLETE_OR_FAIL", f"JSON status is {status}."
        if any(token in text for token in ["NOT_RUN", "REQUIRES_", "PLACEHOLDER", "UNBOUND_", "NEEDS_"]):
            return "INCOMPLETE_OR_PLACEHOLDER", "JSON contains gap/status tokens."
        return "PRESENT_NEEDS_CONTENT_REVIEW", f"JSON status: {status or 'not declared'}."
    if any(token in text for token in ["NOT_RUN", "REQUIRES_", "PLACEHOLDER", "UNRESOLVED", "PARTIAL", "NEEDS_REPAIR"]):
        return "INCOMPLETE_OR_PLACEHOLDER", "Text contains V1 gap/status tokens."
    return "PRESENT_NEEDS_CONTENT_REVIEW", "Text present."


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--packet", type=Path, default=Path("results/20260730_care_failure_forensics_deep_research_packet"))
    ap.add_argument("--task-prompt", type=Path, required=True)
    args = ap.parse_args()

    repo = args.root.resolve()
    packet = (repo / args.packet).resolve()
    now = datetime.now(UTC).isoformat()
    prompt = args.task_prompt.resolve()

    strict = read_json(packet / "strict_validator_report.json")
    finalizer = read_json(packet / "finalizer_state.json")
    completion_text = read_text(packet / "completion_check.md")
    pdf_text = read_text(packet / "pdf_text_extract.txt")

    source_files = [
        "AGENTS.md",
        "START_HERE_FOR_GPT.md",
        "GPT_PLANNER_CARE_PROTOCOL.md",
        "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
        "prompts/AGENT_FLOW_V2_PROTOCOL.md",
        "prompts/HANDOFF_GATE_POLICY.md",
        "prompts/GPT_HARD_GATE_PROMPT.md",
        "prompts/routes/README.md",
        "prompts/routes/handoffs/CURRENT.md",
        "prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md",
        "prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md",
        "routes/README.md",
        "wiki/README.md",
        ".agents/skills/slurm-routing-partition/SKILL.md",
        ".agents/skills/care-mapper/SKILL.md",
    ]
    source_manifest_rows = []
    for rel in source_files:
        path = repo / rel
        source_manifest_rows.append(
            {
                "path": rel,
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else "",
                "size_bytes": path.stat().st_size if path.exists() else "",
                "role": "V2_CONTRACT_BOOTSTRAP_SOURCE",
            }
        )
    write_csv(
        packet / "v2_source_manifest.csv",
        source_manifest_rows,
        ["path", "exists", "sha256", "size_bytes", "role"],
    )

    file_rows = []
    token_counter: Counter[str] = Counter()
    token_examples: dict[str, list[str]] = defaultdict(list)
    for path in iter_text_files(packet):
        text = read_text(path)
        rel = str(path.relative_to(packet))
        for token in GAP_TOKENS:
            count = text.count(token)
            if count:
                token_counter[token] += count
                if len(token_examples[token]) < 12:
                    token_examples[token].append(rel)
        status, notes = status_from_file(path, text)
        file_rows.append(
            {
                "path": rel,
                "status": status,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "notes": notes,
            }
        )

    write_csv(packet / "v1_required_task_status.csv", file_rows, ["path", "status", "size_bytes", "sha256", "notes"])

    section_rows = []
    for section in V2_REQUIRED_SECTIONS:
        present_v1 = section in pdf_text
        section_rows.append(
            {
                "required_v2_section": section,
                "present_in_v1_pdf_text": present_v1,
                "v1_status": "PRESENT_BUT_NEEDS_COMPLETION_AUDIT" if present_v1 else "MISSING_FROM_V1_PDF",
                "notes": "Presence is not evidence of executed GPU/metric work." if present_v1 else "Required by V2 PDF contract.",
            }
        )
    write_csv(
        packet / "v1_pdf_section_completeness.csv",
        section_rows,
        ["required_v2_section", "present_in_v1_pdf_text", "v1_status", "notes"],
    )

    required_output_rows = []
    for rel in V2_REQUIRED_OUTPUTS:
        path = packet / rel
        required_output_rows.append(
            {
                "required_v2_output": rel,
                "exists_now": path.exists(),
                "status": "EXISTS_NEEDS_V2_REVIEW" if path.exists() else "MISSING_FOR_V2",
                "size_bytes": path.stat().st_size if path.exists() else "",
                "notes": "V1-era file cannot be assumed V2-complete." if path.exists() else "Must be generated for V2 completion.",
            }
        )

    gpu_rows = []
    all_text_blob = "\n".join(read_text(p) for p in iter_text_files(packet))
    completed = set(finalizer.get("completed_diagnostics", []))
    missing_diag = set(finalizer.get("missing_required_diagnostics", []))
    for task_id, needles in REQUIRED_GPU_TASKS.items():
        evidence_hits = [n for n in needles if n in all_text_blob or n in completed]
        if task_id == "G1_NNUNET_IDENTITY_REPRODUCTION" and "D0_FULL_PRETRAINED_IDENTITY" in completed:
            status = "PARTIAL_COMPLETED_D0_ONLY"
            notes = "D0 replay exists, but V2 requires G1 consistency/hash comparison against baseline."
        elif task_id == "G3_DECODER_RESET_D0_D3_REAL_NNUNET":
            status = "NOT_COMPLETE"
            notes = (
                "D1-D3 are missing from finalizer. Prior PRISM wrapper artifacts are explicitly non-contract because V2 requires real nnU-Net decoder/plans/loss."
            )
        else:
            status = "REQUIRED_NOT_TERMINAL"
            if evidence_hits:
                notes = f"Text hits only, not terminal V2 GPU evidence: {';'.join(evidence_hits[:5])}."
            else:
                notes = "No terminal V2 GPU evidence found."
        gpu_rows.append(
            {
                "gpu_task": task_id,
                "v1_status": status,
                "evidence_hits": ";".join(evidence_hits),
                "notes": notes,
            }
        )
    write_csv(packet / "v2_gpu_job_manifest.csv", gpu_rows, ["gpu_task", "v1_status", "evidence_hits", "notes"])

    known_blockers = [
        {
            "blocker_id": "B-V1-STRICT-001",
            "severity": "HIGH",
            "status": "OPEN",
            "evidence": "strict_validator_report.json",
            "detail": f"V1 strict validator status={strict.get('status')} decision={strict.get('controller_verification_decision')} hard_fail_count={strict.get('hard_fail_count')}.",
        },
        {
            "blocker_id": "B-V1-GPU-001",
            "severity": "HIGH",
            "status": "OPEN",
            "evidence": "finalizer_state.json",
            "detail": "Missing diagnostics: " + "; ".join(finalizer.get("missing_required_diagnostics", [])),
        },
        {
            "blocker_id": "B-V1-PDF-001",
            "severity": "HIGH",
            "status": "OPEN",
            "evidence": "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf",
            "detail": "V1 PDF has 20 pages; V2 contract requires a completed evidence packet with 70-150 pages expected and no required placeholders.",
        },
        {
            "blocker_id": "B-V1-PRISM-D1D2-001",
            "severity": "HIGH",
            "status": "OPEN",
            "evidence": "runtime/decoder_reset_diagnostics",
            "detail": "Interrupted PRISM diagnostic artifacts must not be counted as V2 decoder-reset D1-D3 because they do not use real nnU-Net decoder/plans/6-class Dice+CE.",
        },
    ]

    gap_json = {
        "status": "V1_INCOMPLETE_REQUIRES_V2_COMPLETION",
        "generated_utc": now,
        "repo": str(repo),
        "packet": str(packet),
        "task_key": "20260730_care_failure_forensics_deep_research_packet_v2_completion",
        "task_prompt": str(prompt),
        "task_prompt_sha256": sha256_file(prompt),
        "git_head": git_head(repo, "HEAD"),
        "origin_main": git_head(repo, "origin/main"),
        "v1_strict_validator": {
            "status": strict.get("status"),
            "decision": strict.get("controller_verification_decision"),
            "hard_fail_count": strict.get("hard_fail_count"),
            "checks": strict.get("checks", []),
        },
        "v1_finalizer": finalizer,
        "completion_check_excerpt": completion_text[:1000],
        "gap_token_counts": dict(token_counter),
        "gap_token_examples": token_examples,
        "known_blockers": known_blockers,
        "required_gpu_tasks": gpu_rows,
        "required_v2_outputs": required_output_rows,
        "non_contract_residuals": [
            {
                "path": "results/20260730_care_failure_forensics_deep_research_packet/runtime/decoder_reset_diagnostics",
                "status": "NON_CONTRACT_PRISM_DIAGNOSTIC_RESIDUAL",
                "reason": "Generated by interrupted PRISM wrapper; V2 requires real nnU-Net D1-D3 diagnostics.",
            }
        ],
        "next_required_action": "Generate true V2 evidence plan and run required GPU diagnostics sequentially, starting with real nnU-Net G1/G3 preflight.",
    }
    (packet / "v1_gap_audit.json").write_text(json.dumps(gap_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    task_rows = [
        {
            "task": "V1 strict validator",
            "status": strict.get("status", "UNKNOWN"),
            "evidence": "strict_validator_report.json",
            "next_action": "Must be replaced by V2 strict validator after all required evidence completes.",
        },
        {
            "task": "V1 PDF",
            "status": "INCOMPLETE_V1_DO_NOT_OVERWRITE",
            "evidence": "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf",
            "next_action": "Generate CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v2.pdf.",
        },
        {
            "task": "D0 identity replay",
            "status": "PARTIAL_COMPLETED",
            "evidence": "d0_identity_replay_completion_receipt.json",
            "next_action": "Upgrade to V2 G1 with baseline consistency/hash comparison.",
        },
        {
            "task": "D1-D3 decoder reset",
            "status": "NOT_COMPLETE",
            "evidence": "finalizer_state.json",
            "next_action": "Run real nnU-Net D1-D3. Do not count PRISM diagnostic residuals.",
        },
        {
            "task": "Feature probes",
            "status": "NOT_COMPLETE",
            "evidence": "feature_probe_summary.csv",
            "next_action": "Run patient-level feature probes or record verified missing bound assets.",
        },
        {
            "task": "MoSAIC decomposition",
            "status": "NOT_COMPLETE",
            "evidence": "mosaic_recipe_decomposition_summary.csv",
            "next_action": "Bind MoSAIC source/weights and run M0-M10 or verified asset-blocker audit.",
        },
        {
            "task": "Cine temporal probe",
            "status": "NOT_COMPLETE",
            "evidence": "cine_temporal_signal_probe.csv",
            "next_action": "Run ED-only vs temporal probe or verified asset-blocker audit.",
        },
    ]
    write_csv(packet / "v2_task_status.csv", task_rows, ["task", "status", "evidence", "next_action"])

    md_lines = [
        "# V1 gap audit for V2 completion",
        "",
        "当前结论：V1 不是可进入 Deep Research 的终态证据包。它已经解决了 PDF 可搜索和部分清单问题，但核心本地证据仍未完成，尤其是统一指标、历史模型逐轮恢复、MoSAIC recipe decomposition、feature probe、selector/oracle、Cine temporal probe 和真实 nnU-Net decoder-reset D1-D3。",
        "",
        "## Validator state",
        "",
        f"- V1 strict validator: `{strict.get('status')}` / `{strict.get('controller_verification_decision')}`.",
        f"- Hard fail count: `{strict.get('hard_fail_count')}`.",
        f"- Missing diagnostics: `{'; '.join(finalizer.get('missing_required_diagnostics', []))}`.",
        "",
        "## Critical correction",
        "",
        "上一轮遗留的 `runtime/decoder_reset_diagnostics` 是 PRISM wrapper 诊断残留，不满足 V2 合同中“真实 nnU-Net plans、decoder、patch sampling、augmentation 和六类 loss”的 D1-D3 要求。它只能作为非合同残留记录，不得算入 decoder-reset 完成。",
        "",
        "## Gap tokens",
        "",
    ]
    for token, count in token_counter.most_common():
        md_lines.append(f"- `{token}`: {count}")
    md_lines += [
        "",
        "## Required GPU tasks",
        "",
        "| GPU task | V1 status | Notes |",
        "| --- | --- | --- |",
    ]
    for row in gpu_rows:
        md_lines.append(f"| `{row['gpu_task']}` | `{row['v1_status']}` | {row['notes']} |")
    md_lines += [
        "",
        "## Immediate next action",
        "",
        "先完成真实 nnU-Net G1/G3 preflight 和执行入口，再串行运行合同要求的 GPU 诊断。V1 PDF 不得覆盖；V2 PDF 必须另存为 `CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v2.pdf`。",
        "",
        "Generated files:",
        "",
        "- `v1_gap_audit.json`",
        "- `v1_pdf_section_completeness.csv`",
        "- `v1_required_task_status.csv`",
        "- `v2_task_status.csv`",
        "- `v2_gpu_job_manifest.csv`",
        "- `v2_source_manifest.csv`",
    ]
    (packet / "v1_gap_audit.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    v2_manifest = {
        "status": "V2_STARTED_FROM_V1_GAP_AUDIT",
        "generated_utc": now,
        "v1_pdf_preserved": str(packet / "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf"),
        "v2_pdf_target": str(packet / "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v2.pdf"),
        "generated_files": [
            "v1_gap_audit.md",
            "v1_gap_audit.json",
            "v1_pdf_section_completeness.csv",
            "v1_required_task_status.csv",
            "v2_task_status.csv",
            "v2_gpu_job_manifest.csv",
            "v2_source_manifest.csv",
        ],
        "controller_decision": "CONTINUE_V2_COMPLETION",
    }
    (packet / "v2_gap_completion_manifest.json").write_text(
        json.dumps(v2_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(v2_manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
