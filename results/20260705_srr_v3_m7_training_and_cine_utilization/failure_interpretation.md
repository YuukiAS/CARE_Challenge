# Failure Interpretation

status: `EXECUTED_UNAUDITED_NEEDS_REVIEW`

M7 produced formal minimum-duration fold0 evidence for all three required variants. The executor does not claim route promotion or route-negative stop; reviewer must judge same-split help/harm, hard subgroup effects, no-T2 safety, and Cine registration blockers.

## Loss Component Zero/Applicability Notes

`loss_component_by_step.csv` contains all required M7 loss components. The post-run range audit found no component with all recorded values exactly zero. Some components are expected to be zero or near-zero on subsets:

- `loss_no_t2_edema_safety`, `loss_edema_proposal_t2_present_only`, and `loss_edema_refiner_t2_present_roi` are mask-gated by T2/no-T2 applicability, so zero rows can be legitimate when the current batch has no applicable positive target.
- `loss_branch_arbitration_consistency` stayed near zero, not missing; gradient sanity rows exist in `loss_component_gradient_sanity.csv`. Reviewer should treat this as a low-signal arbitration-consistency finding to inspect, not as proof of route success.
- Semantic family/interaction mass rows can be zero when the corresponding modality/interaction slot is unavailable for the sampled batch; `branch_arbitration_by_case.csv` and `dictionary_prototype_usage_by_variant.csv` summarize valid-fraction coverage.
