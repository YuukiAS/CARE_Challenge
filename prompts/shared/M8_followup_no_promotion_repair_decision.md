# M8 Follow-up No-promotion Repair Decision Staging Prompt

This is a GPT-authored staging file for the post-M8 follow-up. It must be split by a later Codex maintenance step into `prompts/shared/EXECUTOR_PROMPTS.md` and `prompts/shared/REVIEWER_PROMPTS.md`, then deleted after the split/merge is verified.

Do not treat this staging file as route promotion, fold expansion, validation packaging, upload authorization, hosted-metric claim, leaderboard readiness, or scientific stop.

## Route Bootstrap Evidence

```yaml
diagram_source: "current conversation uploaded visual materials / ChatGPT visual channel"
diagram_versions_read: ["SRR-v2", "SRR-v2.5", "SRR-v3"]
canonical_repo_paths: ["images/SRR-v2.png", "images/SRR-v2.5.png", "images/SRR-v3.png"]
visual_read_status: "READ_FROM_CURRENT_CONVERSATION_UPLOADS"
previous_review_path: "results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md"
previous_review_token: "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
staging_file: "prompts/shared/M8_followup_no_promotion_repair_decision.md"
```

Recovered route objective: SRR-MyoPS v3 is not an nnU-Net postprocess. It is an availability-aware selective retrieval system that preserves a strong nnU-Net anchor through bounded residual correction, semantic representation retrieval banks with real positive/negative prototype evidence, anatomy-guided scar/edema lesion proposal, pathology-specific soft-ROI refinement, explicit no-T2-safe edema supervision, negative-space / hard-negative control, dictionary / prototype objectives, and reviewer-grade help/harm evidence. Cine remains a registration-aware anatomy-first temporal retrieval branch with ED/reference, motion/registration, temporal dictionary, frame-wise anatomy prior, and temporal aggregation evidence.

M8 review outcome: M8 is accepted as a completed executor evidence packet, but it is not accepted as route promotion, fold expansion, validation packaging, hosted-metric claim, leaderboard readiness, scientific stop, or M9 authorization. The next work must therefore be a bounded post-M8 repair/decision milestone, not automatic expansion.

## Executor Prompt

You are the Codex executor/controller for exactly one post-M8 follow-up milestone. This is not M9, not fold expansion, not validation packaging, and not route promotion.

Required protocol sentence: This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md, force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.

### 1. Required reading before execution

