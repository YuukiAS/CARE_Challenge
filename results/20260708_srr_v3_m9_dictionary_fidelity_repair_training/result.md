# M9 SRR Dictionary Fidelity Repair + Cine Output Result

status: `M9_READY_FOR_REVIEW`

route_promotion_decision: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`

This is an executor/controller packet for one M9 milestone only. It does not claim route promotion. Explicit safety boundary: no validation upload, no hosted metric claim, no fold expansion, no M10.

## Prerequisite Gate

- M8 review token present: `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`
- M8 follow-up review token present: `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED`
- M8 follow-up repair state present: `NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND`
- M8 next action present: `GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR`

## Implemented Scope

- Added M9 formal SRR-main variants:
  - `m9_srr_main_true_br2_pattern_sip`
  - `m9_srr_main_lesion_proposal_memory`
  - `m9_srr_main_t2_edema_recall_focus`
- Added M9 model output mode token: `SRR_MAIN_NOT_ANCHOR_RESIDUAL`
- Added M9 nnU-Net role token: `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`
- Added diagram bootstrap evidence token: `SRR_DIAGRAM_BOOTSTRAP_EVIDENCE`
- Repaired expanded SRR loss-weight wiring so config/CLI weights reach `srr_m6_expanded_total_loss`.
- Added M9 loss keys and aliases for scar small-ROI refiner and edema large-ROI T2-present refiner.
- Added safe prototype memory helper that rejects no-T2 edema-negative updates.
- Added Cine final-output inspection entrypoint that fails closed when local final outputs are absent.
- Added a bounded M9 local Cine temporal final-output mode that reuses existing local CineMA frame-wise anatomy predictions, registers one descriptor-selected non-reference frame per safe case with ANTsPy SyNOnly, writes ignored runtime compact-label proxy outputs, and records lightweight local metrics for 12 safe train cases.
- Added M9 aggregator, validator, validator self-test, and Slurm wrappers.
- Expanded the M9 aggregator so post-job runtime aggregation populates training curves, validation events, gradient sanity, Pattern-SIP usage proxies, proposal/refiner rows, component/HD95/remote-FP rows, same-split help/harm against the tracked M8 nnU-Net anchor metrics, hard subgroup rows, and metric-aligned checkpoint selection.

## Runtime State

Submitted Slurm jobs and routing-race state:

- MyoPS M9 dictionary fidelity training A100 mirror: job `58297196`, partition `a100-gpu`, cancelled after the `htzhulab` mirror started.
- MyoPS M9 dictionary fidelity training htzhulab mirror: job `58297510`, partition `htzhulab`, completed with exit code `0:0`.
- MyoPS M9 lesion/prototype memory isolated htzhulab job: job `58297807`, partition `htzhulab`, completed with exit code `0:0`, elapsed `02:03:52`.
- MyoPS M9 T2 edema recall focus isolated htzhulab job: job `58297806`, partition `htzhulab`, completed with exit code `0:0`, elapsed `02:04:07`.
- MyoPS M9 true-BR2 top-up htzhulab job: job `58348646`, partition `htzhulab`, completed with exit code `0:0`, elapsed `02:03:33`; runtime output root `runtime_htzhulab_true_br2_pattern_sip`.
- Cine M9 temporal final-output evidence A100 mirror: job `58297197`, partition `a100-gpu`, cancelled after the `htzhulab` mirror completed.
- Cine M9 temporal final-output evidence htzhulab mirror: job `58297511`, partition `htzhulab`, completed with exit code `0:0`.

Final post-job aggregation was rerun after job `58348646` completed:

```bash
python scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_mirror \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_lesion_memory \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_t2_edema_focus \
  --runtime-root results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_htzhulab_true_br2_pattern_sip \
  --out-dir results/20260708_srr_v3_m9_dictionary_fidelity_repair_training
