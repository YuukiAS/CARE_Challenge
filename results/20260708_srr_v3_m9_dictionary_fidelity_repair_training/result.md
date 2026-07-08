# M9 SRR Dictionary Fidelity Repair + Cine Output Result

status: `M9_NEEDS_MONITOR`

This is an executor/controller monitor packet for M9. It is not review-ready and does not claim route promotion, validation packaging, validation upload, hosted metrics, leaderboard readiness, fold expansion, scientific stop, or M10.

## Prerequisite Gate

- M8 review token present: `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`
- M8 follow-up review token present: `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED`
- M8 follow-up repair state present: `NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND`
- M8 next action present: `GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR`

## Completed This Pass

- Added M9 formal SRR-main variants:
  - `m9_srr_main_true_br2_pattern_sip`
  - `m9_srr_main_lesion_proposal_memory`
  - `m9_srr_main_t2_edema_recall_focus`
- Added M9 model output mode token: `SRR_MAIN_NOT_ANCHOR_RESIDUAL`
- Added M9 nnU-Net role token: `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`
- Repaired expanded SRR loss-weight wiring so config/CLI weights reach `srr_m6_expanded_total_loss`.
- Added M9 loss keys and aliases for scar small-ROI refiner and edema large-ROI T2-present refiner.
- Added safe prototype memory helper that rejects no-T2 edema-negative updates.
- Added Cine final-output inspection entrypoint that fails closed when local final outputs are absent.
- Added a bounded M9 local Cine temporal final-output mode that reuses existing local CineMA frame-wise anatomy predictions, registers one descriptor-selected non-reference frame per safe case with ANTsPy SyNOnly, writes ignored runtime compact-label proxy outputs, and records lightweight local metrics for 12 safe train cases.
- Added M9 aggregator, validator, validator self-test, and Slurm wrappers.
- Expanded the M9 aggregator so post-job runtime aggregation can populate training curves, validation events, gradient sanity, Pattern-SIP usage proxies, proposal/refiner rows, component/HD95/remote-FP rows, same-split help/harm against the tracked M8 nnU-Net anchor metrics, hard subgroup rows, and metric-aligned checkpoint selection.

## Runtime State

Submitted Slurm jobs and routing race state:

- MyoPS M9 dictionary fidelity training A100 mirror: job `58297196`, partition `a100-gpu`, cancelled after htzhulab mirror started.
- MyoPS M9 dictionary fidelity training htzhulab mirror: job `58297510`, partition `htzhulab`, last observed state `RUNNING`.
- MyoPS M9 lesion/prototype memory isolated htzhulab job: job `58297807`, partition `htzhulab`, last observed state `RUNNING`.
- MyoPS M9 T2 edema recall focus isolated htzhulab job: job `58297806`, partition `htzhulab`, last observed state `RUNNING`.
- Cine M9 temporal final-output evidence A100 mirror: job `58297197`, partition `a100-gpu`, cancelled after htzhulab mirror completed.
- Cine M9 temporal final-output evidence htzhulab mirror: job `58297511`, partition `htzhulab`, completed with exit code `0:0`.

The MyoPS jobs have not completed, so M9 cannot be marked `M9_READY_FOR_REVIEW`.

Partial MyoPS formal aggregation is now present for two completed formal variant outputs:

- candidate: `m9_srr_main_true_br2_pattern_sip`
- optimizer steps: `6000`
- validation events: `20`
- train loop seconds: `1660.097`
- selected runtime checkpoint row: `checkpoint_best` / `pathology_aware`
- same-split mean Dice delta vs tracked M8 nnU-Net anchor control:
  - `myops_scar`: `-0.009682347345035466`
  - `myops_edema`: `-0.076883272409283`
- candidate: `m9_srr_main_lesion_proposal_memory`
- optimizer steps: `6000`
- train loop seconds: `1499.562`
- selected runtime checkpoint row: `checkpoint_final` / `pathology_aware`
- same-split mean Dice delta vs tracked M8 nnU-Net anchor control:
  - `myops_scar`: `-0.03627368193360481`
  - `myops_edema`: `-0.07598376935449123`

This is useful runtime evidence but not completion. The aggregate formal train-loop seconds currently total `3159.659`, below the M9 training-budget requirement, and neither aggregated formal candidate beats the same-split anchor.

Cine local temporal final-output evidence is now present:

- status: `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`
- local safe train cases: `12`
- non-reference frames used: `12`
- registration method: `ANTsPy_SyNOnly`
- runtime prediction directory: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/runtime_m9_cine_temporal_output/predictions`

This is local proxy final-output evidence only. It does not claim hosted `myocardium_cinemyops` performance or route readiness.

## Verification Completed

- `python -m py_compile` passed for modified Python modules and new M9 scripts.
- Job shell syntax check passed with `bash -n`.
- CPU smoke proved M9 SRR-main model outputs `SRR_MAIN_NOT_ANCHOR_RESIDUAL` and `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`.
- Loss-weight smoke proved changing `loss_scar_refiner_small_roi` from `0` to `10` changed total loss and gradient norm.
- M9 validator self-test passed for one good fixture and all 29 required known-bad fixtures.
- Real-packet validator exits with `error_count=0` for this monitor packet after all required lightweight output files were populated with pending/evidence rows.
- Aggregator smoke test wrote a separate `/tmp/m9_aggregator_smoke` packet successfully without modifying the real M9 packet while formal jobs are still running.
- M9 Cine local temporal output run completed with `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`, wrote 12 ignored runtime NIfTI predictions, and updated the required M9 Cine manifest/QC/registration/temporal-dictionary/metrics/help-harm/failure files.
- Post-job partial aggregation was run after `m9_srr_main_true_br2_pattern_sip` wrote formal runtime outputs. It updated MyoPS training curves, validation events, Pattern-SIP summaries, component/HD95/remote-FP rows, same-split help/harm, hard-subgroup rows, proposal/refiner rows, and metric-aligned checkpoint selection. Pattern-SIP raw retrieval rows were summarized into lightweight group-level tables rather than publishing the full raw `retrieval_usage.csv`.
- A second partial aggregation was run after `m9_srr_main_lesion_proposal_memory` wrote formal runtime outputs under `runtime_htzhulab_mirror`. It updated the lightweight MyoPS runtime-derived CSV files and preserved `M9_NEEDS_MONITOR` because `m9_srr_main_t2_edema_recall_focus` is not yet aggregated as formal evidence and the training-budget gate is still unmet.
- All three formal M9 variants have early one-batch overfit `PASS` evidence and prototype bank summaries:
  - `m9_srr_main_true_br2_pattern_sip`: loss decrease `1.3056663274765015`.
  - `m9_srr_main_lesion_proposal_memory`: loss decrease `1.2432777881622314`.
  - `m9_srr_main_t2_edema_recall_focus`: loss decrease `1.3054085969924927`.
- Prototype summaries for all three early runs report non-empty scar/edema positive/negative counts and `edema_no_t2_myocardium_negative_voxels: 0`.

## Not Yet Completed

M9 formal MyoPS training/evaluation remains incomplete for the remaining required formal SRR-main candidate `m9_srr_main_t2_edema_recall_focus`, and the aggregate training budget is still below the M9 prompt threshold. Cine has local final-output proxy evidence, but it is not hosted/challenge evidence and does not make the overall packet review-ready while MyoPS jobs are still running.
