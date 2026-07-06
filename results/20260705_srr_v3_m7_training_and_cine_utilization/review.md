# Review 20260705 SRR-v3 M7 Continued Repair

task_key: `20260705_srr_v3_m7_training_and_cine_utilization`
continued_task: `M7 reviewer-blocker repair`
reviewed_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
reviewed_executor_commit: `d049d68 Complete SRR v3 M7 continued repair packet`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M7_CONTINUED_AUDITED_NEEDS_REVISION`

## Scope

This is a read-only review of the M7 continued blocker-repair packet. I did not modify model/training/evaluation code, did not train, did not package or upload validation data, did not claim hosted metrics, did not promote a route, and did not start M8. This review overwrites the prior non-continued M7 `review.md` with the controlled M7 continued audit decision.

The continued packet is reviewed against the current `M7 reviewer (continued): blocker repair audit` contract in `prompts/shared/REVIEWER_PROMPTS.md`.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`, `M7 reviewer (continued): blocker repair audit`
- `prompts/shared/EXECUTOR_PROMPTS.md`, `M7 executor (continued): reviewer-blocker repair`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- prior M7 `review.md` content from this result directory before overwrite
- files under `results/20260705_srr_v3_m7_training_and_cine_utilization/`
- `scripts/evaluation/run_srr_v3_m7_continued_repair.py`
- `scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py`
- `scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M7 continued contract is present in shared prompts. | `SUPPORTED` | `prompts/shared/EXECUTOR_PROMPTS.md` contains `M7 executor (continued): reviewer-blocker repair`; `prompts/shared/REVIEWER_PROMPTS.md` contains this reviewer continued section. The standalone continued prompt file is not part of the active contract. |
| Executor did not claim route promotion, hosted metrics, validation packaging/upload, scientific stop, or M8. | `SUPPORTED` | `completion_check.md` sets `route_promotion_decision: NO_PROMOTION`, `hosted_metric_claim: false`, and `validation_packaging_or_upload: false`; `result.md` repeats the same boundary. |
| Loss gradient sanity was repaired relative to prior M7. | `SUPPORTED_WITH_REVIEW_LIMITS` | `loss_component_gradient_sanity.csv` has 107 rows: 93 `PASS`, 14 `PASS_ZERO_JUSTIFIED`, no `BACKWARD_FAILED`, no `EVIDENCE_NOT_FOUND`, and all rows have `requires_grad=True`. The audited batch includes `t2_present_batch_fraction=0.5`. |
| Loss graph training-validity report exists and addresses the prior detached-metric issue. | `SUPPORTED_WITH_REVIEW_LIMITS` | `loss_graph_training_validity_report.md` identifies `src/care_myocardium/losses/srr_losses.py::srr_m6_expanded_total_loss` through `scripts/training/run_srr_propref_myops_fold0.py::propref_loss`, states that optimizer backward used the graph-connected `total`, and states that the old failure came from detached logging metrics. I did not rerun training or gradient probes in this reviewer session. |
| Formal-val subgroup coverage is no longer all CenterA/LGE-only/no-T2. | `SUPPORTED` | `m7_case_pool_audit.csv` has 8 selected formal-val cases spanning CenterA, CenterB, CenterC; `same_split_help_harm.csv` has 192 formal-val rows with 120 CenterA, 48 CenterB, 24 CenterC, and 72 T2-present rows; `hard_subgroup_metrics.csv` includes `T2_present_complete`, `GT_positive_edema`, `GT_positive_scar`, `CenterB`, `CenterC`, `remote_FP_positive`, `small_lesion`, and `large_lesion`. |
| Diagnostic hardcases were excluded from formal best-variant decision. | `SUPPORTED` | `m7_case_pool_audit.csv` has `selected_for_diagnostic_hardcase=False` for all 220 rows; `same_split_help_harm.csv` rows are all `split_role=formal_val` and `eligible_for_best_variant_decision=True`; `best_variant_decision.md` states no diagnostic train hardcase rows are mixed into formal ranking. |
| Best-variant table avoids promotion. | `SUPPORTED` | `best_variant_decision_table.csv` has 12 rows and every row is `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`; scar Dice deltas range from about `-0.0028249` to `0.0012990`, edema Dice deltas from about `-0.0000805` to `0.0010844`. |
| Cine repair helper ran instead of only copying M5. | `SUPPORTED_WITH_BLOCKED_CINE_STATUS` | `cine_registration_repair_report.md` records 3 safe cases, 6 non-reference pairs, SimpleITK Demons, ANTsPy SyNOnly, and VoxelMorph availability/no-weights evidence. `registration_same_subset_matrix.csv` contains 6 SimpleITK rows, 6 ANTsPy rows, 6 frame0 control rows, and 1 VoxelMorph availability row. |
| Cine temporal dictionary remains correctly blocked because no usable non-reference registration row exists. | `SUPPORTED` | `registration_same_subset_matrix.csv` marks SimpleITK and ANTsPy rows `NOT_USABLE_FOR_TEMPORAL_DICTIONARY`; VoxelMorph is `NOT_USABLE_UNTRAINED_OR_NO_WEIGHTS`; `temporal_dictionary_evidence.csv` has only `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT`. |
| Registration evidence fully satisfies the reviewer row-field gate. | `NOT_SUPPORTED_BUT_NOT_PRIMARY_BLOCKER` | `registration_same_subset_matrix.csv` includes the main anatomy/HD95/NCC/displacement/Jacobian/runtime fields, but uses `m7_continued_decision` rather than the reviewer prompt's explicit `usable_for_temporal_dictionary` field. ANTsPy rows also lack displacement/Jacobian/registration-metric values. Because all non-reference rows are blocked and no temporal readiness is claimed, this is a documentation/field-compliance weakness rather than the strongest blocker. |
| Strict validator known-bad gate passes. | `NOT_SUPPORTED` | `strict_validator_report.csv` has only `known_bad_packet,expected_failure,actual_status,failure_reason`; it lacks actual exit code/status from running mutated known-bad packets. The source `scripts/evaluation/run_srr_v3_m7_continued_repair.py` lines 593-626 build `PASS_FAIL_CLOSED` from boolean checks on the current packet, not by creating bad packets and proving the validator rejects them. This violates the reviewer prompt's strict validator gate. |
| `completion_check.md` is acceptable as `M7_CONTINUED_READY_FOR_REVIEW`. | `NOT_SUPPORTED` | The strict validator gate remains unresolved. The prompt explicitly says to reject if `completion_check.md` claims ready while any continued blocker remains. |

## Commands Run

```bash
env GIT_OPTIONAL_LOCKS=0 timeout 8 git status --short --branch
```

Result before writing this review:

```text
## main...origin/main [ahead 3]
?? .tmp/
```

I did not touch the untracked `.tmp/` directory.

```bash
find results/20260705_srr_v3_m7_training_and_cine_utilization -maxdepth 2 -type f | sort
git ls-files results/20260705_srr_v3_m7_training_and_cine_utilization | sort
```

Result: the M7 continued lightweight packet files are present and tracked; local runtime lock/done files are not part of the tracked packet.

```bash
python - <<'PY'
import csv, pathlib, collections
base=pathlib.Path('results/20260705_srr_v3_m7_training_and_cine_utilization')
for fn in ['loss_component_gradient_sanity.csv','m7_case_pool_audit.csv','same_split_help_harm.csv','hard_subgroup_metrics.csv','best_variant_decision_table.csv','registration_same_subset_matrix.csv','temporal_dictionary_evidence.csv','strict_validator_report.csv']:
    rows=list(csv.DictReader((base/fn).open(newline='')))
    print(fn, len(rows), rows[0].keys() if rows else [])
