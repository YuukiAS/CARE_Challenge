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
- Added M9 aggregator, validator, validator self-test, and Slurm wrappers.

## Runtime State

Submitted Slurm jobs and routing race state:

- MyoPS M9 dictionary fidelity training A100 mirror: job `58297196`, partition `a100-gpu`, cancelled after htzhulab mirror started.
- MyoPS M9 dictionary fidelity training htzhulab mirror: job `58297510`, partition `htzhulab`, last observed state `RUNNING`.
- MyoPS M9 lesion/prototype memory isolated htzhulab job: job `58297807`, partition `htzhulab`, last observed state `RUNNING`.
- MyoPS M9 T2 edema recall focus isolated htzhulab job: job `58297806`, partition `htzhulab`, last observed state `RUNNING`.
- Cine M9 temporal final-output evidence A100 mirror: job `58297197`, partition `a100-gpu`, cancelled after htzhulab mirror completed.
- Cine M9 temporal final-output evidence htzhulab mirror: job `58297511`, partition `htzhulab`, completed with exit code `0:0`.

The MyoPS jobs have not completed, so M9 cannot be marked `M9_READY_FOR_REVIEW`.

Cine currently reports `M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING` because no local final-output Cine predictions were found under the inspected runtime directory.

## Verification Completed

- `python -m py_compile` passed for modified Python modules and new M9 scripts.
- Job shell syntax check passed with `bash -n`.
- CPU smoke proved M9 SRR-main model outputs `SRR_MAIN_NOT_ANCHOR_RESIDUAL` and `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`.
- Loss-weight smoke proved changing `loss_scar_refiner_small_roi` from `0` to `10` changed total loss and gradient norm.
- M9 validator self-test passed for one good fixture and all 29 required known-bad fixtures.
- Real-packet validator exits with `error_count=0` for this monitor packet after all required lightweight output files were populated with pending/evidence rows.
- All three formal M9 variants have early one-batch overfit `PASS` evidence and prototype bank summaries:
  - `m9_srr_main_true_br2_pattern_sip`: loss decrease `1.3056663274765015`.
  - `m9_srr_main_lesion_proposal_memory`: loss decrease `1.2432777881622314`.
  - `m9_srr_main_t2_edema_recall_focus`: loss decrease `1.3054085969924927`.
- Prototype summaries for all three early runs report non-empty scar/edema positive/negative counts and `edema_no_t2_myocardium_negative_voxels: 0`.

## Not Yet Completed

M9 formal training/evaluation, post-job runtime aggregation, real Cine final-output metrics, and replacement of pending/evidence rows with runtime-derived evidence remain incomplete.
