# Review 20260705 SRR-v3 M7 Follow-up 3

task_key: `20260705_srr_v3_m7_training_and_cine_utilization`
continued_task: `M7 follow-up 3 completion-safe re-aggregation and temporal dictionary repair`
reviewed_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
reviewed_executor_commit: `9c19d98 Add SRR v3 M7 follow-up3 completion packet`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`

## Scope

This is a read-only review of the M7 follow-up3 packet. I did not modify model/training/evaluation code, did not train, did not package or upload validation data, did not claim hosted metrics, did not promote a route, and did not start M8. This review writes only this `review.md`.

Follow-up3 is reviewed narrowly against the current `M7 reviewer follow-up 3: completion-safe re-aggregation and temporal dictionary repair audit` contract. That contract did not ask for a new 8-hour training run. It asked the executor to re-aggregate the already completed follow-up2 Slurm probe into tracked lightweight evidence, remove monitor placeholders, and close the Cine temporal-dictionary gap created by a usable registration row.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`, global monitor rule and `M7 reviewer follow-up 3`
- `prompts/shared/EXECUTOR_PROMPTS.md`, global monitor rule and `M7 executor follow-up 3`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- files under `results/20260705_srr_v3_m7_training_and_cine_utilization/`
- `scripts/evaluation/validate_srr_v3_m7_followup3_packet.py`
- latest M7 follow-up2 review content from this result directory before overwrite

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| Follow-up3 did not claim route promotion, hosted metrics, validation packaging/upload, fold expansion, challenge submission, scientific stop, leaderboard readiness, challenge readiness, or M8. | `SUPPORTED` | `result.md`, `completion_check.md`, `review_request.md`, `route_to_leaderboard_gap_report.md`, and `failure_interpretation.md` keep those boundaries explicit. |
| The old monitor packet was converted into post-completion tracked evidence. | `SUPPORTED` | `m7_followup3_slurm_completion_record.md` records job `58021931`, `COMPLETED`, exit `0:0`, elapsed `00:18:38`, runtime seconds `1118`, log path, and runtime output path. `m7_followup3_runtime_reaggregation_report.md` records aggregation command `python scripts/evaluation/run_srr_v3_m7_followup3_completion_repair.py --job-id 58021931`, exit `0`, regenerated files, and no remaining monitor placeholders. |
| Live Slurm state agrees with the packet. | `SUPPORTED` | Reviewer `sacct -j 58021931 --format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End -P` returned `COMPLETED`, elapsed `00:18:38`, exit code `0:0`, start `2026-07-06T15:04:47`, end `2026-07-06T15:23:25`. |
| `followup2_training_adequacy.csv` no longer contains monitor placeholders. | `SUPPORTED` | It now has one completed row: `actual_optimizer_steps=3316`, `train_loop_seconds=900.2381211798638`, `validation_event_count=7`, `eval_cases=8`, `first_train_loss=2.702373504638672`, `last_train_loss=0.566109836101532`, and `adequacy_decision=PASS_MINIMUM_FOLLOWUP2_PROBE`. |
| The short runtime is contract-consistent for follow-up3. | `SUPPORTED_WITH_LIMITS` | The completed probe ran `00:18:38` wall-clock and records `900.238` train-loop seconds. This satisfies the follow-up2 minimum probe floor of 1200 optimizer steps and 900 train-loop seconds, but not the preferred 1800 seconds and not any imagined 8-hour budget. Follow-up3 is therefore adequate only for this repaired-evidence review, not for leaderboard readiness. |
| Loss and batch evidence were re-aggregated from runtime outputs. | `SUPPORTED_WITH_CAVEAT` | `followup2_loss_component_by_step.csv` has 888 rows; `followup2_batch_composition.csv` has 6634 rows with case IDs, split role, center, modality group, T2/C0 availability, GT positivity, remote-FP flags, no-T2 safety role, and training/gradient/validation usage fields. `followup2_loss_component_gradient_sanity.csv` has 26 rows, mostly `PASS`/`PASS_ZERO_JUSTIFIED`, with 2 `ZERO_GRAD_OR_DETACHED` rows; these are a residual mechanism-quality caveat but not a follow-up3 monitor-packet blocker. |
| Same-split MyoPS evidence was regenerated after the job. | `SUPPORTED_WITH_LIMITS` | `followup2_same_split_help_harm.csv` has 32 post-job rows for `m7_followup2_primary_repair`; `srr_source_path` points to runtime predictions under the follow-up2 primary repair output. These rows are formal-val, but the covered hard subgroup table is narrow: `followup2_hard_subgroup_metrics.csv` has only `all_cases`, `LGE-only`, `no_T2_empty_GT`, and `gt_positive_only`. This supports GPT inspection, not a route or leaderboard claim. |
| MyoPS mechanism evidence is no longer only pending placeholders. | `SUPPORTED_WITH_CAVEAT` | `arbitration_opening_diagnostics.csv` reports post-job runtime aggregation with `branch_correction_open_rate_mean=0.9054054054054054`, nonzero proposal/refiner weights, and `final_logit_delta_roi_abs_mean=1.3753634377105817`. `srr_contribution_by_case.csv` has 32 rows, but `anchor_delta_rate` remains `EVIDENCE_NOT_EXPORTED_PER_CASE`, so per-case contribution evidence is still incomplete. |
| Cine usable registration row triggered temporal dictionary execution. | `SUPPORTED` | `registration_same_subset_matrix.csv` has one `usable_for_temporal_dictionary=True` row for `heart_crop_SimpleITK_BSpline_or_Demons_tuned`. `temporal_dictionary_evidence.csv`, `temporal_dictionary_index.json`, `temporal_dictionary_case_summary.csv`, `temporal_aggregation_metrics.csv`, `frame0_vs_temporal_help_harm.csv`, `cine_metrics_summary.csv`, and `cine_temporal_dictionary_followup3_report.md` exist. |
| Temporal dictionary evidence is not merely frame0-only or descriptor-only. | `SUPPORTED_WITH_LIMITS` | The temporal row includes selected non-reference frame `9`, warped source `SimpleITK_Demons_warped_CineMA_segmentation_proxy`, registration quality, frame quality, motion saliency, temporal representer slot usage, aggregation output, local myocardium proxy, class-3 sanity, hosted caveat, and frame0 comparison. It is still diagnostic proxy evidence over one case, not hosted Cine metric evidence. |
| Follow-up3 strict validator is true fail-closed evidence. | `SUPPORTED` | `scripts/evaluation/validate_srr_v3_m7_followup3_packet.py` validates a packet path and exits nonzero on bad gates. `strict_validator_report.csv` has a good-packet exit `0` and eight mutated known-bad fixtures with actual exit code `1`, including monitor-ready, pending adequacy, submitted-only Slurm, completed-not-aggregated, usable-registration-without-temporal-dictionary, frame0-only temporal, diagnostic-hardcase formal decision, and ready-with-blocker cases. |
| The packet is ready for GPT next planning review. | `SUPPORTED_WITH_LIMITS` | The two follow-up3 blockers from the prior review are closed in tracked evidence: post-job reaggregation is present and Cine temporal dictionary was executed. Remaining scientific limitations are explicit and non-promotional. |

