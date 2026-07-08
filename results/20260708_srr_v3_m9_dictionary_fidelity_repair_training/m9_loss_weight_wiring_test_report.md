# M9 Loss-weight Wiring Test Report

status: `PASS_SMOKE_NOT_FULL_M9_READY`

CPU smoke command constructed `SRRProposeRefineMyoPS(variant='m9_srr_main_true_br2_pattern_sip')`, ran a synthetic two-case forward pass, and called `srr_m6_expanded_total_loss(...)` twice with `loss_scar_refiner_small_roi` set to `0` and `10`.

Observed:

```text
weight=0.0  total_loss=3.352638  grad_norm=8.084674  grad_param_count=990
weight=10.0 total_loss=12.969973 grad_norm=33.314659 grad_param_count=990
```

total_loss_changed: `true`

gradient_norm_changed: `true`

M9 output mode observed: `SRR_MAIN_NOT_ANCHOR_RESIDUAL`

nnU-Net role observed: `CONTEXT_TEACHER_SAFETY_CONTROL_ONLY`

