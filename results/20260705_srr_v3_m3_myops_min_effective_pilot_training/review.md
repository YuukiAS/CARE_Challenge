# Review 20260705 SRR-v3 M3 MyoPS Minimum-Effective Pilot Training

task_key: `20260705_srr_v3_m3_myops_min_effective_pilot_training`
reviewed_task: `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md`
reviewed_result_dir: `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/`
reviewed_executor_commit: `54ed52a Add SRR v3 M3 minimum effective pilot`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M3_AUDITED_GO`

## Scope

This is a read-only review of the M3 executor packet. I did not modify model/training/evaluation code, did not generate missing executor artifacts, did not train, did not package or upload validation data, did not claim route promotion, and did not start M4. This review writes only this `review.md`.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md`
- files under `results/20260705_srr_v3_m3_myops_min_effective_pilot_training/`
- `scripts/evaluation/aggregate_srr_v3_m3_pilot.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `jobs/src/run_srr_v3_m3_myops_min_effective_pilot.sh`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M2 prerequisite gate passed before M3. | `SUPPORTED` | `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md` contains `decision: M2_AUDITED_GO`. |
| Required M3 outputs are present and tracked. | `SUPPORTED` | `git ls-files results/20260705_srr_v3_m3_myops_min_effective_pilot_training` lists all task-required first-level Markdown/CSV/JSON outputs plus `commands_run.md` and `slurm_status.md`. |
| Executor did not self-approve or start M4. | `SUPPORTED` | `review_request.md` states M4 remains blocked until a separate reviewer writes `M3_AUDITED_GO`; `review.md` was absent before this review; `test ! -d results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness` exited `0`. |
| M3 was not a 6-step smoke or eval-only old checkpoint. | `SUPPORTED` | `summary.json`, `result.md`, and `adequacy_check.md` record `actual_optimizer_steps=6000`, `train_loop_seconds=2126.2185006489744`, `eval_cases=12`, and new checkpoint paths under the M3 variant directory. |
| Minimum effective training budget is met. | `SUPPORTED` | `adequacy_check.md` marks PASS for optimizer steps `6000 >= 1200`, train loop seconds `2126.2185006489744 >= 1800`, eval cases `12 >= 12`, one-batch overfit PASS, loss decrease `3.788084328174591`, and same-split help/harm present. |
| One-batch overfit passed. | `SUPPORTED` | `one_batch_overfit.json` records `status=PASS`, `steps=60`, first loss `3.621316909790039`, last loss `1.8979804515838623`, and loss decrease `1.7233364582061768`. |
| Training curve and validation events are present. | `SUPPORTED` | `training_curves.csv` has 142 lines, includes step `1` through `6000`, and `validation_events.csv` has 20 validation rows from step `300` through `6000`; best validation step is recorded in `summary.json` as `4800`. |
| Prediction sanity covers 12 eval cases and no-T2 edema safety. | `SUPPORTED` | CSV parsing of `prediction_sanity.csv` found 48 rows over 12 eval cases; no no-T2 row had nonzero `no_t2_edema_voxels`. |
| Gate/residual stats are exported. | `SUPPORTED` | `gate_residual_stats.csv` contains training-log gate/residual means and per-case decode deltas versus nnU-Net for scar and edema. The mean gate values are very small, but the required stats are present. |
| Prototype bank has T2-present edema coverage. | `SUPPORTED` | `prototype_bank_summary.json` records `edema_positive=5`, `edema_negative=23`, and `t2_present_edema_positive=16161`, with no no-T2 myocardium edema negatives. |
| Same-split nnU-Net help/harm is present. | `SUPPORTED` | `same_split_help_harm.csv` has 24 rows across 12 eval cases and two target classes, with nnU-Net source paths recorded. |
| Hard subgroup metrics are present. | `SUPPORTED` | `hard_subgroup_metrics.csv` reports all-cases, GT-positive/T2/no-T2/CenterC/remote-FP groups for `myops_edema` and `myops_scar`, including Dice, HD95, component, and remote-FP deltas. |
| M3 scientific outcome is favorable versus nnU-Net. | `NOT_SUPPORTED` | The pilot is adequate as evidence, but it is negative: all-cases Dice delta is `-0.13233380635489272` for edema and `-0.11771064216985518` for scar; only 1 same-split row has positive Dice delta while 17 have negative Dice delta. |
| M3 claims route promotion or challenge readiness. | `NOT_CLAIMED` | `result.md`, `pilot_training_config.md`, and `commands_run.md` state this is not full-fold training, not route promotion, not challenge readiness, and not validation packaging/upload. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 1]`.

```bash
git ls-files results/20260705_srr_v3_m3_myops_min_effective_pilot_training
```

Result: all prompt-required first-level M3 review packet files are tracked; nested checkpoints, NIfTI predictions, and bulky runtime artifacts are intentionally not part of the committed lightweight packet.

```bash
python - <<'PY'
import csv
from pathlib import Path
p=Path('results/20260705_srr_v3_m3_myops_min_effective_pilot_training/prediction_sanity.csv')
rows=list(csv.DictReader(p.open()))
bad=[r for r in rows if str(r['t2_present']).lower()!='true' and int(float(r['no_t2_edema_voxels']))!=0]
print(len(rows), len(bad), len({r['case_id'] for r in rows}))
PY
```

Result: `48` prediction rows, `0` no-T2 edema safety violations, `12` eval cases.

```bash
python - <<'PY'
import csv
from pathlib import Path
p=Path('results/20260705_srr_v3_m3_myops_min_effective_pilot_training/same_split_help_harm.csv')
rows=list(csv.DictReader(p.open()))
vals=[float(r['dice_delta']) for r in rows if r['dice_delta']]
print(len(rows), len({r['case_id'] for r in rows}), sum(v>0 for v in vals), sum(v<0 for v in vals), sum(vals))
PY
```

Result: `24` help/harm rows, `12` eval cases, `1` positive Dice-delta row, `17` negative Dice-delta rows, Dice-delta sum `-3.000533382296975`.

```bash
test ! -d results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness
```

Result: exit `0`; M4 result directory is absent.

## Residual Caveat

M3 passes as a minimum-effective pilot, not as a successful route. The pilot shows that the current SRR-v3 path can train under the required budget and produce auditable predictions/statistics, but same-split metrics are worse than nnU-Net on the controlled subset. Any next milestone should treat this as negative/harm evidence requiring mechanism ablation or revision, not as route promotion.

## Decision

decision: `M3_AUDITED_GO`

M3 is approved as a completed minimum-effective pilot milestone. This permits the user/GPT to start the next authorized milestone that depends on `review.md:M3_AUDITED_GO`, subject to normal handoff protocol and human push/visibility decisions.

This decision does not authorize route promotion, fold expansion, validation packaging, validation upload, hosted metric claims, scientific stop, formal training adequacy beyond this controlled M3 pilot, or challenge readiness.
