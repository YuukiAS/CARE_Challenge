# Result 20260704 SRR-v2.5 Pathology Proposal Decoders

status: `EXECUTED_UNAUDITED`
self_assessed_status: `COMPONENT_PROPOSAL_LOSS_AND_ONE_CASE_PR_VERIFIED_NEEDS_FORMAL_ABLATION`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

Added a component-level proposal ranking objective to the formal PropRef runner and generated bounded local proposal/refinement diagnostics. The proposal path is now more than voxel BCE/Dice: GT lesion components are ranked against safe-negative/background proposal scores, separately for scar and edema with no-T2 edema blocking.

This still does not pass the subtask. The evidence is one-case local smoke plus unit tests, not formal hard-subgroup improvement.

## Runtime Evidence

| item | value |
| --- | --- |
| eval smoke optimizer steps | `1` |
| eval smoke skip_export | `False` |
| eval case from PR table | `Case1002` |
| scar threshold 0.50 recall / precision | `0.5092143549951503` / `0.7824143070044709` |
| scar lesion-wise recall | `1.0` |
| scar remote FP | `0` |
| scar final Dice/HD95 linkage | `0.004708751237131284` / `180.8299584115473` |
| edema threshold 0.50 recall / precision | `` / `` |
| edema final Dice/HD95 linkage | `1.0` / `0.0` |
| proposal-stage component ranking loss | `1.721025824546814` |

## Outputs

- `proposal_math.md`
- `component_level_loss.md`
- `proposal_pr_sweep.csv`
- `lesion_wise_recall.csv`
- `remote_fp_report.csv`
- `scar_edema_policy.md`
- `ablation_report.md`
- `unit_test_report.md`
- `MANIFEST.md`

## Missing For PASS

- Multi-case fold0 proposal PR and final Dice linkage.
- CenterC scar and CenterC T2-present edema subgroup evidence.
- Ablations for no component ranking, no prototype proposal, no component evidence, no ROI refiner, and scar/edema policy variants.
- Separate read-only audit.

## Gate Decision

decision: `COMPONENT_PROPOSAL_LOSS_AND_ONE_CASE_PR_VERIFIED_NEEDS_FORMAL_ABLATION`

No validation package, external upload, git commit, or git push was performed.