PY
```

Reviewer parsing found:

- `loss_component_gradient_sanity.csv`: 107 rows; 93 `PASS`, 14 `PASS_ZERO_JUSTIFIED`; no `BACKWARD_FAILED` or `EVIDENCE_NOT_FOUND`.
- `m7_case_pool_audit.csv`: 220 rows; selected formal-val cases are `Case1002`, `Case1007`, `Case1009`, `Case1029`, `Case1042`, `Case2002`, `Case2007`, `Case3004`.
- `same_split_help_harm.csv`: 192 rows, all `formal_val`, all eligible for best-variant decision, covering CenterA/CenterB/CenterC and T2-present/T2-absent rows.
- `hard_subgroup_metrics.csv`: 1008 rows including the continued hard subgroup names.
- `best_variant_decision_table.csv`: 12 rows, all `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`.
- `registration_same_subset_matrix.csv`: 19 rows; no row is marked usable for temporal dictionary.
- `temporal_dictionary_evidence.csv`: one blocked row, no ready row.
- `strict_validator_report.csv`: 9 rows but no actual exit-code/status field.

```bash
nl -ba scripts/evaluation/run_srr_v3_m7_continued_repair.py | sed -n '576,632p'
nl -ba results/20260705_srr_v3_m7_training_and_cine_utilization/strict_validator_report.csv | sed -n '1,20p'
```

Result: `write_strict_validator_report()` reads the current packet and assigns `PASS_FAIL_CLOSED` when current-good conditions are true. It does not mutate a packet, invoke a validator, capture an exit code, or prove each named known-bad packet fails closed.

## Required Revision

M7 continued should not proceed as audited-go until the strict validator evidence is repaired.

Required executor repair:

1. Implement or invoke a real M7 continued validator that can be run against a packet directory and exits nonzero when a gate fails.
2. For each required known-bad case, create a temporary mutated packet or fixture that actually contains the bad condition:
   - all gradient rows `BACKWARD_FAILED`;
   - gradient sanity fixed but `loss_graph_training_validity_report.md` missing or insufficient;
   - hard subgroup rows all CenterA/LGE-only/no-T2;
   - diagnostic hardcase rows mixed into formal best-variant decision;
   - Cine branch copies M5 evidence without new registration attempt;
   - frame0-only or one-case SyN marked usable registration;
   - untrained VoxelMorph marked usable;
   - temporal dictionary marked ready despite no usable registration;
   - `completion_check.md` says ready while any continued blocker remains.
3. Re-run the validator on each known-bad packet and record expected failure, actual exit code/status, and failure reason in `strict_validator_report.md` and `strict_validator_report.csv`.
4. Keep the current no-promotion boundary: even after validator repair, `M7_CONTINUED_AUDITED_GO_FOR_NEXT_PLANNING` would only mean GPT planner review is allowed. It must not authorize M8, validation packaging/upload, hosted metric claims, fold expansion, challenge submission, route promotion, scientific stop, or leaderboard readiness.

Optional cleanup for the same repair pass:

- Add an explicit `usable_for_temporal_dictionary` field, or document why `m7_continued_decision` is the controlled substitute, in `registration_same_subset_matrix.csv`.
- Add clear failure reasons to blocked SimpleITK/ANTsPy non-reference rows instead of leaving `failure_reason` blank when the row is already `NOT_USABLE_FOR_TEMPORAL_DICTIONARY`.

## Decision

decision: `M7_CONTINUED_AUDITED_NEEDS_REVISION`

M7 continued made real progress on the prior MyoPS blockers: the gradient sanity table no longer fails wholesale, formal-val coverage is broader, diagnostic rows are separated from formal decision rows, and the best-variant decision remains non-promotional. Cine is also handled more honestly than before: a bounded repair was attempted and temporal dictionary readiness remains blocked.

The packet still fails the current reviewer contract because the strict validator gate is not real known-bad fail-closed evidence. It is a current-packet boolean checklist labeled as known-bad validation. Therefore this review cannot grant `M7_CONTINUED_AUDITED_GO_FOR_NEXT_PLANNING`.

This decision does not authorize route promotion, validation packaging/upload, hosted metric claims, fold expansion, challenge submission, M8, scientific stop, or leaderboard readiness.
