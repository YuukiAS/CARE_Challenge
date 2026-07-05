# Result: 20260704 SRR-v2.5 Training Ablation Matrix

status: `EXECUTED_UNAUDITED`
self_assessed_status: `FULL_FOLD0_MATRIX_COMPLETE_NEEDS_FINAL_READONLY_AUDIT`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## 执行摘要

本轮在已有 help/harm 管线基础上，扩展为 8-row bounded hard-subgroup
matrix。没有重跑 current anchored packet，没有 validation packaging/upload。
两个 identity rows（`nnunet_context_identity`,
`closed_gate_identity_fallback`）直接导出 same-split nnU-Net fold0 hard
predictions；三个 PropRef rows 都用 fold0、同一 explicit eval cases
`Case1002,Case2002,Case3004,Case3011`，每个 6 optimizer steps，并导出
checkpoint_final case metrics、subgroup metrics 和 same-split nnU-Net
help/harm。随后又补齐三个隔离 rows：`srr_v25_no_local_refine`,
`srr_v25_no_anatomy_roi`, `srr_v25_no_anchor`。

该 matrix 仍不支持 route promotion 或 scientific stop：required hard-subgroup
bounded rows 已补齐，full fold0 eval-only rows 也已补齐，但训练 rows 都来自
6-step bounded checkpoints，明显 underpowered。当前用途是机制 triage 和 final
read-only audit 输入，不是 challenge-facing 候选。

## 读取文件

- `prompts/tasks/20260704_srr_v25_full_completion_goal.md`
- `prompts/tasks/20260704_srr_v25_training_ablation_matrix.md`
- `prompts/AGENT_RULES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `/users/a/e/aereinh/.codex-global/skills/core-codex-system-codex-workflow-protocol/SKILL.md`
- `results/20260704_srr_v25_local_refinement_ablation/runtime_smoke/variants/srr_propref_shared_dual_dict/component_hd_by_case_checkpoint_final.csv`
- `results/20260704_srr_v25_local_refinement_ablation/runtime_smoke/variants/srr_propref_shared_dual_dict/subgroup_metrics_checkpoint_final.csv`
- `results/20260704_srr_v25_pathology_proposal_decoders/runtime_smoke/variants/srr_propref_shared_dual_dict/training_log.csv`
- `results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/variants/*/summary.json`
- `results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/help_harm/*/*`

## 修改文件

- `scripts/evaluation/srr_help_harm_vs_nnunet.py`
- `scripts/evaluation/aggregate_srr_v25_bounded_matrix.py`
- `scripts/evaluation/export_srr_v25_identity_matrix_rows.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `src/care_myocardium/models/srr_propref.py`
- `results/20260704_srr_v25_training_ablation_matrix/help_harm_vs_nnunet.csv`
- `results/20260704_srr_v25_training_ablation_matrix/ablation_summary.csv`
- `results/20260704_srr_v25_training_ablation_matrix/subgroup_metrics.csv`
- `results/20260704_srr_v25_training_ablation_matrix/training_curves.csv`
- `results/20260704_srr_v25_training_ablation_matrix/bounded_matrix_summary.csv`
- `results/20260704_srr_v25_training_ablation_matrix/variant_matrix.md`
- `results/20260704_srr_v25_training_ablation_matrix/same_split_metrics.md`
- `results/20260704_srr_v25_training_ablation_matrix/mechanism_decision.md`
- `results/20260704_srr_v25_training_ablation_matrix/MANIFEST.md`
- `results/20260704_srr_v25_full_completion_goal/controller_report.md`
- `results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay/*`
- `results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval/*`

## 运行命令

```bash
./envs/env_CARE/bin/python scripts/evaluation/export_srr_v25_identity_matrix_rows.py \
  --matrix-root results/20260704_srr_v25_training_ablation_matrix/bounded_matrix \
  --case-ids Case1002,Case2002,Case3004,Case3011 \
  --fold 0
```

Result: exit `0`.

