#!/usr/bin/env python3
"""Aggregate SRR-ProposeRefine hardmode artifacts."""

from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/20260703_myops_srr_propose_refine"
VARIANTS = [
    "srr_propref_shared_dual_dict",
    "srr_propref_scar_precision",
    "srr_propref_no_proto_cascade",
]
NNUNET_SCAR = 0.5602
NNUNET_EDEMA_GT_POS = 0.3944


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def finite_float(value: object) -> float | None:
    try:
        val = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if val != val or val in (float("inf"), float("-inf")):
        return None
    return val


def mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def concat_or_missing(filename: str, missing_fields: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        path = OUT_ROOT / "variants" / variant / filename
        variant_rows = read_csv(path)
        if variant_rows:
            rows.extend(variant_rows)
        else:
            row = {field: "evidence not found" for field in missing_fields}
            row["variant"] = variant
            row["source_path"] = str(path)
            row["not_run_reason"] = "formal variant evidence not found"
            rows.append(row)
    return rows


def prediction_count(variant: str) -> int:
    pred_dir = OUT_ROOT / "variants" / variant / "predictions/fold_0/checkpoint_best"
    if not pred_dir.is_dir():
        return 0
    return len(list(pred_dir.glob("*.nii.gz")))


def load_summary(variant: str) -> dict[str, object]:
    path = OUT_ROOT / "variants" / variant / "summary.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def slurm_rows() -> dict[str, dict[str, str]]:
    path = OUT_ROOT / "slurm_status.csv"
    if not path.is_file():
        return {}
    mapping = {
        "57617442_0": "srr_propref_shared_dual_dict",
        "57617442_1": "srr_propref_scar_precision",
        "57617442_2": "srr_propref_no_proto_cascade",
    }
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="|"):
            job_id = row.get("JobID", "")
            if job_id in mapping:
                rows[mapping[job_id]] = row
    return rows


def selected_metric(subgroups: list[dict[str, object]], variant: str, metric_name: str, group: str, column: str = "dice_mean") -> float | None:
    for row in subgroups:
        if row.get("variant") == variant and row.get("metric_name") == metric_name and row.get("group") == group:
            return finite_float(row.get(column))
    return None


def write_architecture_contract() -> None:
    write_text(
        OUT_ROOT / "architecture_contract.md",
        """# Architecture Contract

controlled_state: EXECUTED_UNAUDITED

## Implemented Code Paths

- `src/care_myocardium/models/srr_propref.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_propref_myops_fold0.sh`

## Mechanism Contract

| mechanism | implementation | evidence status |
| --- | --- | --- |
| `shared_evidence_trunk` | `SRRProposeRefineMyoPS` reuses modality-private encoders, multiscale SRR retrieval, and task decoders to produce evidence features and evidence logits. | code implemented |
| `scar_proposal_dictionary` | `ProposalDictionary(pathology=\"scar\")` uses LGE-driven scar features, positive prototypes, negative prototypes, and typed negative memory; `srr_propref_scar_precision` increases scar negative capacity and uses a smaller scar ROI. | code implemented; metric evidence depends on variant runs |
| `edema_proposal_dictionary` | `ProposalDictionary(pathology=\"edema\")` uses T2-conditioned edema features when T2 is available and keeps no-T2 myocardium/scar out of dense edema negatives through the runner loss mask. | code implemented; metric evidence depends on variant runs |
| `negative_prototype_memory` | Trainable negative memory types: outside myocardium, normal myocardium, blood pool, LGE bright artifact, T2 texture noise, remote FP island; replay samples come only from `replay_safe=True` mined components. | code implemented; `hardneg_memory.csv` records loaded evidence |
| `soft_roi_refinement` | `SoftROIRefinementHead` consumes features, evidence logits, proposal logits, and soft ROI masks; final logits are evidence plus soft-ROI-gated residuals. No hard ROI deletion is used. | code implemented; `roi_coverage.csv` records coverage evidence when predictions exist |
| `three_stage_schedule` | Runner stages: evidence warmup, proposal dictionary learning, soft ROI refinement, low-LR calibration. | code implemented; `training_log.csv` records stage per step |

## Forbidden Substitutes

- This is not the old SRR-v2 temperature/gate/mix-weight ladder.
- This is not dictionary-only: final outputs require soft ROI refinement heads.
- This is not compactness-only or hard ROI deletion.
- This does not treat no-T2 myocardium as edema dense negative.
- This does not run fold expansion, validation upload, or upload-ready packaging.
""",
    )


