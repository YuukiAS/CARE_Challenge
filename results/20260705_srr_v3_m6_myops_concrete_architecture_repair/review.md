# Review 20260705 SRR-v3 M6 Concrete Architecture Repair

task_key: `20260705_srr_v3_m6_myops_concrete_architecture_repair`
reviewed_result_dir: `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`
reviewed_executor_commit: `3af6bd3 Add SRR v3 M6 architecture repair`
reviewer_role: `independent read-only reviewer/auditor`
decision: `M6_AUDITED_NEEDS_REVISION`

## Scope

This is a read-only review of the M6 executor packet. I did not modify model/training/evaluation code, did not generate missing executor artifacts, did not train, did not package or upload validation data, did not claim route promotion, and did not start M7. This review writes only this `review.md`.

The short runtime is not itself the deciding issue. The blocker is that the submitted evidence does not satisfy several M6 reviewer gates that were meant to prevent a synthetic-only or claim-only packet from authorizing M7.

## Source Files Reviewed

- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md`
- files under `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`
- `scripts/evaluation/run_srr_v3_m6_concrete_architecture_repair.py`
- M6-modified first-party code paths listed in `code_diff_summary.md`

## Claim Table

| Claim | Decision | Evidence |
| --- | --- | --- |
| M4 prerequisite gate passed before M6. | `SUPPORTED` | `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` contains `decision: M4_AUDITED_GO`. |
| Required M6 output files are present and tracked. | `SUPPORTED` | `git ls-files results/20260705_srr_v3_m6_myops_concrete_architecture_repair` lists all required result artifacts, and `review.md` was absent before this review. |
| Executor made first-party code changes rather than only writing CSV/Markdown. | `SUPPORTED` | Commit `3af6bd3` modifies `scripts/training/run_srr_propref_myops_fold0.py`, `src/care_myocardium/losses/srr_losses.py`, `src/care_myocardium/models/srr_blocks.py`, `src/care_myocardium/models/srr_propref.py`, `src/care_myocardium/models/srr_v2_unet.py`, and adds `scripts/evaluation/run_srr_v3_m6_concrete_architecture_repair.py`. |
| M6 avoids full-fold training, validation packaging/upload, hosted metric claims, route promotion, and M7 execution. | `SUPPORTED` | `result.md` and `commands_run.md` report bounded executor work only; no validation package/upload or hosted metric claim appears in the packet. |
| Three required variants are represented. | `SUPPORTED` | CSV parsing found `m6_full_srr_context_arbitration`, `m6_conservative_component_arbitration`, and `m6_scar_precision_edema_safe` across architecture/runtime evidence tables. |
| Encoder profile evidence exists. | `SUPPORTED_WITH_CAVEAT` | `encoder_decoder_capacity_sanity.csv` includes balanced, safe, and full 4-scale rows. The full row is only a very small synthetic `1x3x3x10x10` forward smoke, so it is architecture smoke only, not capacity evidence for training-scale data. |
| Segmentation context, dictionary retrieval, prototype, proposal, refiner, no-T2 safety, and loss-component tables exist. | `SUPPORTED_WITH_CAVEAT` | Required CSVs exist and are non-empty, but the case IDs and contract text show the evidence is synthetic anchor-derived only; `srr_v3_fidelity_contract.md` explicitly says `bounded runtime/synthetic anchor-derived only`. |
| Branch/evidence arbitration proves both required directions. | `NOT_SUPPORTED` | `branch_arbitration_sanity.csv` has only 3 rows and only `sanity_type=correction_positive`. There are no `low_quality_srr` or equivalent rows, and no row where arbitration chooses the segmentation branch because SRR/prototype/proposal evidence is low quality. The reviewer prompt explicitly requires both SRR adoption in correction-positive sanity and segmentation-branch adoption when SRR evidence is low quality. |
| Explicit fallback/closed-gate identity path is safe. | `SUPPORTED` | `decode_gate_consistency_sanity.csv` reports `final_equals_anchor_labels=True` and `hidden_decode_delta_voxels=0` for all three variants under explicit segmentation fallback. This does not replace the missing low-quality SRR arbitration sanity. |
| Strict validator proves known-bad packets fail closed. | `NOT_SUPPORTED` | `strict_validator_report.md` contains only generated summary lines such as `PASS_FAIL_CLOSED`. The generator script computes booleans from the same in-memory good packet; it does not construct known-bad packets, run a strict validator command against them, or record nonzero exits. Therefore this is not fail-closed evidence for claim-only, missing trace, hidden-decode-delta, zero-SRR-contribution, no-T2 unsafe, or full-volume-refiner packets. |
| Unit tests independently cover the M6 hard gates. | `NOT_SUPPORTED` | `unit_test_report.md` reports existing unittest modules passing, but these tests do not cover the missing low-quality SRR branch-arbitration gate or actual known-bad packet fail-closed behavior. |
| Prototype evidence satisfies route-ready prototype provenance. | `SUPPORTED_WITH_CAVEAT` | `prototype_bank_runtime_sanity.csv` has non-empty scar/edema positive/negative rows with no no-T2 edema negative. However, all prototype rows use `source_split=synthetic_anchor_derived_runtime_sanity` and `source=anchor_derived_runtime_sanity_feature_tensors`, so this remains bounded synthetic smoke evidence, not train/OOF prototype evidence. |
| M6 can authorize M7 as currently written. | `NOT_SUPPORTED` | Because low-quality SRR arbitration evidence and real fail-closed known-bad validator evidence are missing, the packet cannot pass the M6 audited-go gate. |

## Commands Run

```bash
git status --short --branch
```

Result before writing this review: `## main...origin/main [ahead 1]`.

