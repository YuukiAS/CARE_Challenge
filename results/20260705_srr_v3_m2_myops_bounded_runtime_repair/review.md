# Review 20260705 SRR-v3 M2 MyoPS Bounded Runtime Repair

task_key: `20260705_srr_v3_m2_myops_bounded_runtime_repair`
reviewed_task: `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md`
reviewed_result_dir: `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/`
reviewed_executor_commit: `a41ec07 Revise SRR v3 M2 provenance evidence`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M2_AUDITED_GO`

## Scope

This is a read-only review of the M2 continued executor packet. I did not modify model/training/evaluation code, did not generate missing executor artifacts, did not train, did not package or upload validation data, did not claim route promotion, and did not start M3. This review updates only this `review.md`.

This review supersedes the prior `M2_AUDITED_NEEDS_REVISION` decision. The previous blocker was that `cache_provenance_isolation` was marked `CLOSED` without a single auditable artifact containing checkpoint path, prototype source, selected case ids, encoder profile, optimizer steps, and eval case ids. The continued packet adds that artifact and hardens the strict validator.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md`
- files under `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/`
- `scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py`
- `scripts/training/run_srr_propref_myops_fold0.py`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M1 prerequisite gate passed before M2 continued work. | `SUPPORTED` | `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md` contains `decision: M1_AUDITED_GO`. |
| M2 continued started from the correct prior review state. | `SUPPORTED` | The prior `review.md` contained `M2_AUDITED_NEEDS_REVISION`, and `result.md` states the continued revision only addressed the provenance/cache blocker. |
| Required M2 outputs are present and tracked. | `SUPPORTED` | `git ls-files results/20260705_srr_v3_m2_myops_bounded_runtime_repair` lists all task-required Markdown/CSV outputs plus `runtime_smoke_summary.json`, `provenance_cache_summary.json`, and `runtime_smoke/prototype_bank_summary.json`. |
| Executor did not self-approve or start M3. | `SUPPORTED` | `review_request.md` says the prior review records the previous blocker and M3 remains blocked until a separate reviewer writes `M2_AUDITED_GO`; `test ! -d results/20260705_srr_v3_m3_myops_min_effective_pilot_training` exited `0`. |
| No heavy forbidden artifacts are included in the M2 packet. | `SUPPORTED` | A file search under the result directory returned no `*.zip`, `*.nii`, `*.nii.gz`, `*.pt`, `*.pth`, or `*.npz` files. |
| Closed-gate identity and correction-positive opening are exercised. | `SUPPORTED` | `baseline_gate_safety_sanity.csv` has two `PASS` rows: closed-gate max abs diff vs anchor logits `0.0`, and correction-positive gate mean `0.9241417646408081` with nonzero correction. |
| Strong encoder/context path is callable beyond tiny smoke. | `SUPPORTED` | `strong_encoder_context_sanity.csv` records real-case forward runtime on `Case2002` with `strong_4scale`, `base_channels=8`, scale channels `8;16;32;64`, and logits shape `1x6x8x32x32`. |
| T2-present edema prototype coverage is repaired at smoke scale. | `SUPPORTED` | `prototype_t2_coverage_sanity.csv` records initial first-12 LGE-only cases, repair-added cases `Case2001;Case2003;Case2004;Case2005`, non-empty edema positives/negatives, and `t2_present_edema_positive=4351`. `runtime_smoke/prototype_bank_summary.json` matches selected case ids and counts. |
| Proposal/refinement path is bounded local ROI rather than full-volume residual. | `SUPPORTED` | `proposal_refinement_sanity.csv` has scar and edema `PASS` rows with crop volume ratios `0.046875` and `0.08544921875`, both `is_full_volume_crop=False`. |
| No-T2 edema safety is end-to-end inert in the smoke path. | `SUPPORTED` | `no_t2_safety_sanity.csv` records `Case1002`, `t2_present=False`, edema proposal/final logits `-20.0`, zero argmax edema voxels, zero pathology-aware edema voxels, and `PASS_NO_T2_DECODE_HAS_ZERO_EDEMA`. |
| The T2 edema prototype repair is wired into the training entrypoint, not only the exporter. | `SUPPORTED` | `scripts/training/run_srr_propref_myops_fold0.py` defines `ensure_t2_edema_prototype_cases(...)` and calls it inside `train_variant(...)` after reading limited train cases. |
| Cache/provenance isolation now satisfies the M2 task text. | `SUPPORTED` | `runtime_gap_closure_table.csv` points `cache_provenance_isolation` to `provenance_cache_summary.json`. That JSON directly records `checkpoint_path=N/A_NO_TRAINING_SMOKE`, `optimizer_steps=0`, `encoder_profile=strong_4scale`, `encoder_scale_channels=8;16;32;64`, `prototype_source=train_oof_runtime_features_fold0`, prototype summary path, selected case ids `Case2001;Case2003;Case2004;Case2005`, eval case ids `Case1002;Case2002`, patch shape, smoke scope, commands path, and artifact paths. |
| Strict validator passes on the real packet and fails closed on claim-only or missing-provenance packets. | `SUPPORTED` | Read-only reruns of `--strict-validate` and `--known-bad-validator-smoke` both exited `0`; strict validation reported no issues, and known-bad validation reported claim-only/failing-status plus missing `cache_provenance_isolation` and missing `provenance_cache_summary.json`. |
| M2 evidence remains smoke-scale and does not claim scientific route adequacy. | `SUPPORTED` | `result.md`, `completion_check.md`, `code_diff_summary.md`, and `provenance_cache_summary.json` state no training checkpoint was used (`N/A_NO_TRAINING_SMOKE`, `optimizer_steps=0`) and no route promotion, validation packaging/upload, hosted metric claim, or challenge readiness is claimed. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 5]`.

```bash
git ls-files results/20260705_srr_v3_m2_myops_bounded_runtime_repair
```

Result: all task-required M2 packet files, the continued provenance JSON, and this `review.md` are tracked.

```bash
test ! -d results/20260705_srr_v3_m3_myops_min_effective_pilot_training
```

Result: exit `0`; M3 result directory is absent.

```bash
find results/20260705_srr_v3_m2_myops_bounded_runtime_repair -type f \( -name '*.zip' -o -name '*.nii' -o -name '*.nii.gz' -o -name '*.pt' -o -name '*.pth' -o -name '*.npz' \) -print
```

Result: no forbidden heavy artifact paths were returned.

```bash
PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py --strict-validate
```

Result: exit `0`; `strict_validate_passed: true`; no issues.

```bash
PYTHONDONTWRITEBYTECODE=1 ./envs/env_CARE/bin/python scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py --known-bad-validator-smoke
```

Result: exit `0`; claim-only and missing-provenance rows failed closed.

## Residual Caveat

This approval is for M2 bounded runtime repair only. The evidence remains smoke-scale: it proves the repaired runtime paths and provenance checks are callable/auditable, not that SRR-v3 improves metrics over nnU-Net or is ready for challenge validation.

## Decision

decision: `M2_AUDITED_GO`

M2 is approved as the bounded runtime repair milestone. This permits the user/GPT to start the next authorized milestone that depends on `review.md:M2_AUDITED_GO`, subject to normal handoff protocol and human push/visibility decisions.

This decision does not authorize route promotion, fold expansion, validation packaging, validation upload, hosted metric claims, scientific stop, formal training adequacy, or challenge readiness.
