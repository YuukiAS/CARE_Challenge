# M10：SRR-v3 完整机制修复、因果归因与 Cine 时序模型

本文件是 GPT planner 为 M10 编写的独立暂存里程碑。它必须先保存在 `prompts/shared/M10_srr_v3_complete_mechanism_repair.md`。后续 Codex maintenance 步骤必须把 `Execution Contract`、`Controller Prompt`、`Executor Worker Contract` 和 `Mapper Contract` 合并到 `prompts/shared/EXECUTOR_PROMPTS.md`，把 `Reviewer Prompt` 合并到 `prompts/shared/REVIEWER_PROMPTS.md`，保留 `prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml`，确认合并无误后删除本暂存文件。

## Execution Contract

```yaml
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
task_type: milestone
milestone: M10
state: READY
planner: ChatGPT/GPT thread
controller: Codex controller session
executor: separate Codex executor subagent
mapper: separate read-only architecture mapper subagent
finalizer: deterministic FINALIZER_A and FINALIZER_B
validator: first-party fail-closed scripts
reviewer: separate_readonly
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
validation_packaging_allowed: false
validation_upload_allowed: false
hosted_metric_claim_allowed: false
fold_expansion_allowed: false
route_promotion_allowed: false
scientific_stop_allowed: false
```

### 前置审阅关口

执行前必须确认：

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md:
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
```

若精确 token 缺失、当前 HEAD 与任务读取基线不一致且未重新 grounding、工作树存在与本任务 source/write scope 冲突的未提交更改、或 Project route-diagram bootstrap 证据无法确认，立即写最小 blocked packet，状态为 `M10_BLOCKED_PREREQUISITE` 或 `M10_NEEDS_REVISION`；不得训练、不得自行改写路线。

### 路线图视觉读取凭据

```yaml
diagram_source: ChatGPT Project background materials
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
canonical_repo_paths:
  - images/SRR-v2.png
  - images/SRR-v2.5.png
  - images/SRR-v3.png
