# MANIFEST: 20260704_srr_v25_pathology_proposal_decoders

task_source: `prompts/tasks/20260704_srr_v25_pathology_proposal_decoders.md`

## Artifacts

- `result.md` - executor result and gate decision.
- `proposal_math.md` - scar/edema proposal formula and separate policy.
- `component_level_loss.md` - component ranking loss design and smoke evidence.
- `proposal_pr_sweep.csv` - bounded local eval proposal precision/recall sweep.
- `lesion_wise_recall.csv` - lesion-wise recall subset from proposal sweep.
- `remote_fp_report.csv` - remote/small/outside-myocardium FP subset from proposal sweep.
- `scar_edema_policy.md` - scar and edema routing/safety policy.
- `ablation_report.md` - required formal ablations not yet run.
- `unit_test_report.md` - tests, compile, and smoke commands.
- `runtime_smoke/variants/srr_propref_shared_dual_dict/` - one-case local eval artifacts.
- `component_loss_smoke_logged/variants/srr_propref_shared_dual_dict/` - proposal-stage component loss smoke artifacts.

## Current State

state: `COMPONENT_PROPOSAL_LOSS_AND_ONE_CASE_PR_VERIFIED_NEEDS_FORMAL_ABLATION`

No validation package, external upload, git commit, or git push was performed.
