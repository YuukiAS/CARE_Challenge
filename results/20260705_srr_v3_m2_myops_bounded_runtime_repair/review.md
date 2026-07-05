# Review 20260705 SRR-v3 M2 MyoPS Bounded Runtime Repair

task_key: `20260705_srr_v3_m2_myops_bounded_runtime_repair`
reviewed_task: `prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md`
reviewed_result_dir: `results/20260705_srr_v3_m2_myops_bounded_runtime_repair/`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M2_AUDITED_NEEDS_REVISION`

## Scope

This is a read-only milestone review of the M2 executor packet. I did not modify model/training code, did not generate missing executor artifacts, did not train, did not package or upload validation data, did not claim route promotion, and did not start M3. This review writes only this `review.md`.

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
| M1 prerequisite gate passed before M2. | `SUPPORTED` | `results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md` contains `decision: M1_AUDITED_GO`. |
| Required M2 outputs are present and tracked. | `SUPPORTED` | `git ls-files results/20260705_srr_v3_m2_myops_bounded_runtime_repair` lists all task-required Markdown/CSV outputs plus small JSON smoke evidence. |
| Executor did not self-approve or start M3. | `SUPPORTED` | `review_request.md` states `review.md` is intentionally absent at executor stop and M3 remains blocked until `M2_AUDITED_GO`. |
| No heavy forbidden artifacts are included in the M2 packet. | `SUPPORTED` | A file search under the result directory found no `*.zip`, `*.nii`, `*.nii.gz`, `*.pt`, `*.pth`, or `*.npz` files. |
| Closed-gate identity and correction-positive opening are exercised. | `SUPPORTED` | `baseline_gate_safety_sanity.csv` has two `PASS` rows: closed-gate max abs diff vs anchor logits `0.0`, and correction-positive gate mean `0.9241417646408081` with nonzero correction. |
| Strong encoder/context path is callable beyond tiny smoke. | `SUPPORTED` | `strong_encoder_context_sanity.csv` records real-case forward runtime on `Case2002` with `strong_4scale`, `base_channels=8`, scale channels `8;16;32;64`, and logits shape `1x6x8x32x32`. |
| T2-present edema prototype coverage is repaired at smoke scale. | `SUPPORTED` | `prototype_t2_coverage_sanity.csv` records initial first-12 LGE-only cases, repair-added cases `Case2001;Case2003;Case2004;Case2005`, non-empty edema positives/negatives, and `t2_present_edema_positive=4351`. The tracked `runtime_smoke/prototype_bank_summary.json` matches the selected case ids and counts. |
| Proposal/refinement path is bounded local ROI rather than full-volume residual. | `SUPPORTED` | `proposal_refinement_sanity.csv` has scar and edema `PASS` rows with crop volume ratios `0.046875` and `0.08544921875`, both `is_full_volume_crop=False`. |
| No-T2 edema safety is end-to-end inert in the smoke path. | `SUPPORTED` | `no_t2_safety_sanity.csv` records `Case1002`, `t2_present=False`, edema proposal/final logits `-20.0`, zero argmax edema voxels, zero pathology-aware edema voxels, and `PASS_NO_T2_DECODE_HAS_ZERO_EDEMA`. |
| The T2 edema prototype repair is wired into the training entrypoint, not only the exporter. | `SUPPORTED` | `scripts/training/run_srr_propref_myops_fold0.py` defines `ensure_t2_edema_prototype_cases(...)` and calls it inside `train_variant(...)` after reading limited train cases. |
| Strict validator passes on the real packet and fails closed on a claim-only packet. | `SUPPORTED` | Read-only reruns of `--strict-validate` and `--known-bad-validator-smoke` both exited `0`; strict validation reported no issues, and known-bad validation reported claim-only/failing-status issues for all required CSVs. |
| Cache/provenance isolation fully satisfies the M2 task text. | `NOT_SUPPORTED_AS_WRITTEN` | The task requires every smoke output to record checkpoint path, prototype source, selected case ids, encoder profile, optimizer steps, and eval case ids. `runtime_smoke_summary.json` records mode, patch shape, prototype summary path, eval case ids, and gap status, but it does not explicitly record checkpoint path, optimizer steps, encoder profile, prototype source, or selected case ids. These fields are either absent or split across other artifacts, so `runtime_gap_closure_table.csv` marking `cache_provenance_isolation` as `CLOSED` is overclaimed. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 1]`.

```bash
git ls-files results/20260705_srr_v3_m2_myops_bounded_runtime_repair
```

Result: all task-required M2 packet files are tracked; `review.md` was not present before this review.

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

Result: exit `0`; claim-only rows failed closed across the required CSVs.

## Required Revision

The executor should revise the M2 packet to make cache/provenance isolation explicitly auditable. At minimum, `runtime_smoke_summary.json` or a dedicated provenance artifact should record the M2-required fields directly:

- `checkpoint_path`: use an explicit value such as `N/A_NO_TRAINING_SMOKE` if no checkpoint is used.
- `optimizer_steps`: use `0` for the no-training smoke.
- `encoder_profile` and strong encoder channel profile.
- `prototype_source`.
- `selected_case_ids`.
- `eval_case_ids`.

After that, rerun the M2 strict validator and update `runtime_gap_closure_table.csv` so `cache_provenance_isolation` is supported by the referenced artifact. This is a small provenance revision; I do not see evidence that it requires full-fold training, validation packaging/upload, or route promotion.

## Decision

decision: `M2_AUDITED_NEEDS_REVISION`

M2 is not yet approved for M3. The core bounded runtime repair smoke evidence is largely supported, but the M2 task's explicit cache/provenance isolation requirement is not fully satisfied by the current packet. This decision does not authorize route promotion, fold expansion, validation packaging, validation upload, hosted metric claims, scientific stop, formal training adequacy, or challenge readiness.