visual_read_status: READ_FROM_PROJECT_BACKGROUND
later_project_diagrams_found: []
```

恢复出的路线目标：MyoPS 必须以 availability-aware modality-specific encoders 和空间病灶条件检索为输入，在多尺度 shared/private/interaction representer bank 中检索解剖、scar 与 edema 证据；从真实 train/OOF 特征初始化并在线安全更新正负原型记忆；用 union/LV/RV、距离图、不确定性和心肌支撑生成 pathology-specific proposal；再由 scar 小 ROI 高精度 refiner 和 edema 大 ROI、T2 条件化 refiner 形成最终 SRR logits。nnU-Net 只允许作为 same-split baseline、detached context/teacher、uncertainty 或独立 safety comparator，不能作为 formal candidate 的最终 logits 底座。Cine 必须使用 ED/reference、非参考帧配准、帧质量/运动显著性、可学习 temporal dictionary 和时序聚合，不得继续使用 deterministic union proxy 冒充完整时序模型。

### history_files_read

```text
wiki/history/README.md
wiki/history/COMPARISON.md
wiki/history/M08/README.md
wiki/history/M08/ORIGINAL_ANALYSIS.md
wiki/history/M08/snapshot.yaml
wiki/history/M08/COMPONENTS.csv
wiki/history/M08/components/availability-no-t2.md
wiki/history/M08/components/retrieval-dictionary.md
wiki/history/M08/components/prototype-memory.md
wiki/history/M08/components/anatomy-prior.md
wiki/history/M08/components/proposal.md
wiki/history/M08/components/refiner.md
wiki/history/M08/components/arbitration.md
wiki/history/M08/components/losses.md
wiki/history/M08/components/checkpoint-selection.md
wiki/history/M08/components/cine-temporal.md
wiki/history/M08/components/training-evidence.md
wiki/history/M09/README.md
wiki/history/M09/ORIGINAL_ANALYSIS.md
wiki/history/M09/snapshot.yaml
wiki/history/M09/COMPONENTS.csv
wiki/history/M09/components/availability-no-t2.md
wiki/history/M09/components/retrieval-dictionary.md
wiki/history/M09/components/prototype-memory.md
wiki/history/M09/components/anatomy-prior.md
wiki/history/M09/components/proposal.md
wiki/history/M09/components/refiner.md
wiki/history/M09/components/arbitration.md
wiki/history/M09/components/losses.md
wiki/history/M09/components/checkpoint-selection.md
wiki/history/M09/components/cine-temporal.md
wiki/history/M09/components/training-evidence.md
```

同时已读取 `TODO-dictionary.md` 作为设计出发点；其结论不能覆盖 M9 follow-up 和当前 root wiki。最近提交检查至少覆盖 `20650aa`、`d82c647`、`9c89a9a`、`10878dc`、`9e2c84b`、`a08d7fe`、`00fa728`、`6b205e0`、`519368d`、`17d2cb0`。其中 `20650aa` 和 `d82c647` 强化了 M10 历史读取、controller continuity、mapper/wiki、FINALIZER_A/B、单 executor 计划与独立 reviewer 规则；`00fa728`/`6b205e0` 给出 M9 follow-up clean diagnostic-only token。

### M8/M9 问题到 M10 责任映射

M10 必须修复而不是重命名以下问题：

1. M8 的 final output 是 anchor-centered bounded residual，导致 SRR 容易退化为 nnU-Net identity；M10 formal output 必须以 proposal/refiner 形成的 SRR logits 为底座。
2. M9 去掉 anchor 底座后，主干 lesion formation 不够强；M10 必须同时增强空间检索、proposal、memory、refiner 和 full-volume calibration，不能只删除 anchor。
3. dictionary/router 仍偏 case/global；M10 必须实现 lesion-conditioned spatial routing，并逐 case/逐位置验证 invalid-slot weight 为零。
4. Pattern-SIP 是 alias/post-hoc summary；M10 必须实现训练时 pattern-conditioned integrativeness objective，不能复用 `dict_loss` 数值换名。
5. prototype bank 仍偏 buffer/helper；M10 必须使用 train/OOF provenance、EMA memory 加可学习残差，并让 similarity map 进入 proposal logits。
6. hard-negative replay 未闭环；M10 必须完成当前模型误报挖掘、安全过滤、memory refresh、继续训练和前后对比。
7. anatomy prior 对 proposal/refiner 的帮助未量化；M10 必须有真实 on/off intervention 和 final-logit effect。
8. refiner causal effect 文件过去只是 proxy；M10 必须在同一 checkpoint、同一病例、同一 decode 下做真实 toggle。
9. loss key 曾出现 wiring bug、alias 和 placeholder；M10 每个 loss 必须分类为 `real_optimized_loss`、`diagnostic_metric_only` 或 `disabled_with_reason`，禁止 placeholder zero loss 被算作完成。
10. checkpoint selection 不能再由 patch loss 主导；M10 必须在 scheduled checkpoints 上运行 metric-facing full-case evaluation，并分别执行 scar 与 edema hard gates。
11. patch training 与 full-volume topology 不匹配；M10 必须加入大上下文或 proposal crop、定期 full-case evaluation 和仅使用 train/val 的 pathology-specific calibration。
12. Cine 仍是 local deterministic proxy；M10 必须实现可学习 temporal dictionary/aggregation，保持 Cine 结论与 MyoPS 分开。

### 关键科学原则：先完整实现，再判断组件

M10 不允许在系统保真度未闭环时，根据某个组件的负 ablation 宣称它可替代、无效或应删除。组件审查必须分四层：

```text
L1 structural_fidelity: 是否按设计实现，而非名称、CSV 或 wrapper
L2 runtime_activation: 是否有非零梯度、非平凡输出、合法 availability mask 和真实数据来源
L3 final_output_effect: 开关该组件是否改变 intended cases 的 proposal/refiner/final logits 或 labels
L4 scientific_contribution: 在完整系统、充分训练、同一 split 和明确 control 下是否改善目标指标
```

只有 L1-L3 全部通过，才允许评估 L4。没有匹配容量的重训 control，不得使用 `replaceable` 结论。`component_contribution.csv` 的允许结论仅为：

```text
NECESSARY_SIGNAL
COMPLEMENTARY_SIGNAL
ACTIVE_BUT_NOT_BENEFICIAL
REDUNDANT_UNDER_CURRENT_CHECKPOINT
INCONCLUSIVE_NEEDS_MATCHED_RETRAIN
INCOMPLETE_FIDELITY_BLOCKER
```

### M10 完整架构合同

#### 1. Availability 与编码器

正式路径只消费实际存在的模态，禁止把缺失图像当作语义零图参与卷积。允许为张量批处理保留占位 storage，但每一层 private/interaction slot、prototype update、loss 和最终输出都必须由 availability mask 严格阻断。正式模态顺序必须单一来源定义并在 LGE/T2/C0、训练、评估和证据表中一致。

#### 2. 多尺度空间表示库

在至少三个 decoder-relevant scales 上实现：

$$
\mathcal D_\ell=\mathcal D^{\mathrm{sh}}_\ell\cup
\mathcal D^{\mathrm{LGE}}_\ell\cup
\mathcal D^{\mathrm{T2}}_\ell\cup
\mathcal D^{\mathrm{C0}}_\ell\cup
\mathcal D^{\mathrm{LGE,T2}}_\ell\cup
\mathcal D^{\mathrm{LGE,C0}}_\ell\cup
\mathcal D^{\mathrm{T2,C0}}_\ell.
$$

每个 representer 是有独立参数的轻量 residual convolutional adapter 或等价空间模块，private slot 只接收对应 modality-specific feature，interaction slot 只在两个输入均存在时运行。禁止 Lite 式 `[fused,fused,fused]` 复制。shared bank 负责可跨模态复用的心肌/形态表示；LGE-private 优先形成 scar 证据；T2-private 优先形成 edema 证据；C0-private 提供结构/边界支持；interaction bank 负责互补证据而不是简单拼接。

#### 3. Lesion-conditioned spatial router

router 输出必须是空间权重图而不是每个病例一个标量向量。对任务 $$t$$、尺度 $$\ell$$、位置 $$x$$ 和 slot $$k$$，query 至少包含局部 modality features、availability、proposal seed、$$P_{union}$$、$$P_{LV}$$、$$P_{RV}$$、心肌距离、局部不确定性、prototype similarity；使用 nnU-Net context 时必须 detached，并在证据中记录权重来源。router 输出 $$\alpha_{t,\ell,k}(x)$$ 必须在 valid slots 上归一化，invalid slot 的 max/mean weight 必须精确为零或在数值容差 $$10^{-7}$$ 内。

#### 4. Pattern-conditioned SIP

对 availability/center/style/hard-subgroup 组 $$g$$，记录：

$$
u_{t,k,g}=\frac{1}{|\Omega_g|}\sum_{i\in g}\sum_{x\in ROI_i}\alpha_{t,k}^{(i)}(x).
$$

共享 slot 的 integrativeness loss 约束其在多个合法组之间具有稳定复用；private/interaction slot 只在对应模态合法组中计算；同时用局部稀疏与 batch-level load-balance 防止所有位置挤到 shared slot。该 loss 必须有独立实现、独立梯度测试和独立日志，不能等于 entropy/coverage loss 或 `dict_loss` 的 alias。

#### 5. 真实原型记忆与 hard-negative 闭环

scar 与 edema 分别维护正原型和多类安全负原型。原型使用同一 split 的 train/OOF features 初始化，形式为：

$$
p_{t,k}=\operatorname{normalize}(p^{EMA}_{t,k}+\delta_{t,k}),
$$

其中 $$p^{EMA}_{t,k}$$ 是有 provenance/count/age 的安全 EMA memory，$$\delta_{t,k}$$ 是可训练残差。scar negative 至少覆盖 normal myocardium、blood pool、outside myocardium、LGE bright artifact、remote FP island；edema negative 只能来自 T2-present safe negatives。no-T2 myocardium 对 edema negative 的贡献必须恒为零。

prototype similarity 必须进入 proposal logits，而不只是 summary。完成第一阶段训练后必须用当前模型挖掘 remote FP/component-burden FP，安全过滤后刷新 memory，再继续训练并比较 refresh 前后 proposal、final logits、Dice、HD95、remote FP 和 component count。

#### 6. 解剖、proposal、refiner 与最终输出

内部 anatomy decoder 必须监督 union/LV/RV，并产生距离图、uncertainty 和 scar/edema soft gate。nnU-Net 可提供 detached context/teacher，但 formal candidate 的最终输出不得使用 `anchor_logits + delta`。

scar proposal 是 LGE-dominant、component-aware、小病灶高精度 proposal；edema proposal 是 T2-conditioned、大范围高召回 proposal，并在 no-T2 时从 loss、memory update、decode 和 export 四处阻断。proposal 进入 pathology-specific refiner：scar 使用紧致高分辨率 soft ROI，edema 使用更大上下文 soft ROI。ROI 是软权重，不得硬裁掉病灶外延。

最终 pathology logits 必须由 proposal 与 refiner 形成：

$$
z_t^{final}=z_t^{prop}+r_t\odot\Delta z_t^{ref},\qquad t\in\{scar,edema\},
$$

而不是以 nnU-Net logits 为底座。formal output 必须记录 `final_output_base=SRR_PROPOSAL_REFINEMENT`。允许单独导出 `nnunet_safety_comparator` 供 help/harm 分析，但不能静默替代 formal candidate。

#### 7. 损失合同

正式总损失至少包含 anatomy、scar proposal、T2-masked edema proposal、scar refinement、T2-masked edema refinement、prototype contrast/margin、safe memory alignment、hard-negative、Pattern-SIP、invalid-slot、ROI/anatomy prior、boundary/HD surrogate、full-output segmentation 和可选 detached-teacher consistency。每个 loss 必须记录配置权重、实际传入权重、raw value、weighted value、梯度范数和影响参数组。将任一权重从 $$0$$ 改为 $$10$$ 的 known-good test 必须改变 total loss 和目标参数梯度；alias 或 zero placeholder 必须 fail closed。

#### 8. checkpoint 与 calibration

patch loss 仅用于训练 sanity。checkpoint selection 必须在 scheduled checkpoints 上对完整 44-case same-split fold 运行 full-case evaluation，至少覆盖 16 个 T2-present/edema-positive 病例、CenterB 7 例、CenterC 9 例以及 no-T2 病例。scar 与 edema 分开形成 Pareto gate，记录 Dice、HD95、remote FP、component count、proposal lesion-wise recall/precision、ROI GT coverage 和 final-label delta。阈值 calibration 只能使用 train/validation split，不能使用 challenge validation、GT-aware decode 或 held-out test labels。

#### 9. Cine learned temporal branch

在 M9 `src/care_myocardium/cine/temporal_output.py` 的基础上新增真正的 learned temporal path。流程必须为：ED/reference 与关键帧选择；非参考帧到 reference 的 physical-space registration/warping；几何与配准质量矩阵；frame-wise anatomy features/logits；frame-quality 和 motion-saliency router；可学习 temporal representer dictionary；质量门控时序聚合；最终 compact-label output。允许使用经过验证的 ANTsPy SyNOnly/Demons 作为 registration candidate，但 deterministic union 只能是 control，不能是 formal output。必须在同一 12-case safe subset 比较 frame0、M9 deterministic proxy 和 M10 learned temporal output。

### 执行任务图

所有节点均为 blocking，按顺序执行；任何前置节点失败，后续科学节点不得启动。

1. `20260711_srr_v3_m10_architecture_fidelity`
   - result dir: `results/20260711_srr_v3_m10_architecture_fidelity/`
   - required: `result.md`, `architecture_fidelity_contract.md`, `component_activation.csv`, `loss_component_contract.csv`, `invalid_slot_runtime.csv`, `prototype_provenance.json`, `nnunet_role_audit.md`, `commands_run.md`, `MANIFEST.md`
2. `20260711_srr_v3_m10_mechanism_smoke`
   - result dir: `results/20260711_srr_v3_m10_mechanism_smoke/`
   - required: `result.md`, `one_batch_overfit.csv`, `gradient_effect.csv`, `proposal_refiner_sanity.csv`, `no_t2_safety.csv`, `known_bad_selftest.csv`, `commands_run.md`, `MANIFEST.md`
3. `20260711_srr_v3_m10_myops_full_train`
   - result dir: `results/20260711_srr_v3_m10_myops_full_train/`
   - required: `result.md`, `training_budget_ledger.csv`, `training_curves.csv`, `validation_events.csv`, `checkpoint_selection.csv`, `proposal_metrics.csv`, `same_split_help_harm.csv`, `hard_subgroup_metrics.csv`, `commands_run.md`, `MANIFEST.md`
4. `20260711_srr_v3_m10_hard_negative_refresh`
   - result dir: `results/20260711_srr_v3_m10_hard_negative_refresh/`
   - required: `result.md`, `hard_negative_mining_ledger.csv`, `memory_update_ledger.csv`, `refresh_before_after.csv`, `training_budget_ledger.csv`, `commands_run.md`, `MANIFEST.md`
5. `20260711_srr_v3_m10_no_nnunet_context_control`
   - result dir: `results/20260711_srr_v3_m10_no_nnunet_context_control/`
   - required: `result.md`, `training_budget_ledger.csv`, `checkpoint_selection.csv`, `same_split_help_harm.csv`, `nontrivial_signal_check.csv`, `commands_run.md`, `MANIFEST.md`
6. `20260711_srr_v3_m10_cine_learned_temporal`
   - result dir: `results/20260711_srr_v3_m10_cine_learned_temporal/`
   - required: `result.md`, `cine_training_budget.csv`, `cine_case_metrics.csv`, `cine_frame0_vs_proxy_vs_learned.csv`, `cine_registration_failure_matrix.csv`, `cine_final_output_manifest.csv`, `commands_run.md`, `MANIFEST.md`
7. `20260711_srr_v3_m10_component_causal_audit`
   - result dir: `results/20260711_srr_v3_m10_component_causal_audit/`
   - required: `result.md`, `component_interventions.csv`, `component_contribution.csv`, `refiner_true_toggle.csv`, `dictionary_router_interventions.csv`, `anatomy_prior_intervention.csv`, `memory_intervention.csv`, `final_label_effect.csv`, `commands_run.md`, `MANIFEST.md`
8. `20260711_srr_v3_m10_completion_check`
   - result dir: `results/20260711_srr_v3_m10_completion_check/`
   - required: `decision.md`, `required_output_check.csv`, `training_adequacy_check.csv`, `stale_status_scan.csv`, `validator_report.md`, `known_bad_selftest.csv`, `MANIFEST.md`
9. milestone/controller packet
   - result dir: `results/20260711_srr_v3_m10_complete_mechanism_repair/`
   - required: `result.md`, `controller_context.json`, `controller_ledger.csv`, `controller_bootstrap_snapshot.md`, `implementation_snapshot.md`, `finalizer_state.json`, `mapper_report_draft.md`, `mapper_report_final.md`, `architecture_delta_final.md`, `m10_system_summary.md`, `m10_component_contribution.csv`, `m10_myops_decision_matrix.csv`, `m10_cine_decision_matrix.csv`, `completion_check.md`, `review_request.md`, `MANIFEST.md`, `subagents/reviewer_prompt.md`

### 最低有效训练与持续执行预算

M10 的 controller 必须维持 durable continuity，不能在提交 job 后退出并把 monitor packet 当 completion。正式最低预算为：

```yaml
aggregate_min_train_loop_seconds: 36000
aggregate_target_controller_supervised_runtime_hours: 10
require_one_batch_overfit: true
require_prediction_sanity: true
require_loss_decrease: true
require_same_split_baseline: true
require_cache_isolation: true
require_metric_facing_checkpoint_selection: true
require_full_case_eval_cases: 44
myops_full_train:
  min_train_loop_seconds: 14400
  min_optimizer_steps: 40000
  min_validation_events: 20
  min_full_case_checkpoint_events: 8
  min_eval_cases: 44