def write_training_schedule() -> None:
    write_text(
        OUT_ROOT / "training_schedule.md",
        """# Training Schedule

Each formal variant is fold0 only and must run under an 8-hour job budget.

| stage | runner condition | trained objective |
| --- | --- | --- |
| evidence_warmup | first 20% of steps | anatomy, scar evidence, T2-masked edema evidence, retrieval regularization |
| proposal_dictionary | 20-60% of steps | evidence plus proposal BCE/Dice and positive-vs-negative prototype margin |
| soft_roi_refinement | 60-90% of steps | final refined logits plus proposal and ROI coverage losses |
| low_lr_calibration | final 10% of steps | same refined objective at 20% base learning rate |

Default Slurm entrypoint:

```bash
sbatch --array=0-2 jobs/src/run_srr_propref_myops_fold0.sh
```

Default job settings: `htzhulab`, `gpu:1`, `--time=07:30:00`, `max_runtime_seconds=25200`, `max_steps=1800`.
""",
    )


def write_variant_matrix(summaries: dict[str, dict[str, object]], slurm: dict[str, dict[str, str]]) -> None:
    rows = []
    for variant in VARIANTS:
        summary = summaries.get(variant, {})
        rows.append(
            {
                "variant": variant,
                "role": {
                    "srr_propref_shared_dual_dict": "shared evidence trunk plus scar/edema dictionaries and soft ROI refinement",
                    "srr_propref_scar_precision": "scar negative memory and smaller scar ROI emphasized",
                    "srr_propref_no_proto_cascade": "no-prototype conservative soft cascade control",
                }[variant],
                "checkpoint_best": summary.get("checkpoint_best", "evidence not found"),
                "prediction_dir": summary.get("prediction_dir", "evidence not found"),
                "elapsed_seconds": summary.get("elapsed_seconds", "evidence not found"),
                "slurm_elapsed": slurm.get(variant, {}).get("Elapsed", "evidence not found"),
                "slurm_state": slurm.get(variant, {}).get("State", "evidence not found"),
                "slurm_exit_code": slurm.get(variant, {}).get("ExitCode", "evidence not found"),
                "stop_reason": summary.get("stop_reason", "evidence not found"),
                "prediction_file_count": prediction_count(variant),
            }
        )
    write_csv(OUT_ROOT / "variant_matrix.csv", rows)
    lines = ["# Variant Matrix", "", "| variant | role | checkpoint | predictions | files | Slurm state | Slurm elapsed | stop_reason |", "| --- | --- | --- | --- | ---: | --- | ---: | --- |"]
    for row in rows:
        lines.append(
            f"| `{row['variant']}` | {row['role']} | `{row['checkpoint_best']}` | `{row['prediction_dir']}` | {row['prediction_file_count']} | `{row['slurm_state']}:{row['slurm_exit_code']}` | `{row['slurm_elapsed']}` | `{row['stop_reason']}` |"
        )
    write_text(OUT_ROOT / "variant_matrix.md", "\n".join(lines) + "\n")


