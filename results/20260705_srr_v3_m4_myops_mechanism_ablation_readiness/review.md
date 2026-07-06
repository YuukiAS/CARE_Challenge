# Review 20260705 SRR-v3 M4 MyoPS Mechanism Ablation Readiness

task_key: `20260705_srr_v3_m4_myops_mechanism_ablation_readiness`
reviewed_task: `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md`
reviewed_result_dir: `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/`
reviewed_executor_commit: `cc48766 Add SRR v3 M4 mechanism ablation readiness`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M4_AUDITED_GO`

## Scope

This is a read-only review of the M4 executor packet. I did not modify model/training/evaluation code, did not generate missing executor artifacts, did not train, did not package or upload validation data, did not claim route promotion, and did not start any later milestone. This review writes only this `review.md`.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md`
- files under `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/`
- `scripts/evaluation/run_srr_v3_m4_mechanism_ablation.py`
- `jobs/src/run_srr_v3_m4_myops_mechanism_ablation.sh`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M3 prerequisite gate passed before M4. | `SUPPORTED` | `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md` contains `decision: M3_AUDITED_GO`. |
| Required M4 outputs are present and tracked. | `SUPPORTED` | `find results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness -type f` found only the expected first-level lightweight packet files plus this review after writing; before review, `test ! -e .../review.md` returned `REVIEW_ABSENT`. |
| Executor did not self-approve or start a later MyoPS milestone. | `SUPPORTED` | `completion_check.md` and `review_request.md` state later MyoPS milestones remain blocked until `M4_AUDITED_GO`; no `results/*srr_v3_m[5-9]*myops*` result directory was present before this review. |
| M4 covers the required ablation axes. | `SUPPORTED` | `ablation_config_table.csv` includes 8 bounded RUN rows: M3 trained, closed-gate identity, residual-zero/gate-measured, no nnU-Net anchor, deterministic prototypes, no prototype dictionary, no anatomy ROI prior, and no local refinement. It also includes semantic retrieval off and component proposal ranking off as `NOT_RUN_WITH_REASON`. |
| Training-objective ablations were not silently omitted. | `SUPPORTED` | `semantic_retrieval_off` and `component_proposal_ranking_off` are present in `ablation_config_table.csv` with `requires_new_training_checkpoint` reasons; this is consistent with the task instruction to mark rows not run as `NOT_RUN_WITH_REASON`. |
| Same-split nnU-Net help/harm evidence is complete for RUN rows. | `SUPPORTED` | CSV parsing found 192 rows in `same_split_help_harm.csv`: 24 rows per RUN ablation, covering 12 cases and two target metrics/classes. |
| Gate/residual/decode evidence is complete for RUN rows. | `SUPPORTED` | CSV parsing found 96 rows in `gate_residual_by_ablation.csv`: 12 rows per RUN ablation. `mechanism_decision.md` records M3 trained mean gate value `1.9009998316240246e-06`, while closed-gate identity Dice delta is `0.0`. |
| Prototype/dictionary diagnostics are present for RUN rows. | `SUPPORTED_WITH_CAVEAT` | CSV parsing found 96 rows in `prototype_dictionary_by_ablation.csv`: 12 rows per RUN ablation. Active checkpoint rows include prototype source, similarity means, dictionary diagnostics, and state-load fields. Closed-gate identity rows correctly report `not_applicable` prototype sources because that ablation bypasses model outputs and uses the nnU-Net anchor prediction. |
| Proposal/refinement evidence is complete for RUN rows. | `SUPPORTED` | CSV parsing found 192 rows in `proposal_refinement_by_ablation.csv`: 24 rows per RUN ablation, including proposal recall/precision, lesion-wise recall, component counts, remote FP counts, ROI, crop-mask, and residual fields. |
| Hard subgroup evidence is complete for RUN rows. | `SUPPORTED` | CSV parsing found 80 rows in `hard_subgroup_metrics_by_ablation.csv`: 10 rows per RUN ablation, covering all-cases, T2-present, no-T2, CenterC, and remote-FP-positive groups across scar and edema. |
| No-T2 edema safety is preserved. | `SUPPORTED` | Parsing `gate_residual_by_ablation.csv` found `0` rows with `no_t2_edema_voxels > 0`. |
| M4 identifies mechanism direction without using an undertrained smoke as a conclusion. | `SUPPORTED` | The packet uses the audited M3 6000-step checkpoint and bounded inference ablations. `mechanism_decision.md` distinguishes neutral closed-gate identity from harmful trained/no-anchor/prototype/refinement variants rather than treating a smoke run as mechanism proof. |
| M4 claims route promotion, validation packaging/upload, or challenge readiness. | `NOT_CLAIMED` | `mechanism_decision.md` states `route_promotion_decision: NO_PROMOTION`, `route_negative_decision: STOP_NOT_CLAIMED_BY_EXECUTOR`, and `scientific_resolution_status: SCIENTIFIC_UNRESOLVED_MECHANISM_ABLATION_READY`. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 1]` with an unrelated unstaged modification in `prompts/shared/EXECUTOR_PROMPTS.md`.

```bash
find results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness -type f | sort
```

Result: the M4 result packet contains only first-level Markdown/CSV evidence files; no checkpoints, NIfTI predictions, validation packages, uploads, or committed logs were present.

```bash
python - <<'PY'
import csv
from collections import Counter
base='results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness'
with open(f'{base}/ablation_config_table.csv', newline='') as f:
    cfg=list(csv.DictReader(f))
