# M9 Follow-up Completion Check

status: `M9_FOLLOWUP_READY_FOR_REAUDIT`

route_promotion_decision: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`

This follow-up reconciles the prior reviewer blocker class `evidence_state_and_validator_consistency`. It is ready for independent read-only re-audit. It is not an audited decision. Explicit safety boundary: no validation upload, no hosted metric claim, no fold expansion, no M10.

## Slurm Terminal Accounting

- `58297196` `M9SRRDict` on `a100-gpu`: cancelled after the `htzhulab` mirror started.
- `58297510` `M9SRRDict` on `htzhulab`: completed with exit code `0:0`.
- `58297807` `M9SRRDict` lesion/prototype memory isolated run on `htzhulab`: completed with exit code `0:0`, elapsed `02:03:52`.
- `58297806` `M9SRRDict` T2 edema focus isolated run on `htzhulab`: completed with exit code `0:0`, elapsed `02:04:07`.
- `58348646` `M9SRRDict` true-BR2 top-up isolated run on `htzhulab`: completed with exit code `0:0`, elapsed `02:03:33`.
- `58297197` `M9CineOut` on `a100-gpu`: cancelled after the `htzhulab` Cine mirror completed.
- `58297511` `M9CineOut` on `htzhulab`: completed with exit code `0:0`.

## Post-Job Aggregation

Final aggregation command:

```bash
python scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_mirror \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_lesion_memory \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_t2_edema_focus \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_true_br2_pattern_sip \
  --out-dir results/20260708_srr_v3_m9_dictionary_fidelity_repair_training
```

Aggregation exit status: `0`.

Updated tracked evidence includes `m9_training_budget_ledger.csv`, `m9_metric_aligned_checkpoint_selection.csv`, `m9_training_curves.csv`, `m9_validation_events.csv`, `m9_same_split_help_harm.csv`, `m9_hard_subgroup_metrics.csv`, `m9_component_remote_fp_hd95_report.csv`, `m9_proposal_refiner_recall_precision.csv`, `m9_refiner_causal_effect.csv`, and `m9_ablation_matrix.csv`.

## Training Adequacy

- Aggregated formal training-budget rows: `6`.
- Aggregate train-loop seconds: `26415.268`, below the aggregate `28800` second gate.
- Formal SRR-main candidates with `>=7200` train-loop seconds: `3`, satisfying the alternate M9 hard gate.
- `m9_srr_main_lesion_proposal_memory` isolated run: `29575` optimizer steps, `7200.120` train-loop seconds, `20` validation events.
- `m9_srr_main_t2_edema_recall_focus` isolated run: `26321` optimizer steps, `7200.065` train-loop seconds, `20` validation events.
- `m9_srr_main_true_br2_pattern_sip` top-up run: `26233` optimizer steps, `7200.081` train-loop seconds, `20` validation events.

## Metric-Facing Outcome

Selected checkpoint rows in `m9_metric_aligned_checkpoint_selection.csv` remain negative against the tracked M8 nnU-Net anchor:

- `m9_srr_main_true_br2_pattern_sip`: selected `checkpoint_best` / `pathology_aware`, mean Dice delta `-0.0419089071946592`, mean HD95 delta `14.723931326384324`, mean remote-FP delta `2.28125`.
- `m9_srr_main_lesion_proposal_memory`: selected `checkpoint_best` / `pathology_aware`, mean Dice delta `-0.055947265941412486`, mean HD95 delta `14.009386143746562`, mean remote-FP delta `1.7604166666666667`.
- `m9_srr_main_t2_edema_recall_focus`: selected `checkpoint_best` / `pathology_aware`, mean Dice delta `-0.06009304704870019`, mean HD95 delta `21.32252454340387`, mean remote-FP delta `6.614583333333333`.

Per-class selected paired Dice evidence:

- `m9_srr_main_true_br2_pattern_sip`: scar `0.568263` vs anchor `0.587634` (`-0.019371`); edema `0.646942` vs anchor `0.711389` (`-0.064447`).
- `m9_srr_main_lesion_proposal_memory`: scar `0.529388` vs anchor `0.587634` (`-0.058247`); edema `0.657741` vs anchor `0.711389` (`-0.053648`).
- `m9_srr_main_t2_edema_recall_focus`: scar `0.546225` vs anchor `0.587634` (`-0.041409`); edema `0.632612` vs anchor `0.711389` (`-0.078777`).

## Cine Evidence

Cine local temporal final-output evidence is present:

- status: `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`
- local safe train cases: `12`
- non-reference frames used: `12`
- registration method: `ANTsPy_SyNOnly`
- runtime prediction directory: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_m9_cine_temporal_output/predictions`

This is local proxy final-output evidence only. It does not claim hosted `myocardium_cinemyops` performance or route readiness.

## Follow-up Evidence Reconciliation

- `m9_dictionary_fidelity_matrix.csv` now records runtime-derived evidence paths for true-BR2 slot usage, invalid-slot mask runtime, and final metric causal effect.
- `m9_code_patch_summary.md`, `m9_rrl_brr2_adaptation_contract.md`, `m9_nnunet_role_audit.md`, and `m9_pathology_specific_refiner_contract.md` now describe the final post-job aggregation evidence instead of stale intermediate states.
- `m9_prototype_memory_summary.json` now carries a reconciled train/OOF runtime prototype-memory status while preserving the non-empty scar/edema counts and no-T2 safety counts.
- `m9_followup_stale_status_scan.csv` records Markdown, CSV, and JSON stale-status scanning.

## Verification

- M9 validator self-test passed one good fixture and all 37 known-bad fixtures, including the eight follow-up stale-state fixtures.
- Final real-packet validator exited with `error_count=0`.
- `git diff --check` passed.

## Completion Decision

M9 follow-up is ready for independent reviewer re-audit as a reconciled negative/diagnostic packet. The executor decision remains `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`; the next planner action remains `GPT_REPLAN_AFTER_M9_NO_PROMOTION` unless a separate reviewer decides otherwise.
