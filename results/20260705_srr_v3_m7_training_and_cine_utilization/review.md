# Review 20260705 SRR-v3 M7 Follow-up 2

task_key: `20260705_srr_v3_m7_training_and_cine_utilization`
continued_task: `M7 follow-up 2 leaderboard-oriented repair`
reviewed_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
reviewed_executor_commit: `3229765 Add SRR v3 M7 follow-up2 monitor packet`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`

## Scope

This is a read-only review of the M7 follow-up 2 packet. I did not modify model/training/evaluation code, did not train, did not package or upload validation data, did not claim hosted metrics, did not promote a route, and did not start M8. This review writes only this `review.md`.

The packet is reviewed against `M7 reviewer follow-up 2: leaderboard-oriented repair audit` in `prompts/shared/REVIEWER_PROMPTS.md`.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`, `M7 reviewer follow-up 2: leaderboard-oriented repair audit`
- `prompts/shared/EXECUTOR_PROMPTS.md`, `M7 executor follow-up 2: leaderboard-oriented repair`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- latest M7 continued `review.md` content from this result directory before overwrite
- files under `results/20260705_srr_v3_m7_training_and_cine_utilization/`
- `scripts/evaluation/run_srr_v3_m7_followup2_repair.py`
- `scripts/evaluation/validate_srr_v3_m7_continued_packet.py`
- `scripts/evaluation/run_srr_v3_m7_cine_registration_followup2.py`
- `jobs/src/run_srr_v3_m7_followup2_primary_probe.sh`
- `logs/M7FU2Probe_58021931_20260706_150447.log`

## Executive Finding

The follow-up 2 packet is not complete evidence. It was committed as a monitor packet while the primary MyoPS probe was still pending, and the tracked lightweight evidence was not regenerated after the Slurm job later completed.

This is not an acceptable audited-go state. At review time, live Slurm accounting shows job `58021931` completed successfully, but the committed packet still reports `PENDING_MONITOR` for the follow-up 2 training adequacy, loss components, gradient sanity, and batch composition files. A reviewer cannot convert ignored runtime outputs into audited packet evidence.