```bash
./envs/env_CARE/bin/python scripts/training/run_srr_propref_myops_fold0.py \
  --variant <srr_propref_shared_dual_dict|srr_propref_scar_precision|srr_propref_no_proto_cascade> \
  --fold 0 \
  --device cpu \
  --base-channels 4 \
  --encoder-profile tiny_3scale \
  --max-steps 6 \
  --max-runtime-seconds 1200 \
  --val-every 3 \
  --overfit-steps 1 \
  --min-overfit-loss-decrease -999 \
  --limit-train-cases 12 \
  --limit-val-cases 4 \
  --prototype-bank-cases 12 \
  --eval-case-ids Case1002,Case2002,Case3004,Case3011 \
  --out-root results/20260704_srr_v25_training_ablation_matrix/bounded_matrix
```

Result: three runs exited `0`.

Three additional isolated ablation invocations used the same command template as
above with:

- `--run-label srr_v25_no_local_refine --disable-local-refinement`
- `--run-label srr_v25_no_anatomy_roi --disable-anatomy-roi-prior`
- `--run-label srr_v25_no_anchor --disable-nnunet-anchor`

Result: all three isolated ablation runs exited `0`.

```bash
./envs/env_CARE/bin/python scripts/evaluation/srr_help_harm_vs_nnunet.py \
  --srr-metrics results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/variants/<variant>/component_hd_by_case_checkpoint_final.csv \
  --output-dir results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/help_harm/<variant> \
  --fold 0
```

Result: eight help/harm runs exited `0`.

```bash
./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_v25_bounded_matrix.py \
  --matrix-root results/20260704_srr_v25_training_ablation_matrix/bounded_matrix \
  --output-dir results/20260704_srr_v25_training_ablation_matrix \
  --checkpoint checkpoint_final
```

Result: exit `0`.

## 当前证据

- Identity rows: `nnunet_context_identity` and `closed_gate_identity_fallback`
  both have zero delta versus nnU-Net for Dice, HD95, component count, and
  remote-FP metrics on the explicit hard-subgroup cases.
- Bounded PropRef variants: `srr_propref_shared_dual_dict`,
  `srr_propref_scar_precision`, `srr_propref_no_proto_cascade`.
- Isolated bounded ablation rows now cover `srr_v25_no_local_refine`,
  `srr_v25_no_anatomy_roi`, and `srr_v25_no_anchor`.
- Each non-identity variant: `actual_optimizer_steps=6`, `stop_reason=max_steps`,
  `eval_cases=4`.
- Training loss increased in all six 6-step CPU training rows, so this is explicitly
  underpowered: full loss `2.808609 -> 3.829002`, scar_precision
  `3.070143 -> 4.208627`, no_proto `2.677842 -> 3.457186`,
  no-local-refine `2.808608 -> 3.132921`, no-anatomy-roi
  `2.808609 -> 3.849958`, no-anchor `2.804722 -> 3.861267`.
- Same-split help/harm shows no remote-FP regression for all anchor-enabled rows.
  `srr_v25_no_anchor` is the exception and strongly degrades: pathology-aware
  mean delta is scar Dice `-0.608290`, edema Dice `-0.311185`, scar remote-FP
  `+801.0`, and edema remote-FP `+4635.5`.
- `srr_v25_no_local_refine` is effectively identity on the four hard-subgroup
  pathology-aware metrics: scar/edema Dice, HD95, component count, and remote-FP
  all have mean delta `0.0` versus nnU-Net on this bounded packet.
- `srr_v25_no_anatomy_roi` is near-neutral but not helpful: pathology-aware
  edema Dice mean delta `-0.000145`, scar Dice mean delta `-0.000113`, remote-FP
  deltas `0.0`.
- Bounded matrix overlay/taxonomy now exists for the six non-identity variants:
  42 PNGs and 96 taxonomy rows under
  `results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay/`.
  The taxonomy matches the help/harm signal: anchor-enabled rows mainly show
  neutral/boundary patterns, while `srr_v25_no_anchor` concentrates remote-island
  failures.
- Best small signal: no-proto pathology-aware edema has mean Dice delta
  `+0.007202` over 4 cases, but scar_precision/full remain near-zero and the
  evidence is too weak for any route claim.
- CenterC/T2-present edema remains low across variants; the bounded matrix does
  not yet solve the hard-subgroup issue identified in the overlay packet.
