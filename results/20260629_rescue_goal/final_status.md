# 20260629 Rescue Goal Final Status

status: `STOP_NO_ROUTE_BEATS_BASELINE_SIGNAL`
cine_status: `CINE_REFERENCE_ONLY`

## Decision

All required MyoPS and Cine routes were executed and audited. No repaired
proposal, SRR-v2, cascade teacher, or follow-up SRR-v2 improvement route reached
the conservative nnU-Net-relative selection gate. The current goal therefore
stops without selecting a custom route for fold expansion or validation
packaging.

The best first-party MyoPS signal remains diagnostic only:

- Best scar all-case: `srr_v2_capacity12_hardneg`, Dice `0.3090`.
- Best edema GT-positive after final probes:
  `srr_v2_capacity12_scar_precision_interact`, Dice `0.2063`.
- nnU-Net references: scar all-case `0.5602`, edema GT-positive `0.3944`.
- 80% nnU-Net gates: scar all-case `0.4481`, edema GT-positive `0.3155`.

## Route Evidence

| Route | Result/selection | Status | Best target metrics | Gap to 80% nnU-Net gate |
| --- | --- | --- | --- | --- |
| Repaired proposal | `results/20260629_repaired_proposal_repeat/selection.md` | `ROUTE_TO_CASCADE_TEACHER` | scar all-case `0.1038`; edema GT-positive `0.1545` | scar gap `0.3443`; edema gap `0.1610` |
| Required SRR-v2 | `results/20260629_srr_v2_unet_core/selection.md` | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2474`; edema GT-positive `0.1855` | scar gap `0.2007`; edema gap `0.1300` |
| SRR-v2 light-refine extras | `results/20260629_srr_v2_unet_core/light_refine_extras/selection.md` | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2431`; edema GT-positive `0.1879` | scar gap `0.2050`; edema gap `0.1276` |
| SRR-v2 capacity extras | `results/20260629_srr_v2_unet_core/capacity_extras/selection.md` | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.3090`; edema GT-positive `0.1894` | scar gap `0.1391`; edema gap `0.1261` |
| SRR-v2 targeted extras | `results/20260629_srr_v2_unet_core/targeted_extras/selection.md` | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2377`; edema GT-positive `0.1873` | scar gap `0.2104`; edema gap `0.1282` |
| SRR-v2 capacity-targeted extras | `results/20260629_srr_v2_unet_core/capacity_targeted_extras/selection.md` | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2643`; edema GT-positive `0.1939` | scar gap `0.1838`; edema gap `0.1216` |
| SRR-v2 balanced-targeted extras | `results/20260629_srr_v2_unet_core/balanced_targeted_extras/selection.md` | `STOP_NO_SRR_V2_SIGNAL` | scar all-case `0.2678`; edema GT-positive `0.2063` | scar gap `0.1803`; edema gap `0.1092` |
| Cascade teacher | `results/20260629_cascade_teacher_route/selection.md` | `STOP_NO_CASCADE_SIGNAL` | all formal variants failed route-selection criteria | not selected |
| Cine motion alignment | `results/20260629_cine_motion_alignment/selection.md` | `SELECT_MOTION_DESCRIPTOR_ONLY` | descriptor only; no pathology route selected | Cine secondary evidence only |
| Cine motion pathology | `results/20260629_cine_motion_pathology/selection.md` | `SELECT_REFERENCE_CONTROL_ONLY` | motion variants did not beat reference control | Cine secondary evidence only |

## GPU Jobs And Logs

| Work item | Job ID | Partition | Runtime / scheduler state | Logs |
| --- | --- | --- | --- | --- |
| Repaired proposal repeat | `57094448_[0-2]` | `htzhulab` | `06:35:50`, `COMPLETED` | `logs/RePropF0_repaired_uncertainty_hardneg_57170530_20260630_193743.log`; `logs/RePropF0_repaired_posneg_scar_hardneg_57170596_20260630_194005.log`; `logs/RePropF0_repaired_joint_calibrated_proposal_57094448_20260630_194156.log` |
| SRR-v2 basic | `57094446_0` | `htzhulab` | `06:37:38`, `FAILED`, recovered from checkpoint/export evidence | `logs/SRRv2F0_srr_v2_multiscale_private_basic_57094446_20260630_191118.log` |
| SRR-v2 missing variants A100 duplicate | `57095505_[1-2]` | `a100-gpu` | `CANCELLED` after preferred `htzhulab` fallback covered same variants | no selected evidence |
| SRR-v2 htzhulab fallback | `57272337_[1-2]` | `htzhulab` | `06:34:26`, `COMPLETED` | `logs/SRRv2F0_srr_v2_multiscale_private_proposal_57272341_20260701_105238.log`; `logs/SRRv2F0_srr_v2_proposal_uncertainty_hardneg_57272337_20260701_105237.log` |
| Cascade teacher formal | `57272502_[0-2]` | `htzhulab` | `00:18:12`, `COMPLETED` | `logs/CascadeOOFRefine_57272502_20260701_105500.log`; `logs/CascadeOOFRefine_57272503_20260701_105500.log`; `logs/CascadeOOFRefine_57272504_20260701_105500.log` |
| Cascade component guard | `57274444_[0-1]` | `htzhulab` | `00:02:46`, `COMPLETED` | `logs/CascadeCG_57274444_20260701_111923.log`; `logs/CascadeCG_57274446_20260701_111923.log` |
| Cascade signal seek | `57275246_[0-1]` | `htzhulab` | `00:05:05`, `COMPLETED` | `logs/CascadeSS_57275246_20260701_112729.log`; `logs/CascadeSS_57275248_20260701_112729.log` |
| SRR-v2 light-refine extras | `57277361_[0-1]` | `htzhulab` | `06:33:40`, `COMPLETED` | `logs/SRRv2Light_srr_v2_light_refine_lowmix_57277362_20260701_114404.log`; `logs/SRRv2Light_srr_v2_light_refine_hardneg_57277361_20260701_114404.log` |
| SRR-v2 capacity extras | `57279322_[0-1]` | `htzhulab` | `06:32:18`, `COMPLETED` | `logs/SRRv2Cap_srr_v2_capacity12_proposal_57279792_20260701_120937.log`; `logs/SRRv2Cap_srr_v2_capacity12_hardneg_57279322_20260701_120937.log` |
| SRR-v2 targeted extras | `57334792_[0-1]` | `htzhulab` | `06:35:44`, `COMPLETED` | `logs/SRRv2Tgt_srr_v2_edema_t2_focus_57339095_20260702_014620.log`; `logs/SRRv2Tgt_srr_v2_scar_precision_nointeract_57334792_20260702_014620.log` |
| Cancelled targeted A100/Volta duplicates | `57340171`, `57340161` | `a100-gpu`, `volta-gpu` | `CANCELLED` after preferred route covered evidence | no selected evidence |
| SRR-v2 capacity-targeted extras | `57354982_[0-1]` | `htzhulab` | `06:34:29`, `COMPLETED` | `logs/SRRv2CapT_srr_v2_capacity12_edema_t2_focus_57373703_20260702_053035.log`; `logs/SRRv2CapT_srr_v2_capacity12_scar_precision_nointeract_57354982_20260702_054647.log` |
| SRR-v2 balanced-targeted extras | `57358073_[0-1]` | `htzhulab` | `06:32:31`, `COMPLETED` | `logs/SRRv2BalT_srr_v2_capacity12_balanced_lowmix_57384777_20260702_080208.log`; `logs/SRRv2BalT_srr_v2_capacity12_scar_precision_interact_57358073_20260702_082208.log` |

## Completion Audit

- Audit: `results/20260629_rescue_goal/completion_audit.md`
- `completion_proven=True`
- `blocking_requirements=0`
- GPU ledger: `results/20260629_rescue_goal/gpu_action_status.md`
- GPU ledger `open_actions=0`
- Route matrix: `results/20260629_rescue_goal/pending_status.md`

## Interpretation

The negative result is not from one failed variant. The sprint tested proposal
repair, SRR-v2 U-Net capacity, hard-negative replay, targeted edema/scar
weighting, no-interaction and interaction variants, cascade teacher refinement,
component guard, signal seek, and postprocessing. Capacity improved scar from
the original SRR-v2 run but plateaued at `0.3090`, far below the `0.4481`
selection floor. Edema remained weaker, with the best final GT-positive signal
at `0.2063`, below the `0.3155` floor and still carrying high surface-distance
and false-positive burden.

Current Cine motion work also should not be promoted: motion descriptor is the
only alignment-side evidence, and the pathology-side route remains reference
control.

## Not Executed

- No validation upload.
- No upload-ready package.
- No fold expansion.
- No label mapping, fold split, or evaluator change.
- No no-T2 myocardium-as-edema-negative change.

## Next Recommendation

Do not continue this exact SRR tuning ladder under the same goal. If a future
task continues MyoPS, it should use a new hypothesis: for example a stronger
nnU-Net-anchored segmentation strategy, a label/data mechanism audit, or a
different pathology-specific postprocessor with explicit false-positive control.
If the immediate objective is challenge performance, the practical baseline to
carry forward is still nnU-Net rather than any custom SRR route from this
sprint.

No validation upload or upload-ready package was generated.