There is also a separate Cine blocker: follow-up 2 found a `usable_for_temporal_dictionary=True` registration row, but `temporal_dictionary_evidence.csv` says `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED`. Under the follow-up 2 contract, a usable non-reference registration row makes temporal dictionary follow-up mandatory.

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| Follow-up 2 did not claim route promotion, hosted metrics, validation packaging/upload, challenge-ready status, scientific stop, or M8. | `SUPPORTED` | `completion_check.md` has `route_promotion_decision: NO_PROMOTION`, `hosted_metric_claim: false`, and `validation_packaging_or_upload: false`; `route_to_leaderboard_gap_report.md` states follow-up 2 is not leaderboard-ready or challenge-ready. |
| The packet was submitted as a monitor state, not a completed training result. | `SUPPORTED` | `result.md` says `status: M7_FOLLOWUP2_NEEDS_MONITOR`; `completion_check.md` says `status: M7_FOLLOWUP2_NEEDS_MONITOR`; `followup2_training_adequacy.csv` has `PENDING_MONITOR` for optimizer steps and train-loop seconds. |
| The primary probe had not been incorporated into the tracked evidence packet. | `NOT_SUPPORTED_AS_COMPLETE_EVIDENCE` | `followup2_training_adequacy.csv`, `followup2_loss_component_by_step.csv`, `followup2_loss_component_gradient_sanity.csv`, and `followup2_batch_composition.csv` each contain only pending/monitor placeholders. The tracked packet therefore does not meet the follow-up 2 minimum training/probe evidence requirement. |
| Live Slurm status now proves the job eventually completed. | `SUPPORTED_BUT_NOT_PACKET_EVIDENCE` | `sacct -j 58021931` reports `COMPLETED`, elapsed `00:18:38`, exit code `0:0`, start `2026-07-06T15:04:47`, end `2026-07-06T15:23:25`. `logs/M7FU2Probe_58021931_20260706_150447.log` records start and end. However, this completion happened outside the committed lightweight packet and was not aggregated into the tracked follow-up 2 evidence files. |
| The script explains how an unfinished job entered the result packet. | `SUPPORTED` | `scripts/evaluation/run_srr_v3_m7_followup2_repair.py` sets `M7_FOLLOWUP2_NEEDS_MONITOR` whenever a `training_job_id` is supplied, writes `PENDING_MONITOR` rows, and does not query Slurm or parse the runtime variant output before writing `result.md` and `completion_check.md`. This is a monitor packet generator, not a completion aggregator. |
| Strict validator known-bad gate was repaired relative to follow-up 1. | `SUPPORTED` | `strict_validator_report.csv` includes a good-packet exit `0` and nine mutated known-bad fixtures with actual exit code `1`; `validator_unit_test_report.md` states good packet exits 0, every mutated bad packet exits nonzero, and the key missing-file/ready-with-blocker/temporal/dignostic-mix cases fail. |
| SRR-v3 image fidelity artifacts exist. | `SUPPORTED_WITH_LIMITS` | `srr_v3_image_fidelity_checklist.csv` and `architecture_gap_table.md` exist. The checklist has code/runtime paths, but several rows are only `PARTIAL_VERIFIED`, `REPAIRED_PENDING_FORMAL_TRAINING`, or `PENDING_CINE_ESCALATION`, so this is not route-complete evidence. |
| Branch arbitration no-op repair has code/unit evidence. | `SUPPORTED_WITH_LIMITS` | `branch_arbitration_formula_report.md`, `branch_arbitration_unit_tests.md`, and `arbitration_opening_diagnostics.csv` exist. The diagnostics are still largely smoke/synthetic or pending runtime-probe evidence: `arbitration_opening_diagnostics.csv` has a single `synthetic_unit_roi` row and runtime training probe placeholders. |
| Modality order and no-zero-fill contract artifacts exist. | `SUPPORTED_WITH_LIMITS` | `modality_order_contract.md` and `modality_order_unit_tests.md` exist. I did not find this to be the blocking issue in this review. |
| Follow-up 2 mechanism diagnosis is adequate as completed repaired evidence. | `NOT_SUPPORTED` | `srr_contribution_by_case.csv` still has `correction_gate_open_rate=PENDING_FOLLOWUP2_PROBE` for 192 rows. `proposal_refiner_effectiveness.csv` rows are marked `OLD_M7_EVIDENCE_NOT_REPAIRED_PROBE`. These are diagnostic placeholders, not completed repaired primary-probe evidence. |
| Formal validation and hardcase boundary are preserved. | `SUPPORTED_WITH_LIMITS` | Follow-up 2 files keep promotion blocked and use `NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR` for old M7 rows. This is the correct boundary, but it also confirms that old metric rows cannot support a new best-variant or leaderboard conclusion. |
| Cine follow-up 2 attempted stronger cropped/anatomy-guided registration escalation. | `SUPPORTED` | `cine_registration_followup2_report.md` lists heart-crop affine, tuned SimpleITK Demons/B-spline, cropped ANTsPy attempt when available, optical-flow proxy, and VoxelMorph probe; `registration_same_subset_matrix.csv` has the required `usable_for_temporal_dictionary` field. |
| Cine temporal dictionary gate passes. | `NOT_SUPPORTED` | `registration_same_subset_matrix.csv` contains one row with `usable_for_temporal_dictionary=True` for `heart_crop_SimpleITK_BSpline_or_Demons_tuned`; `temporal_dictionary_evidence.csv` says `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED` and `temporal_dictionary_attempted=False`. The prompt requires temporal dictionary follow-up 2 when at least one usable non-reference registration row exists. |
| `completion_check.md` is acceptable for audited-go. | `NOT_SUPPORTED` | It correctly avoids ready/promotion, but it is a monitor state. It cannot authorize next planning or downstream milestone work. |

## Commands Run

```bash
env GIT_OPTIONAL_LOCKS=0 timeout 8 git status --short --branch
```

Result before writing this review:

```text
## main...origin/main [ahead 2]
?? .tmp/
```

I did not touch `.tmp/`.

```bash
squeue -j 58021931 -o '%i|%P|%j|%T|%M|%l|%R'
sacct -j 58021931 --format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End -P
```

Result:

- `squeue`: no active job row now; Slurm reports invalid job id because the job is no longer in the active queue.
- `sacct`: job `58021931` / `M7FU2Probe` on `htzhulab` is `COMPLETED`, elapsed `00:18:38`, exit code `0:0`, start `2026-07-06T15:04:47`, end `2026-07-06T15:23:25`.

```bash
sed -n '1,260p' results/20260705_srr_v3_m7_training_and_cine_utilization/commands_run.md
sed -n '1,220p' results/20260705_srr_v3_m7_training_and_cine_utilization/followup2_training_adequacy.csv
sed -n '1,220p' results/20260705_srr_v3_m7_training_and_cine_utilization/m7_followup2_training_rerun_decision.md
```

Result: the packet records `squeue ... PENDING Priority` before local commit, `followup2_training_adequacy.csv` is still `PENDING_MONITOR`, and `m7_followup2_training_rerun_decision.md` says `PRIMARY_PROBE_SUBMITTED_NEEDS_MONITOR`.

