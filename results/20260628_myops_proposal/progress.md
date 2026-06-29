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