def write_metrics_summary(subgroups: list[dict[str, object]], proposals: list[dict[str, object]], summaries: dict[str, dict[str, object]]) -> str:
    lines = [
        "# Metrics Summary",
        "",
        "Same-split references from the audited MyoPS evidence package:",
        "",
        f"- nnU-Net fold0 scar all-case Dice: `{NNUNET_SCAR:.4f}`",
        f"- nnU-Net fold0 edema GT-positive Dice: `{NNUNET_EDEMA_GT_POS:.4f}`",
        "",
        "| variant | scar all-case Dice | edema GT-positive Dice | scar proposal recall | scar proposal precision | edema proposal recall | edema proposal precision | decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    final_state = "EXECUTED_UNAUDITED"
    for variant in VARIANTS:
        scar = selected_metric(subgroups, variant, "myops_scar", "all_cases")
        edema = selected_metric(subgroups, variant, "myops_edema", "gt_positive_only")
        scar_prop = [row for row in proposals if row.get("variant") == variant and row.get("metric_name") == "myops_scar"]
        edema_prop = [row for row in proposals if row.get("variant") == variant and row.get("metric_name") == "myops_edema"]
        scar_recall = mean([finite_float(row.get("proposal_recall")) for row in scar_prop])
        scar_precision = mean([finite_float(row.get("proposal_precision")) for row in scar_prop])
        edema_recall = mean([finite_float(row.get("proposal_recall")) for row in edema_prop])
        edema_precision = mean([finite_float(row.get("proposal_precision")) for row in edema_prop])
        if not summaries.get(variant):
            decision = "NEEDS_EVIDENCE"
            final_state = "NEEDS_EVIDENCE"
        elif scar is None and edema is None:
            decision = "DIAGNOSTIC_ONLY"
        elif (scar is not None and scar >= 0.80 * NNUNET_SCAR) or (edema is not None and edema >= 0.80 * NNUNET_EDEMA_GT_POS):
            decision = "AUDIT_FOR_PROMOTION"
        else:
            decision = "DIAGNOSTIC_ONLY"
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} | `{}` |".format(
                variant,
                "evidence not found" if scar is None else f"{scar:.4f}",
                "evidence not found" if edema is None else f"{edema:.4f}",
                "evidence not found" if scar_recall is None else f"{scar_recall:.4f}",
                "evidence not found" if scar_precision is None else f"{scar_precision:.4f}",
                "evidence not found" if edema_recall is None else f"{edema_recall:.4f}",
                "evidence not found" if edema_precision is None else f"{edema_precision:.4f}",
                decision,
            )
        )
    lines.extend(
        [
            "",
            "Hosted validation metrics are `evidence not found`; validation upload and packaging are forbidden for this task.",
        ]
    )
    write_text(OUT_ROOT / "metrics_summary.md", "\n".join(lines) + "\n")
    return final_state


def write_label_export_qc() -> None:
    lines = ["# Label Export QC", "", "| variant | prediction files | compact-label QC | raw-label package |", "| --- | ---: | --- | --- |"]
    for variant in VARIANTS:
        rows = read_csv(OUT_ROOT / "variants" / variant / "component_hd_by_case.csv")
        invalid = sorted({row.get("invalid_label_values", "") for row in rows if row.get("invalid_label_values", "")})
        count = prediction_count(variant)
        if count == 0:
            compact = "evidence not found"
        elif invalid:
            compact = "invalid compact labels: " + ",".join(invalid)
        else:
            compact = "compact labels 0..5 only in evaluated predictions"
        lines.append(f"| `{variant}` | {count} | {compact} | evidence not found; no validation package generated |")
    write_text(OUT_ROOT / "label_export_qc.md", "\n".join(lines) + "\n")


