# Batch 4 独立规划审查

planning_review_decision: AUDITED_GO
planning_review_token: BATCH4_PLANNING_AUDITED_GO
reviewed_commit: 20e3aaf304f1687ba2e50c3885eb4bf88738d889
reviewed_at: 2026-07-21
review_role: independent_gpt_planning_critic
reviewed_prompt_path: prompts/tasks/20260721_srr_batch4_forced_fold0_training_controller.md
reviewed_plan_path: docs/plans/laneB_round04_active_srr_batch4_forced_fold0_training_execution.md
reviewed_config_path: configs/srr_production/myops_batch4.yaml
reviewed_executor_plan_path: prompts/tasks/20260721_srr_batch4_forced_fold0_training_executor_plan.yaml
reviewed_contract_git_blob_sha1: 469153163d24c2fb791ec0074119b596b7043106
critic_decision: READY_FOR_CODEX_MERGE
critic_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
blocking_findings: []

## 审查结论

同意启动 Batch 4 controller。该决定只授权合同内的接口修复、完整 176 例原型/记忆资产构建、同配置预检、一次 1800 步 MyoPS fold0 训练、三次完整 44 例评价、终态聚合和独立运行后审阅；不授权 Cine 训练、fold expansion、validation 打包或上传、hosted 指标主张、路线晋级、M11 或最终科学结论。

Batch 4 的训练设计能够针对 Batch 3A 暴露的主要断点：训练与推理 checkpoint schema 不兼容、不同模式使用不同 checkpoint、identity 导出绕过模型 logits、原型/记忆仅为少病例烟雾资产、训练病例覆盖不足，以及 patch loss 代替完整体积 checkpoint 选择。固定的 M10 D3 full-4scale 模型、176/44 划分、1800 optimizer steps、至少 1800 秒训练循环，以及 step 600/1200/1800 的三次 44 例评价，足以形成第一次可与 nnU-Net 同划分比较的受控训练证据。

## 已核对的硬门

1. 已视觉阅读项目材料中的 SRR-v2、SRR-v2.5、SRR-v3。计划保留模态专属编码、可用性感知检索、共享/私有/交互表示、病种专属候选区域、软区域细化、原型/记忆和 nnU-Net 有界安全基底，没有退化成普通 nnU-Net 后处理。
2. 唯一正式训练模型固定为 `m10_d3_hierarchical_memory_propref + full_4scale + base_channels=32 + anchor_bounded_srr_correction`；不得执行期降级为 tiny 模型。
3. 训练必须加载全部 176 个 fold0 训练病例，完整体积评价必须覆盖全部 44 个 fold0 验证病例。
4. 冻结原型/记忆必须只来自 176 个训练病例；验证病例泄漏、无 T2 病例贡献水肿正例或伪负例均须失败关闭。
5. 正式训练必须同时达到 `optimizer_steps >= 1800` 与 `train_loop_seconds >= 1800`；one-batch、短 smoke、启动失败、race loser、submitted、pending、running 或 monitor packet 均为零正式训练 credit。
6. step 600、1200、1800 均须保存可重载 schema-v2 checkpoint，并完成各 44 例 NIfTI 推理与公平评价。
7. 同一个选中 checkpoint 必须复用同一模型权重和同一原型/记忆资产，运行 identity、anchor-bounded、no-anchor 三种模式；不得重新初始化。
8. identity 必须从模型 logits/softmax 导出并满足标签逐体素一致与 softmax 最大绝对差不超过 `1e-6`，禁止 raw label 覆盖绕过。
9. checkpoint 选择固定使用病种平衡 Dice delta、平均 Dice delta、harm 病例数、HD95、远端假阳性和较早 step 的字典序；patch loss 仅作训练诊断。
10. `htzhulab -> a100-gpu -> volta-gpu` 竞速必须保持同一逻辑运行与相同代码、配置、划分和资产哈希，使用隔离 attempt 目录和原子 winner lock；V100 仅在同配置显存预检通过后加入。
11. 训练依赖使用 `afterok`；终态 accounting/finalizer 使用 `afterany`。controller 必须负责到所有 attempt 终态、聚合、strict validator、mapper final 和本地轻量 packet commit，不得提交 job 后退出。
12. controller、executor、mapper 和 finalizer 不得写运行后 `review.md`，不得 push，且不得作 hosted 或晋级主张；独立只读 reviewer 仍为终态硬门。

## 执行期强制解释

本审查通过不表示代码已经修好，也不表示训练可以绕过预检。Controller 现在可以进入 B4-01 至 B4-03，完成合同内接口修复、176 例资产构建和同配置预检；只有预检通过后才可提交 B4-04 Slurm 训练。预检失败不得把已授权训练降级回 smoke，也不得直接结束 Batch 4；应在既定写入范围内修复并重复预检。任何需要改变模型结构、数据划分、patch、loss、训练步数或科学选择的修改，才需要返回 GPT 规划者。

## Sprint 流程判断

当前门禁等价于一次独立 planning critic，而不是恢复旧 Route A/B/C 的多线程 planner–critic–integrator 流程。本次已在当前独立 GPT 线程完成，不应再要求第二个 planning critic。Batch 4 后续只保留两类独立监督：执行期间由 coordinator 持续核对 controller 与 Slurm 是否按合同运行；终态 packet 由独立只读 reviewer 审阅。小型同范围代码修复和 operational retry 不应重新触发规划审查。

## 最终决定

planning_review_decision: AUDITED_GO
planning_review_token: BATCH4_PLANNING_AUDITED_GO
reviewed_commit: 20e3aaf304f1687ba2e50c3885eb4bf88738d889
next_action: FETCH_ORIGIN_MAIN_AND_RESUME_BATCH4_CONTROLLER_FROM_B4_00