Read these files before doing any scientific or code work:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
prompts/shared/M8_followup_no_promotion_repair_decision.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/result.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/completion_check.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/MANIFEST.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/commands_run.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_route_promotion_decision.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_best_variant_decision_table.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_candidate_assembly_matrix.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_same_split_help_harm.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_srr_contribution_by_case.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_hard_subgroup_metrics.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_component_remote_fp_hd95_report.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_nnunet_anchor_control_metrics.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_training_budget_ledger.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_validation_events.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_temporal_dictionary_evidence.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_registration_same_subset_matrix.csv
```

If any required M8 evidence file is missing, write a minimal blocked packet with status `M8_FOLLOWUP_NEEDS_EVIDENCE_MISSING_M8_INPUT`, list the missing paths, and stop. Do not infer from old summaries.

### 2. Task identity and scope

Use this result directory:

```text
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/
```

Allowed first-party helper path:

```text
scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py
```

The scientific question is narrow:

Can existing M8 evidence support a deployable, non-GT, non-case-ID, baseline-preserving arbitration or repair contract that makes SRR-v3 useful after the M8 no-promotion review, or must GPT return to route planning because the current SRR candidate family is still scientifically unresolved?

This follow-up must use existing M8 evidence and, if available locally, existing M8 runtime prediction/proxy artifacts. It must not start new model training. It must not submit validation packaging. It must not upload. It must not claim hosted metrics. It must not turn M8 into M9.

### 3. Route interpretation to enforce

The follow-up must preserve the SRR-v3 route structure:

1. availability-aware modality handling; zero-filled missing C0/T2 must never be interpreted as real images without an availability mask;
2. semantic representation retrieval and prototype/dictionary evidence must be connected to final logits or final labels, not only CSV diagnostics;
3. anatomy-guided proposal must remain soft and evidence-based; no hard deletion or hard ROI clipping as the mainline;
4. scar and edema must be evaluated separately, with pathology-specific failure modes and no `foreground_mean` promotion;
5. no-T2 edema safety is mandatory: no rule may treat no-T2 myocardium as edema-negative training evidence, and no deployable arbitration may introduce edema voxels into no-T2 safety cases;
6. nnU-Net may be the anchor/control and safety source, but SRR cannot be reduced to an optional postprocess wrapper.

### 4. Required implementation or diagnostic work

Implement or update `scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py` so it can be run from repository root and produce a fail-closed result packet. It may read tracked M8 CSV/JSON/MD evidence and local runtime summaries if present. It must not require checkpoints or NIfTI files to pass the minimal diagnostic, but if local prediction artifacts are available it may add optional final-label-impact checks.

The helper must construct four ledgers:

1. `m8_review_findings_ledger.csv`: parse or manually encode M8 review claims into machine-checkable rows with fields `finding_id`, `source_path`, `source_line_or_section`, `claim`, `effect_on_followup`, `blocking_level`.
2. `m8_candidate_failure_matrix.csv`: summarize why each M8 candidate failed promotion. Required fields: `candidate_id`, `metric_name`, `anchor_dice`, `candidate_dice`, `dice_delta`, `anchor_hd95`, `candidate_hd95`, `hd95_delta`, `remote_fp_delta`, `component_delta`, `hard_subgroup`, `failure_class`, `eligible_for_repair_contract`.
3. `m8_proxy_feature_schema.csv`: define deployable proxy features allowed for arbitration. Required fields: `feature_name`, `source`, `available_at_inference`, `uses_ground_truth`, `uses_case_id`, `uses_hosted_feedback`, `allowed_for_policy`, `reason`.
4. `m8_proxy_arbitration_help_harm.csv`: evaluate at least three pre-declared deployable policies against the nnU-Net anchor and M8 candidates. Required fields: `policy_id`, `policy_description`, `uses_only_allowed_features`, `candidate_source`, `metric_name`, `case_count`, `dice_mean_anchor`, `dice_mean_policy`, `dice_delta`, `hd95_mean_anchor`, `hd95_mean_policy`, `hd95_delta`, `remote_fp_mean_anchor`, `remote_fp_mean_policy`, `no_t2_edema_voxels`, `scar_guardrail_status`, `edema_guardrail_status`, `promotion_status`.

The three policy families must include:

1. `anchor_only_control`: the no-change safety baseline;
2. `candidate_only_control`: the best M8 local candidate as-is, to verify the M8 no-promotion result is reproduced;
3. at least one deployable arbitration/fallback policy that may use only non-GT proxy signals such as availability mask, T2-present status, residual magnitude, candidate-anchor disagreement magnitude, distance to anatomy support, component size, largest-component fraction, baseline/candidate uncertainty if already exported, proposal/refiner gate statistics if already exported, and local intensity/prototype support if already exported.

Forbidden policy features:

```text
case_id
validation ground truth labels for choosing the rule
Dice / HD95 / component metric values as rule inputs
hosted validation feedback
manual case lists
center ID as a primary decision feature unless explicitly marked diagnostic-only
empty-GT shortcut promotion
foreground_mean-only selection
```

Ground truth may be used only after a policy is pre-declared, to evaluate help/harm on the same split. If thresholds are tuned using metrics, the helper must label the result `DIAGNOSTIC_THRESHOLD_TUNED_NOT_DEPLOYABLE` and must not mark it repair-ready.

### 5. Required outputs

The result directory must contain these top-level files:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m8_followup_route_objective.md
m8_review_findings_ledger.csv
m8_candidate_failure_matrix.csv
m8_proxy_feature_schema.csv
m8_proxy_arbitration_help_harm.csv
m8_hard_subgroup_help_harm.csv
m8_no_t2_safety_report.csv
m8_repair_contract.md
m8_next_required_action.md
m8_followup_strict_validator_report.csv
m8_followup_strict_validator_report.md
m8_followup_validator_selftest_report.csv
m8_followup_validator_selftest_report.md
```