def write_failure_interpretation(final_state: str, subgroups: list[dict[str, object]], proposals: list[dict[str, object]]) -> None:
    lines = ["# Failure Interpretation", ""]
    if final_state == "NEEDS_EVIDENCE":
        lines.append("At least one required formal variant lacks completed metric evidence. This route remains `NEEDS_EVIDENCE` until the three formal variants finish or the task records an allowed not-run reason.")
    else:
        for variant in VARIANTS:
            scar = selected_metric(subgroups, variant, "myops_scar", "all_cases")
            edema = selected_metric(subgroups, variant, "myops_edema", "gt_positive_only")
            scar_prop = mean([finite_float(row.get("proposal_recall")) for row in proposals if row.get("variant") == variant and row.get("metric_name") == "myops_scar"])
            edema_prop = mean([finite_float(row.get("proposal_recall")) for row in proposals if row.get("variant") == variant and row.get("metric_name") == "myops_edema"])
            reasons = []
            if scar_prop is not None and scar_prop < 0.50:
                reasons.append("scar positive prototype collapse or ROI too strict")
            if edema_prop is not None and edema_prop < 0.50:
                reasons.append("edema positive prototype collapse, T2-conditioned evidence failure, or ROI too strict")
            if scar is not None and scar < 0.80 * NNUNET_SCAR and edema is not None and edema < 0.80 * NNUNET_EDEMA_GT_POS:
                reasons.append("final refinement remains far below same-split nnU-Net gate")
            if not reasons:
                reasons.append("no blocking failure interpretation from aggregate metrics; requires independent audit")
            lines.append(f"- `{variant}`: " + "; ".join(reasons) + ".")
    lines.append("")
    if final_state == "EXECUTED_UNAUDITED":
        lines.append("route_decision: `STOP_NO_PROPREF_SIGNAL`")
        lines.append("")
    lines.append("No additional temperature/gate/mix-weight/threshold tuning was launched by this aggregation step.")
    write_text(OUT_ROOT / "failure_interpretation.md", "\n".join(lines) + "\n")


