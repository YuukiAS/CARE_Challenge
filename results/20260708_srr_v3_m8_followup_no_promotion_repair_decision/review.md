# M8 Follow-up Independent Review

review_status: `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED`

reviewed_packet: `results/20260708_srr_v3_m8_followup_no_promotion_repair_decision`
reviewed_at_utc: `2026-07-08`
reviewer_role: `read_only_milestone_reviewer`

## Decision

The M8 follow-up packet is accepted as a valid diagnostic no-promotion repair
decision packet. It does not support a deployable repair contract.

This review does not authorize route promotion, fold expansion, validation
packaging, validation upload, hosted metric claims, leaderboard claims,
scientific stop, M9, or automatic implementation of another milestone.

## Evidence Checked

- `result.md`, `completion_check.md`, and `review_request.md` consistently report
  `M8_FOLLOWUP_NO_DEPLOYABLE_REPAIR_FOUND_READY_FOR_REVIEW`.
- `commands_run.md` records only
  `python scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py`.
  It also states that no Slurm job, training, validation package, or upload was
  launched.
- Re-running the helper from repository root reproduced the same final status:
  `M8_FOLLOWUP_NO_DEPLOYABLE_REPAIR_FOUND_READY_FOR_REVIEW`.
- `m8_review_findings_ledger.csv` carries forward the required M8 review token
  `M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`.
- `m8_candidate_failure_matrix.csv` includes scar and edema separately for all
  M8 local candidate rows. Edema remains below the same-split nnU-Net anchor for
  every candidate; scar gains are marked small or diagnostic-only.
- `m8_proxy_feature_schema.csv` marks deployability-critical forbidden features
  as not allowed: case ID, center-only routing, Dice, HD95,
  component-count metric values, hosted feedback, and foreground mean.
- `m8_proxy_arbitration_help_harm.csv` includes anchor-only, candidate-only, and
  deployable proxy fallback policies. Candidate-only reproduces M8 no promotion;
  deployable proxy policies do not produce a scar-plus-edema mechanism-consistent
  SRR help signal.
- `m8_hard_subgroup_help_harm.csv` includes CenterB, CenterC, T2-present,
  no-T2 safety, scar-positive, edema-positive, remote-FP, and component-burden
  subgroup rows. The key hard subgroups remain harm or unresolved, especially
  edema-positive/T2-present and CenterB/CenterC edema.
- `m8_no_t2_safety_report.csv` reports zero no-T2 edema voxels for all evaluated
  policy rows and selects no policy for repair contract.
- `m8_repair_contract.md` states
  `NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND`.
- `m8_next_required_action.md` states
  `GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR`.
- `m8_followup_strict_validator_report.md` reports `PASS` with `error_count=0`.
- `m8_followup_validator_selftest_report.md` reports `PASS`, `self_test_rows=15`,
  and no failed self-tests. The CSV confirms one good fixture passes and all
  known-bad mutations fail closed, including missing M8 review token, missing
  anchor comparison, forbidden policy features, no-T2 violation,
  foreground-mean/easy-only evidence, candidate-only promotion, missing output,
  ready-with-validator-error, route-promotion claim, monitor completion,
  Cine frame0-only temporal claim, and placeholder-only proof.

## Scientific Interpretation

The follow-up answers the intended question: existing M8 evidence does not
support a deployable non-GT arbitration or repair contract.

The strongest candidate-only scar row improves Dice by only about `+0.0054`,
while the paired edema row drops by about `-0.0073`. The deployable conservative
proxy fallback uses SRR on zero cases and therefore collapses to anchor-only
control. The deployable high-SRR-signal fallback uses SRR on all scar cases and
half of edema cases, but scar gain remains small and edema remains worse than
the anchor. Hard subgroup rows show unresolved or harmful behavior for CenterB,
CenterC, T2-present, and edema-positive subgroups.

Therefore the correct audited outcome is
`M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED`.

## Required Next State

Return control to GPT/user planning with
`GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR`.

Do not start implementation, fold expansion, validation packaging/upload, route
promotion, hosted-metric claiming, or M9 from this packet.