```bash
find results/20260705_srr_v3_m6_myops_concrete_architecture_repair -maxdepth 3 -type f | sort
```

Result: all required first-level M6 result packet files were present; `review.md` was absent before this review.

```bash
python - <<'PY'
import csv, os
base='results/20260705_srr_v3_m6_myops_concrete_architecture_repair'
required=[...]
print('missing', [x for x in required if not os.path.exists(os.path.join(base,x))])
for fn in [x for x in required if x.endswith('.csv')]:
    with open(os.path.join(base,fn), newline='') as f:
        rows=list(csv.DictReader(f))
    print(fn, 'rows', len(rows), 'caseids', sorted({r.get('case_id','') for r in rows if 'case_id' in r})[:10])
PY
```

Result: no required files were missing. The main runtime case IDs were `synthetic_anchor_derived_t2_present` and `synthetic_no_t2`.

```bash
python - <<'PY'
import csv
base='results/20260705_srr_v3_m6_myops_concrete_architecture_repair'
with open(f'{base}/branch_arbitration_sanity.csv', newline='') as f:
    branch=list(csv.DictReader(f))
print(sorted({r['sanity_type'] for r in branch}))
print([r for r in branch if 'segmentation' in r.get('chosen_source','') or r.get('fallback_reason')=='explicit_segmentation_fallback'])
PY
```

Result: only `correction_positive` sanity rows exist; no segmentation-branch low-quality SRR row exists.

```bash
python - <<'PY'
from pathlib import Path
base=Path('results/20260705_srr_v3_m6_myops_concrete_architecture_repair')
strict=(base/'strict_validator_report.md').read_text()
fid=(base/'srr_v3_fidelity_contract.md').read_text()
print('strict_report_has_commands', 'exit_code' in strict or 'command' in strict)
print('synthetic_only_declared', 'synthetic anchor-derived' in fid)
PY
```

Result: the strict report has no command/exit-code evidence, and the fidelity contract declares synthetic anchor-derived bounded evidence.

```bash
python -m py_compile scripts/evaluation/run_srr_v3_m6_concrete_architecture_repair.py src/care_myocardium/models/srr_propref.py src/care_myocardium/losses/srr_losses.py
git diff --check
```

Result: both commands exited `0`.

## Required Revision

M6 should not be treated as failed science, but it is not audit-ready for `M6_AUDITED_GO`. The executor needs to revise the packet and, if needed, the helper/validator code so that:

1. `branch_arbitration_sanity.csv` includes a low-quality SRR/prototype/proposal case where arbitration chooses the segmentation branch, with final labels exactly matching the segmentation branch and explicit `chosen_source` / `fallback_reason`.
2. The strict validator is a real fail-closed validator or equivalent command-driven check. `strict_validator_report.md` must record known-bad packet names, commands, expected failures, actual nonzero exits, and the reason each known-bad case failed.
3. The readiness decision distinguishes synthetic anchor-derived smoke from train/OOF or real-case runtime evidence. If the intended M6 gate is synthetic-only architecture smoke, `completion_check.md` should not claim a stronger ready state than the prompt allows.
4. Unit-test evidence should cover the M6 hard gates directly, especially low-quality SRR arbitration and known-bad validator behavior.

## Decision

decision: `M6_AUDITED_NEEDS_REVISION`

M6 has useful first-party implementation work and several meaningful synthetic sanity artifacts, but the current packet does not satisfy the independent review gate for M6 audited-go. M7 remains blocked until a revised M6 packet is reviewed and receives `M6_AUDITED_GO`.

This decision does not authorize route promotion, fold expansion, validation packaging/upload, hosted metric claims, scientific stop, challenge readiness, or M7 execution.
