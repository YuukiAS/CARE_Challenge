# Review 20260705 SRR-v3 M7 Training and Cine Utilization

task_key: `20260705_srr_v3_m7_training_and_cine_utilization`
reviewed_result_dir: `results/20260705_srr_v3_m7_training_and_cine_utilization/`
reviewed_executor_commit: `8cb619e Complete SRR v3 M7 training and Cine diagnostic packet`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M7_AUDITED_NEEDS_REVISION`

## Scope

This is a read-only review of the M7 executor packet. I did not modify model/training/evaluation code, did not train, did not package or upload validation data, did not claim route promotion, and did not start any later milestone. This review writes only this `review.md`.

M7 is reviewed as two linked but separate lines: MyoPS training/help-harm evidence, and Cine secondary diagnostic utilization. The Cine gap is real. The packet mostly preserves that gap honestly, but the MyoPS packet has hard evidence failures that prevent audited-go.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`, M7 executor section
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md`
- `results/20260705_srr_v3_m5_cine_secondary_contract/review.md`
- files under `results/20260705_srr_v3_m7_training_and_cine_utilization/`
- `jobs/src/run_srr_v3_m7_myops_training.sh`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M6 prerequisite gate is satisfied. | `SUPPORTED` | `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` contains `decision: M6_AUDITED_GO`. |
| M5 Cine prerequisite is satisfied for a diagnostic Cine subline. | `SUPPORTED_WITH_LIMITS` | `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` contains `decision: M5_AUDITED_DIAGNOSTIC_GO`, but that review explicitly preserved `CINE_REGISTRATION_GAP_REMAINS` and `TEMPORAL_DICTIONARY_NOT_READY`. |
| M7 did not self-approve or start M8. | `SUPPORTED` | No `review.md` existed in the M7 packet before this review. `result.md` and `completion_check.md` state no M8, validation package/upload, hosted metric claim, or route promotion. |
| Required M7 lightweight result files are tracked. | `SUPPORTED` | `git ls-files results/20260705_srr_v3_m7_training_and_cine_utilization` lists the first-level M7 packet files, including MyoPS evidence, Cine reports, and this review after writing. Runtime subdirectories are local evidence and are not part of the tracked lightweight packet. |
| Three required MyoPS variants were included. | `SUPPORTED` | `variant_matrix.csv` contains `m7_full_srr_context_arbitration`, `m7_conservative_component_arbitration`, and `m7_scar_precision_edema_safe`, all marked required. |
| Training duration and optimizer-step adequacy are present. | `SUPPORTED` | `training_adequacy_by_variant.csv` has 3 `PASS` rows: 12382, 17660, and 14029 optimizer steps; each has `train_loop_seconds` just over 1800 seconds, 20 validation events, and 12 eval cases. |
| One-batch overfit evidence is present. | `SUPPORTED` | `one_batch_overfit_by_variant.csv` has 3 `PASS` rows with 40 steps and decreasing losses for all required variants. |
| Same-split nnU-Net help/harm evidence exists. | `SUPPORTED_WITH_CAVEAT` | `same_split_help_harm.csv` has 288 rows across 3 variants, 12 cases, best/final checkpoints, argmax/pathology-aware decode, and scar/edema metrics. However, all rows are `CenterA`, `LGE-only`, and `t2_present=False`, limiting subgroup conclusions. |
| Hard subgroup coverage satisfies M7 prompt. | `NOT_SUPPORTED` | `hard_subgroup_metrics.csv` only includes groups `all_cases`, `LGE-only`, `no_T2_empty_GT`, and `gt_positive_only`. The M7 prompt required hard subgroup coverage including T2-present, GT-positive, no-T2 empty-GT, CenterB/CenterC, remote-FP-positive, small-lesion, and large-lesion. CenterB/CenterC and T2-present evidence are absent from the M7 evaluation rows reviewed. |
| Loss component curves exist. | `SUPPORTED` | `loss_component_by_step.csv` has 11050 rows covering required M7 loss components, and no audited component is all-zero across the packet. |
| Loss component gradient sanity passes. | `NOT_SUPPORTED` | `loss_component_gradient_sanity.csv` has 75 rows and all 75 are `BACKWARD_FAILED:RuntimeError` with `grad_l2_norm=EVIDENCE_NOT_FOUND` and `param_with_grad_count=0`. This is a hard M7 gate failure, not merely a low-signal finding. |
| No-T2 edema safety is preserved in the evaluated cases. | `SUPPORTED` | `no_t2_safety_by_variant.csv` has 144 rows and reviewer parsing found max `no_t2_edema_voxels=0`. This is limited to the evaluated no-T2/LGE-only cases. |
| Metric-table decision avoids route promotion. | `SUPPORTED` | `best_variant_decision.md` and `best_variant_decision_table.csv` assign every variant/checkpoint/decode row `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`; max scar Dice delta is small (`0.006052879325744249`) and edema Dice delta is always `0.0`. |
| CineMA usage has enough evidence to count as completed Cine registration/temporal dictionary. | `NOT_SUPPORTED` | `cinema_usage_report.md`, `registration_same_subset_matrix.csv`, and `temporal_dictionary_evidence.csv` all preserve `CINE_REGISTRATION_GAP_REMAINS` and `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`. No qualified non-reference registration option exists. |
| Cine gap is honestly blocked rather than falsely promoted. | `SUPPORTED_WITH_CAVEAT` | The matrix correctly marks frame0 control, one-case SyN smoke, untrained VoxelMorph, SimpleITK/Demons fallback with Jacobian concerns, and optical-flow proxy as `NOT_USABLE_FOR_TEMPORAL_DICTIONARY`. This is honest, but it means M7 did not materially close the Cine registration/temporal dictionary gap. |
| `completion_check.md` is valid as `M7_READY_FOR_REVIEW`. | `NOT_SUPPORTED` | The packet claims `experiment_adequacy_decision: PASS`, but gradient sanity entirely failed and hard subgroup coverage is incomplete. Under the M7 prompt, these are blockers for a ready packet. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 8]`.

