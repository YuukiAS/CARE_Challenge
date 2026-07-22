# Result 20260722_srr_batch7_minimal_pathology_decomposition

status: partial_complete
self_assessed_status: NEEDS_CONTINUED_EXECUTION

## 执行摘要

本轮按 executor 边界修复了一个关键实现错误：正式 SIP 不再从当前 batch 的 `effective_beta` 计算，而是从完整训练中心 coefficient 表计算。当前 batch 只用于选择训练预测路径；`source_eligibility_mask` 和 `all_center_beta` 定义完整的 source set。no-T2 中心在 edema 的 beta、SIP source set 和 loss 资格中被排除。

随后按 controller finding 修复了两个训练前硬门：BR2 representer 现在用非零 deterministic basis 加零初始化 residual adapter，available representer 的乘 beta 前 RMS 为 1，missing contribution 仍精确为 0，初始 BR2 输出仍等于 minimal；正式 `loss_no_t2_edema_safety` 解析权重已归零，并由静态 validator 拒绝 no-T2 edema loss 非零 known-bad。

本次追加修复 Batch7 专用 source-balanced sampler 硬门：正式训练 loop 在 `--batch7-source-balanced-pathology scar|edema` 下不再走旧 `batch_from_anchored_cases` complete/hardneg/random pool，而是使用 metadata.center 作为 training source，按合格中心的种子化均衡随机循环、中心内 uniform case、lesion/anchor-error patch 采样；edema pool 只包含 T2-present 中心。训练会写 `source_balanced_sampler_manifest.csv` 和 `source_balanced_sampler_summary.json`，并在中心 count 偏差超过 0.15 或 training_source 不是 `metadata.center` 时 hard fail。

本次还修复了 BR2 初始梯度链路：projection 继续严格 zero init，初始输出仍等于 minimal；beta 使用小的 signed deterministic 非零初值。staged-gradient 检查证明 step0 proposal loss 能到达 projection，模拟一次只更新 projection 后，同一 loss 能到达 beta 和 representer adapter。

正式六组 400 步 Slurm 训练、post-completion aggregation、validator、wiki/CURRENT 终态更新和本地轻量 commit 尚未完成。本文件不是 completion packet。

## 读取文件

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/FINAL_OUTPUT_READABILITY_POLICY.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `prompts/routes/handoffs/CURRENT.md`
- `wiki/README.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `.agents/skills/care-mapper/SKILL.md`
- `results/srr_production/code_maturity/batch7_br2_sip_comprehensive_architecture_audit_20260722.md`
- `docs/plans/laneB_round04_active_srr_batch7_minimal_pathology_decomposition_execution.md`
- `configs/srr_production/myops_batch7_minimal_decomposition.yaml`
- `prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_controller.md`
- `prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml`

## 修改文件

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/losses/srr_losses.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `scripts/evaluation/prepare_srr_batch7_minimal_decomposition_packet.py`
- `tests/srr_production/test_myops_batch7_minimal_decomposition.py`
- `results/20260722_srr_batch7_minimal_pathology_decomposition/*`

## 运行命令

- `./envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/tasks/20260722_srr_batch7_minimal_pathology_decomposition_executor_plan.yaml` -> pass
- `./envs/env_CARE/bin/python -m py_compile src/care_myocardium/models/srr_propref.py src/care_myocardium/losses/srr_losses.py scripts/training/run_srr_propref_myops_fold0.py scripts/evaluation/prepare_srr_batch7_minimal_decomposition_packet.py` -> pass
- `./envs/env_CARE/bin/python -m py_compile scripts/training/run_srr_propref_myops_fold0.py tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> pass
- `./envs/env_CARE/bin/python -m pytest tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> 15 passed
- `./envs/env_CARE/bin/python scripts/evaluation/prepare_srr_batch7_minimal_decomposition_packet.py` -> pass
- `./envs/env_CARE/bin/python scripts/training/run_srr_propref_myops_fold0.py ... --enable-batch7-decomposition-br2 --batch7-decomposition-use-sip --batch7-source-balanced-pathology scar --batch-size 1 --print-contract` -> pass

## 产物清单

- `center_modality_inventory.csv`: fold0 scope center/source inventory from metadata.
- `pathology_source_eligibility.csv`: full source/representer eligibility, including no-T2 edema exclusions.
- `resolved_stage_loss_weights.csv`: static loss authority table with legacy Pattern-SIP and generic dictionary losses at zero.
- `sip_formula_unit_tests.json`: full-center-table SIP diagnostics; batch-size-one batch proxy rejected.
- `source_learner_coefficients.csv`: initial full center coefficient table.
- `representer_scale_checks.csv`: available pre-beta RMS=1, missing contribution=0, initial BR2 delta=0.
- `br2_staged_gradient_checks.json`: projection-zero staged gradient chain evidence.
- `availability_mask_checks.csv`: hard availability mask by representer.
- `matched_run_manifest.csv`: static matching contract; runtime status still `NOT_SUBMITTED_STATIC_CONTRACT_ONLY`.
- Runtime `source_balanced_sampler_manifest.csv`: implemented in training loop; formal rows remain pending Slurm execution.

## 未完成事项

- Formal six matched 400-step Slurm runs are not submitted or terminal.
- BR2 no-SIP/SIP step-50 warmup sharing is not yet implemented as a runtime checkpoint split.
- Runtime gradient matrix, representer scale checks, beta hierarchy checks, availability mask checks, aggregation metrics, decision matrices, validator outputs, mapper final, wiki/CURRENT final state, and local lightweight commit remain pending.

## 需要人工批准的事项

None at this stage. Remaining work is same-scope executor implementation/runtime work.