run=[r['ablation_id'] for r in cfg if r['status']=='RUN']
for name in ['same_split_help_harm','gate_residual_by_ablation','prototype_dictionary_by_ablation','proposal_refinement_by_ablation','hard_subgroup_metrics_by_ablation']:
    with open(f'{base}/{name}.csv', newline='') as f:
        rows=list(csv.DictReader(f))
    print(name, len(rows), dict(Counter(r['ablation_id'] for r in rows)))
PY
```

Result: the five evidence tables contain complete coverage for all 8 RUN ablations: `192`, `96`, `96`, `192`, and `80` rows respectively.

```bash
python - <<'PY'
import csv
base='results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness'
with open(f'{base}/gate_residual_by_ablation.csv', newline='') as f:
    rows=list(csv.DictReader(f))
bad=[r for r in rows if float(r.get('no_t2_edema_voxels') or 0)>0]
print(len(bad))
PY
```

Result: `0` no-T2 edema safety violations.

```bash
find results -maxdepth 1 -type d -name '*srr_v3_m[5-9]*myops*' -print | sort
```

Result: no later MyoPS milestone result directory was present before this review.

## Residual Caveat

M4 passes as a mechanism ablation readiness milestone, not as a successful SRR route. The evidence is negative or neutral relative to nnU-Net: M3 trained mean Dice delta is `-0.12502222426237394`, closed-gate identity is neutral at `0.0`, no-anchor is strongly harmful at `-0.31825760478682236`, and no-local-refinement remains harmful at `-0.1303016853605136`. This supports the executor's bounded attribution that current harm is not caused by identity fallback alone and that proposal/refinement/decode behavior remains weak or miscalibrated.

Because semantic retrieval off and component proposal ranking off require separately trained checkpoints, they are not resolved by this M4 packet. They are correctly listed as `NOT_RUN_WITH_REASON`, so this is not a blocker for M4, but it remains a limitation for any future mechanism revision plan.

## Decision

decision: `M4_AUDITED_GO`

M4 is approved as a completed mechanism ablation readiness milestone. This permits the user/GPT to start the next authorized milestone that depends on `review.md:M4_AUDITED_GO`, subject to normal handoff protocol and human push/visibility decisions.

This decision does not authorize route promotion, fold expansion, validation packaging, validation upload, hosted metric claims, scientific stop, formal new-checkpoint ablation conclusions for semantic retrieval/component ranking, or challenge readiness.