```bash
find results/20260705_srr_v3_m7_training_and_cine_utilization -maxdepth 3 -type f | sort
git ls-files results/20260705_srr_v3_m7_training_and_cine_utilization | sort
```

Result: M7 packet files are present and tracked; local runtime subdirectories exist but are not tracked as lightweight packet files.

```bash
python - <<'PY'
import csv, pathlib, collections
base=pathlib.Path('results/20260705_srr_v3_m7_training_and_cine_utilization')
for fn,key in [('hard_subgroup_metrics.csv','group'),('same_split_help_harm.csv','center'),('same_split_help_harm.csv','modality_group'),('same_split_help_harm.csv','t2_present')]:
    rows=list(csv.DictReader((base/fn).open(newline='')))
    print(fn,key,collections.Counter(r.get(key,'') for r in rows).most_common())
rows=list(csv.DictReader((base/'loss_component_gradient_sanity.csv').open(newline='')))
print('gradient status', collections.Counter(r['status'] for r in rows))
print('gradient param counts', collections.Counter(r['param_with_grad_count'] for r in rows).most_common())
rows=list(csv.DictReader((base/'training_adequacy_by_variant.csv').open(newline='')))
print('adequacy', [(r['variant'], r['optimizer_steps'], r['train_loop_seconds'], r['validation_event_count'], r['eval_case_count'], r['decision']) for r in rows])
rows=list(csv.DictReader((base/'best_variant_decision_table.csv').open(newline='')))
print('best max scar delta', max(float(r['scar_dice_delta_mean']) for r in rows))
print('any edema nonzero delta', any(float(r['edema_dice_delta_mean']) != 0 for r in rows))
rows=list(csv.DictReader((base/'no_t2_safety_by_variant.csv').open(newline='')))
print('no_t2 max edema voxels', max(int(float(r.get('no_t2_edema_voxels') or 0)) for r in rows))
PY
```

Result:

- hard subgroup groups are only `all_cases`, `LGE-only`, `no_T2_empty_GT`, and `gt_positive_only`.
- same-split evidence is all `CenterA`, all `LGE-only`, and all `t2_present=False`.
- gradient sanity status is 75 `BACKWARD_FAILED:RuntimeError` rows with `param_with_grad_count=0`.
- training adequacy rows pass nominal duration/step gates.
- best scar Dice delta is `0.006052879325744249`, no edema row has nonzero Dice delta, and no-T2 edema voxels remain `0`.

```bash
rg -n "M7|validation package|validation packaging|upload|hosted|route promotion|full fold|full-fold|checkpoint|NIfTI|nii.gz|TEMPORAL_DICTIONARY|CINE_REGISTRATION" results/20260705_srr_v3_m7_training_and_cine_utilization
```

Result: relevant matches are boundary statements, no-promotion decisions, Cine blocker statements, and local checkpoint/source path references inside evidence tables; no validation package/upload or hosted metric claim was found.

## Required Revision

M7 should not proceed as audited-go until the executor fixes the evidence packet and, if needed, the training/evaluation code:

1. Fix `loss_component_gradient_sanity.csv` so required loss components have valid backward evidence, nonzero gradients where applicable, and explicit legitimate N/A explanations where truly mask-gated. A packet with 75/75 `BACKWARD_FAILED:RuntimeError` rows cannot be `M7_READY_FOR_REVIEW`.
2. Repair hard subgroup coverage or explicitly downgrade completion. The prompt required T2-present, GT-positive, no-T2 empty-GT, CenterB/CenterC, remote-FP-positive, small-lesion, and large-lesion evidence. Current same-split evidence is all CenterA/LGE-only/no-T2.
3. Keep the Cine status strict. `CINE_REGISTRATION_GAP_REMAINS` and `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP` are the correct current conclusion unless a real same-safe-subset non-reference registration option is added with acceptable plausibility evidence.
4. Revise `completion_check.md` and `review_request.md` to stop claiming a fully ready M7 packet while these hard blockers remain, or rerun/aggregate enough evidence to close them.

## Decision

decision: `M7_AUDITED_NEEDS_REVISION`

M7 contains useful training-duration evidence and correctly avoids route promotion. It also correctly refuses to turn the existing Cine gap into a completed temporal dictionary. However, the all-failed gradient sanity table and incomplete hard subgroup coverage violate M7 readiness gates. The packet is not acceptable for `M7_AUDITED_GO_FOR_NEXT_PLANNING`, and it also should not be treated as a final route-negative scientific stop.

This decision does not authorize route promotion, validation packaging/upload, hosted metric claims, fold expansion, challenge submission, scientific stop, or any downstream milestone.