```

Aggregation exit status: `0`.

## MyoPS Training Adequacy

Current `m9_training_budget_ledger.csv` contains six formal runtime rows.

- Aggregate formal train-loop seconds: `26415.268`.
- Formal SRR-main candidates with `>=7200` train-loop seconds: `3`.
- The alternate M9 hard gate is satisfied by three formal SRR-main candidates with `>=7200` train-loop seconds each plus completed control/runtime eval evidence, even though aggregate formal train-loop seconds remain below `28800`.
- `m9_srr_main_lesion_proposal_memory` isolated run: `29575` optimizer steps, `7200.120` train-loop seconds, `20` validation events.
- `m9_srr_main_t2_edema_recall_focus` isolated run: `26321` optimizer steps, `7200.065` train-loop seconds, `20` validation events.
- `m9_srr_main_true_br2_pattern_sip` top-up run: `26233` optimizer steps, `7200.081` train-loop seconds, `20` validation events.

## Metric Outcome

`m9_metric_aligned_checkpoint_selection.csv` selected metric-facing rows after final post-job aggregation. All selected formal candidates remain negative against the tracked M8 nnU-Net anchor:

- `m9_srr_main_true_br2_pattern_sip`: selected `checkpoint_best` / `pathology_aware`, mean Dice delta `-0.0419089071946592`, mean HD95 delta `14.723931326384324`, mean remote-FP delta `2.28125`.
- `m9_srr_main_lesion_proposal_memory`: selected `checkpoint_best` / `pathology_aware`, mean Dice delta `-0.055947265941412486`, mean HD95 delta `14.009386143746562`, mean remote-FP delta `1.7604166666666667`.
- `m9_srr_main_t2_edema_recall_focus`: selected `checkpoint_best` / `pathology_aware`, mean Dice delta `-0.06009304704870019`, mean HD95 delta `21.32252454340387`, mean remote-FP delta `6.614583333333333`.

Selected paired per-class Dice:

- `m9_srr_main_true_br2_pattern_sip`: scar `0.568263` vs anchor `0.587634` (`-0.019371`); edema `0.646942` vs anchor `0.711389` (`-0.064447`).
- `m9_srr_main_lesion_proposal_memory`: scar `0.529388` vs anchor `0.587634` (`-0.058247`); edema `0.657741` vs anchor `0.711389` (`-0.053648`).
- `m9_srr_main_t2_edema_recall_focus`: scar `0.546225` vs anchor `0.587634` (`-0.041409`); edema `0.632612` vs anchor `0.711389` (`-0.078777`).

These metrics do not support route promotion. M9 is ready for independent review as a completed negative/diagnostic milestone, not as a deployable SRR route.

## Cine Evidence

Cine local temporal final-output evidence is present:

- status: `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`
- local safe train cases: `12`
- non-reference frames used: `12`
- registration method: `ANTsPy_SyNOnly`
- runtime prediction directory: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_m9_cine_temporal_output/predictions`
- mean local Dice delta vs frame0: class_1 `0.017473`, class_2 `0.294540`, class_3 `-0.011230`

This is local proxy final-output evidence only. It does not claim hosted `myocardium_cinemyops` performance or route readiness.

## Verification Completed

- `python -m py_compile` passed for modified Python modules and new M9 scripts.
- Job shell syntax check passed with `bash -n`.
- CPU smoke proved M9 SRR-main model outputs `SRR_MAIN_NOT_ANCHOR_RESIDUAL` and `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`.
- Loss-weight smoke proved changing `loss_scar_refiner_small_roi` from `0` to `10` changed total loss and gradient norm.
- Final M9 validator self-test passed for one good fixture and all 29 required known-bad fixtures.
- Final real-packet validator exited with `error_count=0`.
- `git diff --check` passed after final packet updates.

## Current Executor Decision

M9 is `M9_READY_FOR_REVIEW` for a separate read-only reviewer. The executor decision is `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`. Explicit safety boundary: no validation upload, no hosted metric claim, no fold expansion, no M10.
