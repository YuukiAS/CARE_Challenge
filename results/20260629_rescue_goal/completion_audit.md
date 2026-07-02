# 20260629 Rescue Goal Completion Audit

This audit is evidence-gated. It does not redefine the goal around partial outputs.

- completion_proven: `False`
- blocking_requirements: `1`

| requirement | status | evidence | detail |
| --- | --- | --- | --- |
| goal: required non-final artifacts | PASS | `results/20260629_rescue_goal/result.md, results/20260629_rescue_goal/MANIFEST.md, results/20260629_rescue_goal/progress.md, results/20260629_rescue_goal/route_status.csv, results/20260629_rescue_goal/pending_status.md, results/20260629_rescue_goal/gpu_action_status.csv, results/20260629_rescue_goal/gpu_action_status.md, results/20260629_rescue_goal/gpu_partition_status.csv, results/20260629_rescue_goal/gpu_partition_status.md` | all present |
| goal: final_status.md only after all evidence is complete | PENDING | `results/20260629_rescue_goal/final_status.md` | not written yet |
| operational: GPU action ledger | INCOMPLETE | `results/20260629_rescue_goal/gpu_action_status.csv, results/20260629_rescue_goal/gpu_action_status.md` | rows=13, open_actions=2; srr_v2_targeted_extras:QUEUED_OR_RUNNING:monitor:wait=not_pending; srr_v2_capacity_targeted_extras:QUEUED_OR_RUNNING:monitor:wait=continue_monitoring:pending_hours=0.04:rechecks=0/12:next=2026-07-02 04:29:25 |
| operational: GPU partition snapshot | PASS | `results/20260629_rescue_goal/gpu_partition_status.csv, results/20260629_rescue_goal/gpu_partition_status.md` | rows=3; htzhulab:pending=2:running=6:reasons=(None):1; (Resources):1; a100-gpu:pending=442:running=22:reasons=(AssocGrpGRES):4; (JobHeldUser):219; (Priority):218; (Resources):1; volta-gpu:pending=100:running=56:reasons=(AssocGrpGRES):2; (Dependency):3; (Priority):94; (Resources):1 |
| operational: cascade formal GPU action | PASS | `jobs/src/run_cascade_oof_refiner.sh` | formal cascade variants ready 3/3; no GPU action required |
| operational: SRR-v2 isolated fallback readiness | PASS | `jobs/src/run_srr_v2_unet_core.sh, scripts/evaluation/finalize_rescue_srr_route.py` | OUT_ROOT/PREFLIGHT_OUT_ROOT and aggregation --root are available; new duplicate fallback GPU launches still require explicit approval if command review rejects them |
| repaired_proposal: result/selection/metrics artifacts | PASS | `results/20260629_repaired_proposal_repeat/result.md, results/20260629_repaired_proposal_repeat/selection.md, results/20260629_repaired_proposal_repeat/metrics_summary.md` | selection_status=ROUTE_TO_CASCADE_TEACHER |
| repaired_proposal: all formal variants ready | PASS | `3/3 variants ready` | repaired_uncertainty_hardneg: ready under results/20260629_repaired_proposal_repeat/variants/repaired_uncertainty_hardneg; repaired_posneg_scar_hardneg: ready under results/20260629_repaired_proposal_repeat/variants/repaired_posneg_scar_hardneg; repaired_joint_calibrated_proposal: ready under results/20260629_repaired_proposal_repeat/variants/repaired_joint_calibrated_proposal |
| srr_v2: result/selection/metrics artifacts | PASS | `results/20260629_srr_v2_unet_core/result.md, results/20260629_srr_v2_unet_core/selection.md, results/20260629_srr_v2_unet_core/metrics_summary.md` | selection_status=STOP_NO_SRR_V2_SIGNAL |
| srr_v2: all formal variants ready | PASS | `3/3 variants ready` | srr_v2_multiscale_private_basic: ready under results/20260629_srr_v2_unet_core/variants/srr_v2_multiscale_private_basic; srr_v2_multiscale_private_proposal: ready under results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_multiscale_private_proposal; srr_v2_proposal_uncertainty_hardneg: ready under results/20260629_srr_v2_unet_core_htzhulab_fallback/variants/srr_v2_proposal_uncertainty_hardneg |
| cascade_teacher: result/selection/metrics artifacts | PASS | `results/20260629_cascade_teacher_route/result.md, results/20260629_cascade_teacher_route/selection.md, results/20260629_cascade_teacher_route/metrics_summary.md` | selection_status=STOP_NO_CASCADE_SIGNAL |
| cascade_teacher: all formal variants ready | PASS | `3/3 variants ready` | nnunet_anatomy_prior_refiner: ready under results/20260629_cascade_teacher_route/variants/nnunet_anatomy_prior_refiner with 44/44 validation predictions; nnunet_pathology_teacher_srr_refiner: ready under results/20260629_cascade_teacher_route/variants/nnunet_pathology_teacher_srr_refiner with 44/44 validation predictions; coarse_to_fine_srr_roi: ready under results/20260629_cascade_teacher_route/variants/coarse_to_fine_srr_roi with 44/44 validation predictions |
| cine_motion_alignment: result/selection artifacts | PASS | `results/20260629_cine_motion_alignment/result.md, results/20260629_cine_motion_alignment/selection.md, results/20260629_cine_motion_alignment/metrics_summary.md` | selection_status=SELECT_MOTION_DESCRIPTOR_ONLY |
| cine_motion_pathology: result/selection artifacts | PASS | `results/20260629_cine_motion_pathology/result.md, results/20260629_cine_motion_pathology/selection.md, results/20260629_cine_motion_pathology/metrics_summary.md` | selection_status=SELECT_REFERENCE_CONTROL_ONLY |

## Conclusion

The rescue goal is not complete. Do not write `final_status.md` until every MyoPS route has formal variant evidence and the final route decision can be justified against the nnU-Net reference.