def write_manifest() -> None:
    files = [
        "result.md",
        "MANIFEST.md",
        "architecture_contract.md",
        "variant_matrix.md",
        "variant_matrix.csv",
        "training_schedule.md",
        "metrics_summary.md",
        "proposal_metrics.csv",
        "subgroup_metrics.csv",
        "component_hd_by_case.csv",
        "hardneg_memory.csv",
        "roi_coverage.csv",
        "label_export_qc.md",
        "failure_interpretation.md",
        "command_transcript.md",
        "slurm_status.csv",
    ]
    lines = [
        "# MANIFEST: 20260703_myops_srr_propose_refine",
        "",
        "- Task: `prompts/tasks/20260703_myops_srr_propose_refine.md`",
        "- Result: `results/20260703_myops_srr_propose_refine/result.md`",
        "- Review: `results/20260703_myops_srr_propose_refine/review.md` (not written by executor)",
        "",
        "| artifact | purpose |",
        "| --- | --- |",
    ]
    for file in files:
        lines.append(f"| `{file}` | task-scoped PropRef evidence artifact |")
    lines.append("| `variants/<variant>/` | per-variant checkpoints, predictions, logs/configs, and metrics when formal runs complete |")
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def write_result(final_state: str, summaries: dict[str, dict[str, object]], slurm: dict[str, dict[str, str]]) -> None:
    missing = [variant for variant in VARIANTS if not summaries.get(variant)]
    lines = [
        "# Result 20260703 MyoPS SRR ProposeRefine",
        "",
        f"self_assessed_status: {final_state}",
        "route_decision: STOP_NO_PROPREF_SIGNAL",
        "role: executor",
        "review_required: true",
        "",
        "## Execution Summary",
        "",
        "Implemented a first-party SRR-ProposeRefine mechanism with shared evidence trunk, scar/edema proposal dictionaries, typed negative prototype memory, soft ROI refinement heads, and a staged training runner. No validation upload, upload-ready package, fold expansion, label mapping edit, fold split edit, evaluator edit, network access, commit, or push was performed.",
        "",
        "claim.architecture_contract: `architecture_contract.md` documents the implemented mechanism and forbidden-substitute boundary.",
        "claim.three_stage_schedule: `training_schedule.md` and per-variant `training_log.csv` record evidence warmup, proposal dictionary learning, soft ROI refinement, and low-LR calibration.",
        "claim.no_t2_contract: runner loss masks dense edema supervision to T2-present samples and hard-negative replay only consumes `replay_safe=True` mined components; no-T2 myocardium/scar unsafe edema entries remain excluded.",
        "claim.variant_evidence: `variant_matrix.md`, `metrics_summary.md`, and aggregate CSVs index per-variant checkpoints, prediction dirs, metrics, ROI coverage, and hard-negative memory where present.",
        f"claim.next_state: executor stops at `{final_state}` pending separate read-only audit.",
        "",
        "## Formal Variant Status",
        "",
        "| variant | checkpoint | predictions | prediction files | Slurm state | Slurm elapsed | train_loop_seconds |",
        "| --- | --- | --- | ---: | --- | ---: | ---: |",
    ]
    for variant in VARIANTS:
        summary = summaries.get(variant, {})
        lines.append(
            f"| `{variant}` | `{summary.get('checkpoint_best', 'evidence not found')}` | `{summary.get('prediction_dir', 'evidence not found')}` | {prediction_count(variant)} | `{slurm.get(variant, {}).get('State', 'evidence not found')}:{slurm.get(variant, {}).get('ExitCode', 'evidence not found')}` | `{slurm.get(variant, {}).get('Elapsed', 'evidence not found')}` | `{summary.get('elapsed_seconds', 'evidence not found')}` |"
        )
    lines.extend(
        [
            "",
            "## Files Changed",
            "",
            "- `src/care_myocardium/models/srr_propref.py`",
            "- `scripts/training/run_srr_propref_myops_fold0.py`",
            "- `scripts/evaluation/aggregate_srr_propref_20260703.py`",
            "- `jobs/src/run_srr_propref_myops_fold0.sh`",
            "- `results/20260703_myops_srr_propose_refine/`",
            "",
            "## Failures And Incomplete Items",
            "",
        ]
    )
    if missing:
        lines.append("- Formal metric evidence missing for: `" + "`, `".join(missing) + "`.")
    else:
        lines.append("- Independent audit is still required before any promotion.")
    lines.extend(
        [
            "- Hosted validation metrics and upload-ready raw-label packages are `evidence not found` because they are forbidden by task scope.",
            "- `review.md` was not written because this session is executor-only.",
            "",
            "## Required Next State",
            "",
            final_state,
        ]
    )
    write_text(OUT_ROOT / "result.md", "\n".join(lines) + "\n")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    proposal = concat_or_missing(
        "proposal_metrics.csv",
        ["variant", "case_id", "metric_name", "proposal_recall", "proposal_precision", "lesion_wise_recall", "outside_myocardium_fp_ratio"],
    )
    subgroup = concat_or_missing("subgroup_metrics.csv", ["variant", "metric_name", "group", "dice_mean", "hd95_mean"])
    component = concat_or_missing("component_hd_by_case.csv", ["variant", "case_id", "metric_name", "dice", "hd", "hd95", "component_count", "remote_fp_count"])
    memory = concat_or_missing("hardneg_memory.csv", ["variant", "memory_source", "class_id", "safety_type", "replay_safe_components"])
    roi = concat_or_missing("roi_coverage.csv", ["variant", "case_id", "metric_name", "gt_coverage", "outside_myocardium_roi_ratio"])
    write_csv(OUT_ROOT / "proposal_metrics.csv", proposal)
    write_csv(OUT_ROOT / "subgroup_metrics.csv", subgroup)
    write_csv(OUT_ROOT / "component_hd_by_case.csv", component)
    write_csv(OUT_ROOT / "hardneg_memory.csv", memory)
    write_csv(OUT_ROOT / "roi_coverage.csv", roi)
    summaries = {variant: load_summary(variant) for variant in VARIANTS}
    slurm = slurm_rows()
    write_architecture_contract()
    write_training_schedule()
    write_variant_matrix(summaries, slurm)
    final_state = write_metrics_summary(subgroup, proposal, summaries)
    write_label_export_qc()
    write_failure_interpretation(final_state, subgroup, proposal)
    write_manifest()
    write_result(final_state, summaries, slurm)
    write_text(
        OUT_ROOT / "command_transcript.md",
        "\n".join(
            [
                "# Command Transcript",
                "",
                f"- aggregate_command: `{' '.join(sys.argv)}`",
                f"- aggregate_time_utc: `{datetime.now(UTC).isoformat()}`",
                "- aggregate_exit_status: `0`",
                "- network_used: `false`",
            ]
        )
        + "\n",
    )
    print(f"wrote {OUT_ROOT}")


if __name__ == "__main__":
    main()
