# M9 nnU-Net Role Audit

status: `RUNTIME_RECONCILED_FOR_M9_FOLLOWUP`

Formal M9 variants expose:

- `m9_final_output_mode`: `SRR_MAIN_NOT_ANCHOR_RESIDUAL`
- `nnunet_role`: `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`
- `srr_main_logits`
- `proposal_logits`
- `refiner_logits`
- `anatomy_context_logits`
- `final_logits`
- `final_label_delta_vs_srr_without_dictionary`
- `final_label_delta_vs_anchor_control`

The new formal M9 code path sets `final_logits = srr_logits` for `m9_` variants. It does not use the older anchor-plus-bounded-delta residual equation as the normal output path.

Post-job aggregation rows are now tracked in:

- `m9_same_split_help_harm.csv`
- `m9_component_remote_fp_hd95_report.csv`
- `m9_metric_aligned_checkpoint_selection.csv`
- `m9_route_promotion_decision.md`

The reconciled evidence supports the same no-promotion direction: formal M9 candidates remain negative against the tracked M8 nnU-Net anchor, and nnU-Net remains context/teacher/safety control rather than the formal M9 candidate output base.