`m8_followup_route_objective.md` must restate that the objective is post-M8 no-promotion repair decision, not M9, not route promotion, and not validation packaging.

`m8_hard_subgroup_help_harm.csv` must include at least these subgroup labels when present in M8 evidence: `CenterB`, `CenterC`, `T2_present`, `no_T2_safety`, `scar_positive`, `edema_positive`, `remote_FP_cases`, and `component_burden_cases`.

`m8_no_t2_safety_report.csv` must explicitly report whether any policy introduces edema voxels for no-T2 cases. Any nonzero value is a blocker unless the row is explicitly diagnostic-only and not selected.

`m8_repair_contract.md` must state one of:

```text
REPAIR_CONTRACT_READY_FOR_REVIEW
NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND
NEEDS_EVIDENCE_MISSING_INPUTS
NEEDS_REVISION_PIPELINE_OR_VALIDATOR
```

A repair contract can be marked ready only if it is deployable, uses no forbidden features, preserves no-T2 edema safety, is compared to the same-split nnU-Net anchor, reports scar and edema separately, includes hard-subgroup help/harm, and does not claim validation readiness. It may authorize GPT to consider a future bounded implementation milestone; it does not authorize Codex to start that milestone.

`m8_next_required_action.md` must choose exactly one next action:

```text
GPT_PLAN_BOUNDED_REPAIR_IMPLEMENTATION
GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR
NEEDS_EVIDENCE_BEFORE_ANY_NEXT_TASK
NEEDS_REVISION_BEFORE_REVIEW
```

### 6. Strict validator and known-bad self-tests

The helper or separate validator mode must fail closed on these known-bad mutations:

1. missing M8 review or wrong previous token;
2. missing same-split nnU-Net anchor comparison;
3. policy uses `case_id`;
4. policy uses Dice/HD95/component values as decision inputs;
5. policy uses hosted feedback;
6. no-T2 edema voxels are introduced by a selected policy;
7. only `foreground_mean` is reported;
8. candidate-only is marked promoted despite M8 no-promotion review;
9. required output missing;
10. `completion_check.md` says ready while validator has nonzero errors;
11. route promotion, fold expansion, validation packaging, upload, hosted metric claim, or M9 is claimed;
12. monitor or pending Slurm status is marked completion;
13. Cine frame0-only or descriptor-only evidence is used to claim temporal readiness;
14. synthetic or placeholder evidence is used as the only proof.

The self-test report must include at least one good fixture and the known-bad mutations above. If any known-bad mutation passes, completion must be `M8_FOLLOWUP_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

### 7. Completion states

Allowed executor completion states:

```text
M8_FOLLOWUP_READY_FOR_REVIEW
M8_FOLLOWUP_NEEDS_EVIDENCE_MISSING_M8_INPUT
M8_FOLLOWUP_NEEDS_REVISION_PIPELINE_OR_VALIDATOR
M8_FOLLOWUP_NO_DEPLOYABLE_REPAIR_FOUND_READY_FOR_REVIEW
M8_FOLLOWUP_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

`M8_FOLLOWUP_READY_FOR_REVIEW` is allowed only when all required files exist, the validator exits zero on the real packet, known-bad self-tests fail closed, and no forbidden action is claimed. It is not an audited decision.

### 8. Git and artifact policy

Commit only lightweight Markdown/CSV/JSON files and the first-party helper. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees.

Recommended local commit command:

```bash
git add -f scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py \
  results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/*.md \
  results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/*.csv \
  results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/*.json
git commit -m "Add M8 follow-up repair decision packet"
```

Do not push automatically.

## Reviewer Prompt

You are the separate read-only reviewer/auditor for the M8 follow-up no-promotion repair decision milestone.

