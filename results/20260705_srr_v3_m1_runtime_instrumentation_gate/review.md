# Review 20260705 SRR-v3 M1 Runtime Instrumentation Gate

task_key: `20260705_srr_v3_m1_runtime_instrumentation_gate`
reviewed_task: `prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md`
reviewed_result_dir: `results/20260705_srr_v3_m1_runtime_instrumentation_gate/`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M1_AUDITED_NEEDS_EVIDENCE`

## Scope

这是 M1 的独立只读审阅。我没有修改模型代码，没有补 executor 缺失产物，没有训练，没有 validation packaging/upload，没有 route promotion，也没有启动 M2。本审阅只写入本文件 `review.md`。

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/review.md`
- files under `results/20260705_srr_v3_m1_runtime_instrumentation_gate/`
- `scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M0 prerequisite gate passed before M1. | `SUPPORTED` | `results/20260705_srr_v3_m0_architecture_master_contract/review.md` contains `decision: M0_AUDITED_GO`. |
| Required M1 outputs are present and tracked. | `SUPPORTED` | `git ls-files results/20260705_srr_v3_m1_runtime_instrumentation_gate` lists all prompt-required files: `result.md`, `instrumentation_contract.md`, the four CSV exports, `instrumentation_unit_tests.md`, `completion_check.md`, `review_request.md`, and `MANIFEST.md`. |
| M1 exported gate/residual runtime evidence rather than natural-language-only claims. | `SUPPORTED` | `gate_residual_export.csv` has 11 lines: header, 8 case/class rows, and 2 aggregate rows. Rows include gate open-rate thresholds, bounded delta, `gate * bounded_delta` correction magnitude, decode deltas versus nnU-Net anchor, anchor confidence, and `runtime_instrumented` evidence status. |
| M1 exported anchor/component alignment evidence. | `SUPPORTED` | `anchor_context_alignment_export.csv` has 4 runtime rows for `Case1002`, `Case2002`, `Case3004`, and `Case3011`; all rows have `shape_alignment_status=PASS`, anchor source paths, anchor fold, and tensor shapes. |
| M1 exported no-T2 safety evidence. | `SUPPORTED` | `no_t2_safety_export.csv` includes no-T2 `Case1002` with `edema_logit_max=-20.0`, `final_edema_logit_max=-20.0`, zero edema decode voxels, and `PASS` logit/decode guard status. |
| M1 exported prototype coverage evidence. | `SUPPORTED_BLOCKING` | `prototype_coverage_export.csv` is present and runtime/source-summary derived, but it reports `edema_positive=0`, `edema_negative=0`, `t2_present_edema_positive=0`, and `coverage_status=EDEMA_PROTOTYPES_EMPTY`. |
| Strict validator behavior is fail-closed. | `SUPPORTED` | Read-only rerun of `./envs/env_CARE/bin/python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --strict-validate` exited `1` with `prototype_coverage_export.csv: edema_prototypes_empty`. |
| Executor used eval-only instrumentation and did not claim formal training adequacy. | `SUPPORTED` | `result.md` and `instrumentation_contract.md` state the packet used an existing bounded checkpoint with `6` optimizer steps on four explicit fold0 cases, no training, and no route promotion. |
| Executor did not start M2 or self-review. | `SUPPORTED` | Before this review, `review.md` was absent; current checks show M2-M4 result directories are absent. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 2]`.

```bash
git ls-files results/20260705_srr_v3_m1_runtime_instrumentation_gate
```

Result: all prompt-required M1 packet files are tracked.

```bash
wc -l results/20260705_srr_v3_m1_runtime_instrumentation_gate/*.csv
```

Result: `gate_residual_export.csv` has 11 lines, `anchor_context_alignment_export.csv` has 5 lines, `no_t2_safety_export.csv` has 5 lines, and `prototype_coverage_export.csv` has 2 lines.

```bash
./envs/env_CARE/bin/python scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py --strict-validate
```

Result: exit `1`; `strict_validate_passed: false`; issue `prototype_coverage_export.csv: edema_prototypes_empty`.

## Blockers

M1 should not receive `M1_AUDITED_GO` because the task completion gate explicitly says not to mark ready if prototype coverage cannot identify T2-present edema positives/negatives. The exported prototype coverage confirms this blocker: edema prototype positive and negative counts are both zero, and the strict validator fails closed for that reason.

This is not a tooling failure. The instrumentation helper and CSV packet are useful diagnostic evidence, but the actual bounded checkpoint remains undertrained and does not provide a non-empty T2-present edema prototype source.

## Decision

decision: `M1_AUDITED_NEEDS_EVIDENCE`

M2 remains blocked. The next authorized step should build or select an adequate non-empty T2-present edema prototype source, then rerun M1-style instrumentation so the prototype coverage gate can be re-audited. This review does not authorize route promotion, fold expansion, validation packaging/upload, hosted metric claims, scientific stop, or next-stage training beyond a GPT/user-authorized milestone.