## Commands Run

```bash
env GIT_OPTIONAL_LOCKS=0 timeout 8 git status --short --branch
```

Result before writing this review:

```text
## main...origin/main [ahead 1]
```

```bash
sacct -j 58021931 --format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End -P
```

Result:

```text
58021931|M7FU2Probe|htzhulab|COMPLETED|00:18:38|0:0|2026-07-06T15:04:47|2026-07-06T15:23:25
58021931.batch|batch||COMPLETED|00:18:38|0:0|2026-07-06T15:04:47|2026-07-06T15:23:25
58021931.extern|extern||COMPLETED|00:18:38|0:0|2026-07-06T15:04:47|2026-07-06T15:23:25
```

```bash
python - <<'PY'
import csv, pathlib, collections
base=pathlib.Path('results/20260705_srr_v3_m7_training_and_cine_utilization')
for fn in [
 'followup2_training_adequacy.csv',
 'followup2_loss_component_by_step.csv',
 'followup2_loss_component_gradient_sanity.csv',
 'followup2_batch_composition.csv',
 'followup2_same_split_help_harm.csv',
 'followup2_hard_subgroup_metrics.csv',
 'srr_contribution_by_case.csv',
 'arbitration_opening_diagnostics.csv',
 'proposal_refiner_effectiveness.csv',
 'registration_same_subset_matrix.csv',
 'temporal_dictionary_evidence.csv',
 'strict_validator_report.csv',
]:
    rows=list(csv.DictReader((base/fn).open(newline='')))
    print(fn, len(rows), rows[0].keys() if rows else [])
PY
```