Required protocol sentence: This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, and do not start the next milestone. Review only the completed result directory, write review.md with the controlled milestone decision, then force-add/commit review.md. Do not push automatically.

### 1. Review scope

Review only:

```text
prompts/shared/M8_followup_no_promotion_repair_decision.md
scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_route_promotion_decision.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_best_variant_decision_table.csv
```

You may also read the required protocol files if needed:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
```

### 2. Required checks

Check that the executor did not convert M8 into route promotion, fold expansion, validation packaging, hosted metric claim, leaderboard readiness, scientific stop, or M9.

Check that `results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/` includes:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m8_followup_route_objective.md
m8_review_findings_ledger.csv
m8_candidate_failure_matrix.csv
m8_proxy_feature_schema.csv
m8_proxy_arbitration_help_harm.csv
m8_hard_subgroup_help_harm.csv
m8_no_t2_safety_report.csv
m8_repair_contract.md
m8_next_required_action.md
m8_followup_strict_validator_report.csv
m8_followup_strict_validator_report.md
m8_followup_validator_selftest_report.csv
m8_followup_validator_selftest_report.md
```

Check that the policy feature schema marks these as forbidden for selected deployable policies: case ID, GT metric values as decision inputs, hosted feedback, manual case lists, foreground_mean-only selection, and center-ID-only routing.

Check that the same-split nnU-Net anchor is included and that scar and edema are reported separately. Do not accept a foreground mean as route evidence.

Check no-T2 edema safety. Any selected policy with nonzero no-T2 edema voxels must be rejected unless it is clearly diagnostic-only and not selected.

Check hard subgroups. The packet must not be easy-only. It must include T2-present, no-T2 safety, CenterB/CenterC or the strongest available equivalents, scar-positive/edema-positive, and remote-FP/component-burden analysis where available.

Check validator behavior. The real packet validator must pass with zero errors only for a valid packet, and known-bad self-tests must fail closed. If a known-bad mutation passes, return `M8_FOLLOWUP_AUDITED_NEEDS_REVISION`.

Check evidence quality. Monitor packets, pending Slurm jobs, smoke-only evidence, synthetic evidence, placeholder evidence, old summaries, executor self-review, or missing aggregation cannot support audited-go.

### 3. Review decision states

Write `results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md` with exactly one of these controlled decisions:

```text
M8_FOLLOWUP_AUDITED_REPAIR_CONTRACT_READY
M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED
M8_FOLLOWUP_AUDITED_NEEDS_EVIDENCE
M8_FOLLOWUP_AUDITED_NEEDS_REVISION
M8_FOLLOWUP_AUDITED_PROTOCOL_BLOCKED
```

`M8_FOLLOWUP_AUDITED_REPAIR_CONTRACT_READY` means only this: GPT may plan a future bounded repair implementation milestone using the reviewed repair contract. It does not authorize Codex to start that implementation automatically, and it does not authorize route promotion, fold expansion, validation packaging, upload, hosted metric claims, leaderboard claims, scientific stop, or M9.

Use `M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED` if the executor produced a valid diagnostic packet but no deployable non-GT arbitration/repair contract improves the situation enough to justify implementation.

Use `M8_FOLLOWUP_AUDITED_NEEDS_EVIDENCE` if required M8 inputs or follow-up outputs are missing, if runtime/proxy evidence is insufficient, or if the packet relies only on natural-language claims.

Use `M8_FOLLOWUP_AUDITED_NEEDS_REVISION` if code, schema, validator, leakage prevention, no-T2 safety, same-split comparison, or hard-subgroup reporting is broken.

Use `M8_FOLLOWUP_AUDITED_PROTOCOL_BLOCKED` if the executor violated role boundaries by writing `review.md`, starting the next milestone, claiming M9, packaging validation, uploading, or claiming hosted metrics.

### 4. Commit policy

Commit only the review file:

```bash
git add -f results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
git commit -m "Add M8 follow-up repair decision review"
```

Do not push automatically.