hard_negative_refresh:
  min_train_loop_seconds: 7200
  min_optimizer_steps: 20000
  min_validation_events: 12
  min_full_case_checkpoint_events: 4
  min_eval_cases: 44
no_nnunet_context_control:
  min_train_loop_seconds: 7200
  min_optimizer_steps: 20000
  min_validation_events: 12
  min_full_case_checkpoint_events: 4
  min_eval_cases: 44
cine_learned_temporal:
  min_train_loop_seconds: 7200
  min_optimizer_steps: 5000
  min_validation_events: 12
  min_eval_cases: 12
```

每个单一 Slurm job 的 walltime 不得超过 8 小时。建议依赖链为：MyoPS full train（约 4 小时）→ hard-negative refresh（约 2 小时）→ no-nnU-Net-context control（约 2 小时）→ Cine learned temporal（约 2 小时）→ `FINALIZER_A`。这些 job 必须顺序执行，不允许把 MyoPS 与 Cine 并行化。若实际硬件吞吐导致达到 optimizer steps 早于 wall-clock budget，仍必须满足 train-loop seconds；early stop 只能在预先定义的 plateau/OOM/divergence 条件下触发，并将该 run 分类为 `SCIENTIFIC_UNDERTRAINED`，不能补写成功。

### 组件干预要求

完整系统通过 fidelity 和正式训练关口后，在同一 selected checkpoint、同一 44 cases、同一 decode 下运行：

```text
full_system
dictionary_static_bypass_same_checkpoint
spatial_router_to_global_same_checkpoint
prototype_similarity_off_same_checkpoint
anatomy_prior_off_same_checkpoint
scar_refiner_off_same_checkpoint
edema_refiner_off_same_checkpoint
both_refiners_off_same_checkpoint
nnunet_context_off_same_checkpoint
pre_refresh_vs_post_refresh
```

这些是 within-checkpoint intervention，用于判断 runtime 因果影响，不自动等价于匹配容量重训后的 replaceability。只有 `no_nnunet_context_control` 是本 M10 明确要求的 retrained scientific control。任何其他组件若需做“可替代”结论，必须返回 `INCONCLUSIVE_NEEDS_MATCHED_RETRAIN`，留给后续 GPT planner，不得在 M10 临时加训练变体。

### 科学判定门

M10 的 operational completion 不要求模型一定赢，但要求所有实现、训练与证据合同完整。机制信号仅在以下条件下成立：

- scar gate：同一 split 上 scar Dice 不低于 nnU-Net anchor，HD95 和 remote FP 不恶化，且至少一个指标严格改善；
- edema gate：T2-present/edema-positive Dice 与 HD95 不低于 anchor，CenterB 与 CenterC 无未解释伤害，no-T2 edema prediction 恒为零；
- proposal/refiner gate：proposal lesion-wise recall/precision、ROI coverage 和真实 refiner toggle 证明 proposal→refiner→final logits 的因果链；
- dictionary gate：空间 router、Pattern-SIP、prototype similarity 和 invalid-slot mask 全部有独立 runtime/gradient/final-output evidence；
- Cine gate：learned temporal output 在同一 12-case subset 相对 frame0 和 deterministic proxy 有可解释的 before/after 指标与 failure matrix。

若指标为负但实现保真、训练充分、证据完整，只能写 `M10_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`；不得科学停止。若实现保真未通过，则写 `M10_NEEDS_REVISION`，不能把结果解释为路线无效。

### 允许修改与新增的一方路径

优先修改：

```text
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/losses/srr_losses.py
src/care_myocardium/cine/temporal_output.py
scripts/training/run_srr_propref_myops_fold0.py
```

允许新增：

```text
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/cine/temporal_model.py
scripts/training/run_srr_v3_m10_complete_repair.py
scripts/training/run_cine_temporal_model_m10.py
scripts/evaluation/aggregate_srr_v3_m10_packet.py
scripts/evaluation/validate_srr_v3_m10_packet.py
jobs/src/run_srr_v3_m10_myops_full.sh
jobs/src/run_srr_v3_m10_hard_negative_refresh.sh
jobs/src/run_srr_v3_m10_no_context_control.sh
jobs/src/run_srr_v3_m10_cine_temporal.sh
configs/srr_v3_m10_complete_repair.yaml
src/care_myocardium/tests/test_srr_v3_m10_fidelity.py
```

可以根据当前 repo 结构调整新文件名，但必须在 `implementation_snapshot.md` 中给出旧路径→实际路径映射，不能借调整路径缩减责任。禁止修改 label mapping、官方 split、CARE evaluator、challenge validation data 或 submission logic。

## Controller Prompt

你是本 M10 唯一顶层 controller。先重新读取磁盘上的任务、当前 HEAD、`AGENTS.md`、agent-flow v2、Slurm routing skill、care-mapper skill、root wiki、M8/M9 history 和 M9 follow-up review token，生成 `controller_context.json`、bootstrap snapshot 与 append-only ledger。不要依赖本对话摘要。

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, mapper/wiki/fingerprint gates when architecture is affected, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.

严格按 executor plan 启动一个 executor，不得自行增加 executor/mapper 数量。executor 完成 architecture implementation snapshot 后，启动 mapper draft。只有 architecture fidelity 和 mechanism smoke 两个目录均通过 strict validator，才允许提交训练依赖链。

Slurm 默认使用 `htzhulab`；仅在 skill 允许时使用 `a100-gpu`、`volta-gpu` fallback 或 routing race。所有镜像 job 必须隔离 runtime/log/lock；一个镜像启动后取消仍 pending 的镜像并记录。提交 MyoPS full、refresh、no-context 与 Cine 的顺序依赖链，并用 `scripts/ops/submit_care_dependency_finalizer.py` 提交 `afterany` finalizer。finalizer 必须依赖全部 job IDs，而不是只依赖最后一个可能因 upstream failure 而永远不启动的 job。

controller 在 job pending/running 期间维护 durable continuity；`PENDING`、`RUNNING`、`COMPLETING`、`AWAITING_SACCT` 都是 `NEEDS_MONITOR`。若 dependency finalizer 失败，使用 namespace-local tmux watcher fallback，记录 session/PID/command/log/lock/result dir，并让 watcher 按 `finalizer_state.json` 状态继续。不得用提交回执、pending `squeue`、monitor packet 或 watcher setup 声称完成。

`FINALIZER_A` 必须收集所有 job 的 terminal state、exit code、elapsed、log/runtime paths，确认 runtime output 存在，执行 `aggregate_srr_v3_m10_packet.py`，运行 packet validator并写 `READY_FOR_MAPPER_FINAL` 或明确 failure。随后 mapper final 更新 root wiki、component table、architecture.yaml 和全部 canonical figures。`FINALIZER_B` 再运行全部 strict validators、Toolkit healthcheck、wiki history checks、`git diff --check`，只提交当前 M10 的轻量 source/config/helper/test/wiki/result packet。

controller report 在独立 reviewer 前必须保持：

```text
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
git_push_decision: SKIP_PUSH
next_required_action: separate reviewer writes review.md
```

写完 controller report 后停止。不得写 `review.md`，不得启动 M11，不得 push。

## Executor Worker Contract

你是 M10 executor，不是 planner、reviewer 或 controller。你必须完成上面完整任务图，不能把 TODO-dictionary 的四个标题直接变成四个浅层 variant，也不能只增加 slot 数、loss 名、CSV 或 wrapper。

先做当前代码审计，逐 symbol 证明 M8/M9 的真实路径，然后实现完整 SRR-v3 修复。正式模型必须使用 lesion-conditioned spatial dictionary、真实 train/OOF+EMA prototype memory、proposal/refiner final base、独立 loss wiring、full-case checkpoint selection。不要从头写一个简陋 U-Net 冒充修复，不要把 nnU-Net identity 包装成 safety，不要把 deterministic prototype、旧 mined CSV、global pooled gate、proxy causal table 或 zero loss 当正式实现。

在提交任何正式训练前必须完成：静态路径检查；invalid-slot unit/runtime test；loss weight/gradient test；prototype provenance 和 no-T2 safe-negative test；one-batch overfit；proposal/refiner 输出 sanity；full output 不等于 anchor identity；所有 required known-bad fixtures fail closed。若任何一项失败，写 `M10_NEEDS_REVISION` 并停止，不得用训练掩盖 wiring failure。

训练时只使用授权 split、缓存和输出目录。每个 run 的 checkpoint、prediction、NIfTI 和大日志留在 ignored runtime path；tracked packet 只记录轻量 MD/CSV/JSON。scheduled checkpoint 必须真实运行 full-case evaluation，不能训练结束后只比较 `checkpoint_best`/`checkpoint_final` 两个 patch-loss checkpoint。hard-negative refresh 必须由当前 run 的错误产生，并保留 case/source/category/T2 safety ledger。

正式 component audit 只能在完整系统通过 fidelity 后运行。对每个 intervention 记录 component、toggle、intended role、checkpoint、case count、proposal logit delta、refiner logit delta、final logit delta、changed label voxels、Dice/HD95/remote-FP/component delta、subgroup 和 interpretation。若只有 within-checkpoint intervention，必须标为 `INCONCLUSIVE_NEEDS_MATCHED_RETRAIN` 而不是可替代。

Cine 必须新增 learned temporal aggregation。若 registration 在某 case 失败，记录 failure matrix 并使用预先定义的 frame0 safety behavior；不得静默丢 case，不得把失败 case 从 denominator 移除。Cine 结果不能改变 MyoPS gate。

This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md. Do not write review.md, do not approve yourself, and do not start the next milestone; a separate read-only Codex reviewer must write review.md before continuation.

## Mapper Contract

你是 controller 内部独立 mapper。使用 `.agents/skills/care-mapper/SKILL.md`。draft 阶段读取实现 snapshot、source/config/entrypoint 和已有 runtime evidence，任何未证明路径保持 `partial/unverified`。不得训练、提交 Slurm、修改模型代码或写 review。

final 阶段在 `FINALIZER_A` 之后重新从当前 source 和聚合 evidence grounding。逐组件更新 `wiki/COMPONENTS.csv`、`wiki/architecture.yaml`、`wiki/MODEL.md`、`wiki/README.md`、`wiki/EXECUTION.md`、`wiki/LINEAGE.md` 和 model-current/model-gap/execution-flow 的 D2/SVG/PNG。每个组件必须记录 source/symbol、inputs/outputs、losses、final_output_effect、runtime evidence、fingerprint、M10 状态。不得因为文件存在而标 `implemented/verified`；只有 L1-L3 证据齐全才可 verified。

保持 M8/M9 history immutable，只追加 lineage/比较说明，不得覆盖原始分析。运行：

```bash
AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit \
  python scripts/architecture/run_toolkit_healthcheck.py --check