Reviewer parsing found completed post-job evidence rather than `PENDING_MONITOR` placeholders:

- `followup2_training_adequacy.csv`: 1 completed row, `PASS_MINIMUM_FOLLOWUP2_PROBE`.
- `followup2_loss_component_by_step.csv`: 888 rows.
- `followup2_loss_component_gradient_sanity.csv`: 26 rows; 18 `PASS`, 6 `PASS_ZERO_JUSTIFIED`, 2 `ZERO_GRAD_OR_DETACHED`.
- `followup2_batch_composition.csv`: 6634 rows.
- `followup2_same_split_help_harm.csv`: 32 rows.
- `followup2_hard_subgroup_metrics.csv`: 6 rows.
- `srr_contribution_by_case.csv`: 32 rows.
- `arbitration_opening_diagnostics.csv`: 1 post-job aggregate row.
- `proposal_refiner_effectiveness.csv`: 192 rows.
- `registration_same_subset_matrix.csv`: 4 rows, including 1 usable row.
- `temporal_dictionary_evidence.csv`: 1 executed row.
- `strict_validator_report.csv`: 9 rows, no failed fail-closed rows.

```bash
rg -n "PENDING_MONITOR|NEEDS_MONITOR|JOB_SUBMITTED|PENDING_PRIORITY|RUNNING|AWAITING_SACCT|TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED" \
  results/20260705_srr_v3_m7_training_and_cine_utilization/result.md \
  results/20260705_srr_v3_m7_training_and_cine_utilization/completion_check.md \
  results/20260705_srr_v3_m7_training_and_cine_utilization/review_request.md \
  results/20260705_srr_v3_m7_training_and_cine_utilization/followup2_*.csv \
  results/20260705_srr_v3_m7_training_and_cine_utilization/*followup3*.md \
  results/20260705_srr_v3_m7_training_and_cine_utilization/temporal_dictionary*
```

Result: no blocking monitor tokens in the ready decision files or regenerated follow-up2 CSVs. Historical submitted/pending commands remain in `commands_run.md`, but they are followed by completed `sacct` and aggregation `exit 0` entries, so they do not by themselves make the final packet a monitor packet.

## Residual Limits

This review does not say the method is leaderboard-ready. It only says follow-up3 repaired the two specific follow-up2 blockers well enough for GPT planner inspection.

Remaining limitations:

- Training ran for the minimum probe floor, not a long run. It is 3316 steps and about 900 train-loop seconds, not 8 hours.
- Hard subgroup evidence after repaired training is narrow; `followup2_hard_subgroup_metrics.csv` does not establish broad T2-present / CenterB / CenterC superiority.
- Per-case `anchor_delta_rate` is still not exported.
- Cine temporal dictionary evidence is one-case diagnostic proxy evidence with no hosted metric.
- No route promotion, validation upload, hosted metric claim, fold expansion, M8, scientific stop, leaderboard readiness, or challenge-ready status is authorized.

## Decision

decision: `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`

The tracked packet now contains completed Slurm reaggregation and Cine temporal dictionary execution. It passes the follow-up3 monitor-packet and temporal-dictionary repair gates. This decision only allows GPT to inspect the repaired evidence and decide what to plan next.

This decision does not authorize M8, route promotion, validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, leaderboard readiness, or challenge-ready status.
