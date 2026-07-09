# M9 nnU-Net Role Audit

status: `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`

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

Anchor-only and M8 anchor-residual controls still need post-job aggregation rows before M9 can be reviewed.