python scripts/architecture/generate_care_architecture_wiki.py
python scripts/architecture/generate_care_architecture_wiki.py --check-all
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
```

mapper report 只描述架构与证据状态，不决定 route promotion 或 scientific stop。

## Reviewer Prompt

你是独立只读 M10 reviewer。必须在 controller/executor 的轻量 final packet 已本地提交后启动。你的读取范围是本 M10 staging/merged prompt、上述九个 result directories、M10 一方 source/config/helper/test、root wiki、M8/M9 history 和 M9 follow-up review。你可以运行只读 strict validators，但不得修文件、训练、恢复 job、生成 wiki、打包 validation、upload、push 或启动 M11。

This is a separate read-only reviewer/auditor session. Do not fix code, do not generate missing artifacts, do not train, do not package validation, do not upload, and do not start the next milestone. Write only review.md with the controlled audit decision.

逐项审查：

1. exact M9 prerequisite token、diagram bootstrap、history_files_read、task graph 和所有 required result dirs/files；
2. controller/executor/mapper/finalizer/reviewer 分离，durable continuity、终态 Slurm accounting 与 post-job aggregation；
3. aggregate train-loop seconds 是否至少 36000，每个 run 的 steps/seconds/validation/full-case eval/case count 是否达到合同；
4. 是否真实实现 spatial router、Pattern-SIP、OOF+EMA+learnable-residual memory、hard-negative refresh、proposal/refiner final base和 learned Cine temporal；
5. formal final logits 是否仍暗中是 nnU-Net anchor identity；
6. no-T2 edema 是否在 supervision、memory、decode、export 全部阻断；
7. loss 是否存在 alias/placeholder/miswired，checkpoint 是否仍由 patch loss 主导；
8. component conclusions 是否严格区分 L1-L4，是否把 within-checkpoint toggle 错写成 replaceability；
9. same-split 44 cases、T2-present 16 cases、CenterB/CenterC、scar-positive、edema-positive、remote FP、small/large lesion、no-T2 safety 是否齐全；
10. Cine 是否真实使用非参考帧、registration evidence、learned aggregation、same-12-case comparison 和 failure matrix；
11. validator 是否扫描 MD/CSV/JSON、strict nonzero、known-bad 是否覆盖 missing outputs、stale pending、fake alias loss、deterministic prototype、global-only router、anchor identity、proxy causal table、frame0/union-only Cine、monitor packet completion；
12. wiki/source/evidence fingerprint、Toolkit healthcheck、generated figures和 local commit 是否一致。

以下任一情况必须拒绝 audited-go：缺 result dir/file；monitor/pending 状态；训练不足；runtime output 未聚合；只改名称或 CSV；global router 冒充 spatial router；Pattern-SIP 与旧 dict loss 数值相同/同图；prototype 没 provenance 或没进入 proposal；no-T2 进入 edema negative；proposal/refiner 不改变 final logits；nnU-Net 是 formal final base；proxy 表冒充 causal ablation；patch-loss checkpoint；Cine deterministic union/frame0-only；validator 非 fail-closed；mapper/wiki stale。

允许的 review decisions：

```text
M10_AUDITED_GO_MECHANISM_SIGNAL
M10_AUDITED_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED
M10_AUDITED_NEEDS_REVISION
M10_AUDITED_NEEDS_EVIDENCE
M10_AUDITED_NEEDS_MONITOR
```

`M10_AUDITED_GO_MECHANISM_SIGNAL` 只表示完整机制获得足够信号，允许 GPT/user 规划下一里程碑；它不授权 route promotion、fold expansion、validation packaging/upload、hosted claim 或 M11 自动执行。若完整实现和训练充分但指标仍为负，使用 `M10_AUDITED_COMPLETE_NO_PROMOTION_SCIENTIFIC_UNRESOLVED`，不得越权宣布 SRR 科学失败。