```bash
sed -n '1,260p' logs/M7FU2Probe_58021931_20260706_150447.log
sed -n '1,260p' results/20260705_srr_v3_m7_training_and_cine_utilization/runtime/variants/m7_followup2_primary_repair/summary.json
```

Result: ignored runtime artifacts show the job later completed and produced runtime outputs, including `actual_optimizer_steps=3316` and `elapsed_seconds=900.238...`. These are not reflected in the tracked follow-up 2 CSV/report packet.

```bash
python - <<'PY'
import csv, pathlib, collections
base=pathlib.Path('results/20260705_srr_v3_m7_training_and_cine_utilization')
for rel in [
 'followup2_training_adequacy.csv',
 'followup2_loss_component_by_step.csv',
 'followup2_loss_component_gradient_sanity.csv',
 'followup2_batch_composition.csv',
 'srr_contribution_by_case.csv',
 'arbitration_opening_diagnostics.csv',
 'proposal_refiner_effectiveness.csv',
 'registration_same_subset_matrix.csv',
 'temporal_dictionary_evidence.csv',
 'strict_validator_report.csv',
]:
    rows=list(csv.DictReader((base/rel).open(newline='')))
    print(rel, len(rows), rows[0].keys() if rows else [])
PY
```

Reviewer parsing found:

- `followup2_training_adequacy.csv`: one row, `PENDING_MONITOR`.
- `followup2_loss_component_by_step.csv`: one row, `PENDING_MONITOR`.
- `followup2_loss_component_gradient_sanity.csv`: one row, `PENDING_MONITOR`.
- `followup2_batch_composition.csv`: one row, `PENDING_MONITOR` and a `required_fields` string, not actual batch rows.
- `srr_contribution_by_case.csv`: 192 rows, all `correction_gate_open_rate=PENDING_FOLLOWUP2_PROBE`.
- `arbitration_opening_diagnostics.csv`: one synthetic row.
- `proposal_refiner_effectiveness.csv`: old-M7 diagnostic evidence, not repaired-probe evidence.
- `registration_same_subset_matrix.csv`: four rows, including one usable registration row.
- `temporal_dictionary_evidence.csv`: one row, temporal dictionary required but not executed.
- `strict_validator_report.csv`: good packet exit 0 plus known-bad failures with exit code 1.

## Why This Happened

The problem is not that the executor claimed the primary probe had completed. The tracked files mostly say the opposite: `M7_FOLLOWUP2_NEEDS_MONITOR` and `PENDING_MONITOR`.

The actual issue is that the packet was committed too early for a review that could decide follow-up 2 adequacy. The monitor packet recorded a submitted Slurm job and then stopped. After the job completed, the executor did not regenerate `followup2_training_adequacy.csv`, `followup2_loss_component_by_step.csv`, `followup2_loss_component_gradient_sanity.csv`, `followup2_batch_composition.csv`, same-split help/harm, hard subgroup metrics, and mechanism diagnostics from the completed run before committing a reviewable packet.

This created a misleading workflow state: there is a committed "follow-up2 monitor packet" with a review request, but the required primary-probe evidence is still pending in tracked files. That cannot be audited as completed evidence.

## Required Executor Repair

1. Regenerate the follow-up 2 lightweight packet from completed job `58021931`:
   - update `followup2_training_adequacy.csv` with actual optimizer steps, train-loop seconds, validation events, and pass/fail decision;
   - update `followup2_loss_component_by_step.csv`;
   - update `followup2_loss_component_gradient_sanity.csv`;
   - update `followup2_batch_composition.csv` with real per-case rows, not a placeholder;
   - update `followup2_same_split_help_harm.csv`, `followup2_hard_subgroup_metrics.csv`, `srr_contribution_by_case.csv`, `arbitration_opening_diagnostics.csv`, and `proposal_refiner_effectiveness.csv` from the repaired primary probe.
2. Keep non-rerun variants marked not comparable unless they are rerun under the same repaired mechanism.
3. Resolve the Cine temporal dictionary gate:
   - either execute temporal dictionary follow-up 2 using the usable non-reference registration row and report the required fields;
   - or revise the registration usability decision if that row is not actually usable under the contract, with exact failure reasons.
4. Keep `route_to_leaderboard_gap_report.md`, `completion_check.md`, and `result.md` explicit that no route promotion, validation packaging/upload, hosted metric claim, M8, scientific stop, challenge-ready, or leaderboard-ready status is authorized.

## Decision

decision: `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`

The strict validator blocker from follow-up 1 appears repaired. However, the follow-up 2 packet is still not complete evidence: the primary MyoPS probe was committed as pending monitor evidence and the tracked packet was not regenerated after the job completed. The Cine branch also found a usable registration row but did not run the mandatory temporal dictionary follow-up.

This decision does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, leaderboard readiness, or challenge-ready status.
