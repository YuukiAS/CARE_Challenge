# MyoPS Proposal Progress

## 2026-06-28 Initial Implementation

- Loaded `AGENTS.md`, `prompts/AGENT_RULES.md`, Result5, the 20260628 task files, and 20260626 result evidence.
- Added an optional proposal head to `SRRMyoPSLite`.
- Added task-scoped proposal losses and metrics to `scripts/training/run_srr_myops_fold0.py`.
- Added aggregation support for `proposal_metrics.csv` and `prototype_usage.csv`.
- Added three Slurm wrappers under `jobs/src/`.
- Ran `unittest` SRR tests successfully: 8 tests passed.
- Ran a CPU proposal preflight successfully under ignored `results/20260628_myops_proposal/preflight/`.
- Ran a one-case export probe successfully; `proposal_metrics.csv` and `prototype_usage.csv` were written.

## Formal Jobs

| job_id | variant | partition | state at submission check |
| --- | --- | --- | --- |
| `56912267` | `proposal_pos_neg_basic` | `htzhulab` | `PD (Priority)` |
| `56912269` | `proposal_anatomy_distance` | `htzhulab` | `PD (Priority)` |
| `56912268` | `proposal_uncertainty_gate` | `htzhulab` | `PD (Priority)` |

No fallback partition was used because `htzhulab` had no clear long-wait evidence.

## 2026-06-28 Queue Follow-up

Latest checked state after completing the Cine registration secondary track:

| job_id | variant | partition | latest state |
| --- | --- | --- | --- |
| `56912267` | `proposal_pos_neg_basic` | `htzhulab` | `PD (Priority)` |
| `56912269` | `proposal_anatomy_distance` | `htzhulab` | `PD (Priority)` |
| `56912268` | `proposal_uncertainty_gate` | `htzhulab` | `PD (Priority)` |

No proposal selection can be made until at least one formal job produces fold0 validation/export metrics.

## 2026-06-28 PropPNF0 Running

`proposal_pos_neg_basic` started on `htzhulab`:

- job_id: `56912267`
- node: `g1807htzh01`
- log: `logs/PropPNF0_56912267_20260628_210159.log`
- observed runtime: `01:50:26` at `2026-06-28 22:52 EDT`
- remote process check: active Python training process using GPU0 at about `90.9 GiB / 95.8 GiB`, `100%` GPU utilization.
- latest observed artifact: `results/20260628_myops_proposal/variants/proposal_pos_neg_basic/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`

The log currently only contains wrapper startup lines; progress is being inferred from Slurm state, process/GPU utilization, and checkpoint mtime. The remaining formal variants are still queued on `htzhulab`.

## 2026-06-29 All Formal Jobs Running

At `2026-06-29 01:45 EDT`, all three formal proposal variants were running:

| job_id | variant | partition | state | runtime | node | log |
| --- | --- | --- | --- | --- | --- | --- |
| `56912267` | `proposal_pos_neg_basic` | `htzhulab` | `R` | `4:43:16` | `g1807htzh01` | `logs/PropPNF0_56912267_20260628_210159.log` |
| `56912268` | `proposal_uncertainty_gate` | `htzhulab` | `R` | `18:06` | `g1807htzh01` | `logs/PropUncF0_56912268_20260629_012709.log` |
| `56912269` | `proposal_anatomy_distance` | `htzhulab` | `R` | `8:22` | `g180702` | `logs/PropAnatF0_56912269_20260629_013654.log` |

The variant checkpoint directories exist under `results/20260628_myops_proposal/variants/`. Formal metrics/export/selection are still pending job completion.

## 2026-06-29 Uncertainty Job Repair

Original uncertainty-gated job `56912268` failed:

- Slurm state: `FAILED`
- Exit code: `1:0`
- Elapsed: `00:24:49`
- MaxRSS from batch step: about `4.8 GiB`, so this was not an obvious memory exhaustion failure.
- Log: `logs/PropUncF0_56912268_20260629_012709.log`
- Only observed formal artifact: `results/20260628_myops_proposal/variants/proposal_uncertainty_gate/checkpoints/fold_0/srr_fold0_config/checkpoint_best.pt`, size `0` bytes.

Repair applied:

- `scripts/training/run_srr_myops_fold0.py` now saves checkpoints via same-directory atomic temp file replacement and treats zero-byte `checkpoint_best.pt` as invalid.
- Proposal Slurm wrappers now invoke `python -u` so future traceback/log output is unbuffered.
- CPU uncertainty preflight passed under ignored `results/20260628_myops_proposal/preflight/uncertainty_debug/`, including non-empty `checkpoint_best.pt`, `checkpoint_final.pt`, `training_log.csv`, and summary files.

Resubmission:

- New uncertainty-gated formal job: `56942380`
- Initial state: `PD (None)` on `htzhulab`

## 2026-06-29 Pos-Neg Proposal Completed

`proposal_pos_neg_basic` job `56912267` completed successfully:

- Slurm state: `COMPLETED`
- Exit code: `0:0`
- Elapsed: `06:31:10`
- Summary: `results/20260628_myops_proposal/variants/proposal_pos_neg_basic/summary.md`
- Summary status: `budget_status=OK`, `stop_reason=max_runtime_seconds`, `best_step=105000`
- Exported full-volume predictions and wrote `subgroup_metrics.csv`, `component_hd_by_case.csv`, `proposal_metrics.csv`, `prototype_usage.csv`, `training_log.csv`, and checkpoints.

Initial readout is weak: all-case edema Dice `0.1768`, all-case scar Dice `0.1017`, with high component and remote-FP burden. Do not select or reject the proposal route from this single variant; wait for `proposal_anatomy_distance` and repaired `proposal_uncertainty_gate`, then run the aggregate report.