- Full fold0 eval-only export is complete for all six expected non-identity
  variants from existing bounded checkpoints. Each row has 44 fold0 validation
  cases, 88 predictions, 176 case metric rows, 36 subgroup rows, and same-split
  help/harm against fold0 nnU-Net.
- Full fold0 pathology-aware deltas show that all anchor-enabled rows are
  near-identity or tiny mixed effects versus nnU-Net. The largest positive mean
  signal is `srr_propref_no_proto_cascade` edema Dice `+0.001480`, paired with
  scar Dice `-0.000410` and edema remote-FP `+0.045455`.
- The `srr_v25_no_anchor` row is strongly harmful on full fold0: edema Dice
  `-0.142051`, edema remote-FP `+2073.727`, scar Dice `-0.558659`, and scar
  remote-FP `+856.932`. This supports the baseline-preserving anchor gate as
  necessary, but does not prove the SRR route beats nnU-Net.

## 测试结果

```bash
./envs/env_CARE/bin/python -m py_compile \
  scripts/evaluation/srr_help_harm_vs_nnunet.py \
  scripts/training/run_srr_myops_fold0.py \
  scripts/training/run_srr_propref_myops_fold0.py \
  scripts/validation/validate_srr_v25_anti_laziness.py \
  src/care_myocardium/losses/srr_losses.py \
  src/care_myocardium/models/srr_propref.py \
  src/care_myocardium/models/srr_v2_unet.py \
  src/care_myocardium/tests/test_srr_dictionary_bank.py \
  src/care_myocardium/tests/test_srr_proposal_prototypes.py \
  src/care_myocardium/tests/test_srr_anatomy_distance_roi_prior.py \
  src/care_myocardium/tests/test_srr_baseline_gate.py \
  src/care_myocardium/tests/test_srr_encoder_context_interface.py \
  src/care_myocardium/tests/test_srr_runtime_prototype_bank.py \
  src/care_myocardium/tests/test_srr_v25_anti_laziness_validator.py
```

Result: exit `0`.

```bash
./envs/env_CARE/bin/python -m unittest \
  src.care_myocardium.tests.test_srr_encoder_context_interface \
  src.care_myocardium.tests.test_srr_anatomy_distance_roi_prior \
  src.care_myocardium.tests.test_srr_runtime_prototype_bank \
  src.care_myocardium.tests.test_srr_proposal_prototypes \
  src.care_myocardium.tests.test_srr_baseline_gate \
  src.care_myocardium.tests.test_srr_v25_anti_laziness_validator \
  src.care_myocardium.tests.test_srr_v25_loss_contract \
  src.care_myocardium.tests.test_myops_decode_guardrails \
  src.care_myocardium.tests.test_srr_dictionary_bank
```

Result: exit `0`, latest targeted run `Ran 36 tests`, `OK`.

```bash
./envs/env_CARE/bin/python scripts/validation/validate_srr_v25_anti_laziness.py \
  --repo-root . \
  --controller prompts/tasks/20260704_srr_v25_full_completion_goal.md \
  --results-root results \
  --json
```

Result: exit `0`, `error_count: 10`. All reported issues are legacy
`CLAIM_WITHOUT_RUNTIME_EVIDENCE` findings in older result/review files; no new
`UTILITY_ONLY_NOT_CALLED`, `PROTOTYPE_SOURCE_NOT_FINAL`, or
`BASELINE_PRESERVING_GATE_MISSING` blocker was reported for this work.

```bash
git diff --check
```

Result: exit `0`.

## 未完成事项

- Required hard-subgroup bounded variants in `variant_matrix.md` are now covered,
  but this remains a 6-step bounded matrix rather than full formal evidence.
- Full fold0 eval-only subgroup evidence exists for all six expected
  non-identity rows, but it comes from the same bounded checkpoints.
- No final read-only audit has reviewed this complete packet yet.

## 需要人工批准的事项

None. No validation package, upload, commit, or push was performed.

## 下一步

Run the final read-only audit. Current state is
`FULL_FOLD0_MATRIX_COMPLETE_NEEDS_FINAL_READONLY_AUDIT`.
