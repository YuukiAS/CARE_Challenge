---
task_key: 20260726_care_mosaic_validation_gap_forensics_and_final_blueprint
task_kind: scientific_milestone
task_type: mosaic_hosted_gap_forensics_and_blueprint_adjudication
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: NOT_AUTHORIZED
experiment_adequacy_gate: "The task must resolve hosted-submission lineage as far as evidence allows, evaluate all 220 leakage-safe MoSAIC OOF cases with target-matched subgroups, decompose inference-recipe and target-domain effects, audit historical CARE components, rebuild the scar candidate dataset when the current one-component-per-case gate is scientifically insufficient, and produce one evidence-bound final blueprint plus a non-executed controller draft."
route_negative_gate: NOT_AUTHORIZED
scientific_completion_gate: "Completion requires a quantified attribution ledger with CONFIRMED/REFUTED/PLAUSIBLE_UNRESOLVED/NOT_IDENTIFIABLE statuses, reconstructed final-mask metrics rather than component-classification F1 alone, explicit residual uncertainty from the unlabeled 15-case validation set, and a deterministic final architecture decision rule. Validation and Docker upload remain user decisions."
diagnostic_publication_gate: LOCAL_LIGHTWEIGHT_PACKET_ONLY
diagnostic_publication_scope: ["source", "config", "tests", "Markdown", "CSV", "JSON", "YAML", "SHA256 text", "small plots"]
blocked_after_diagnostic_publication: ["validation_upload", "docker_upload", "hosted_metric_claim_without_lineage", "route_promotion", "scientific_stop", "new_slurm_allocation", "git_push"]
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# MoSAIC 本地—Hosted 排名翻转归因、CARE 历史机制复核与最终蓝图裁决

## Execution Contract

这不是继续执行已暂停的 `CARE-SCF-v1 / SafeScar` Step 4–5，也不是直接制作 validation 包或 Docker。当前任务的唯一目标，是在现有训练数据、15 例 validation 图像、220 例 MoSAIC OOF 资产、历史 CARE 预测和现有代码基础上，把以下三个问题尽可能做成可审计的科学闭环：

1. OrganAgent hosted scar `0.6965` 到底是否能被证明来自 MoSAIC；如果能，为什么 clean OOF 明显更差却在 hosted 上排名翻转；如果不能，必须停止把该行称为 MoSAIC。
2. Batch7、MMRD、SRR-Cascade/SCR 中哪些机制真实参与最终输出、哪些对病例外错误具有增量信息、哪些是因为评价或实现缺陷而被过早放弃。
3. `CARE-SER-Lite revised` 与完整双病理 `CARE-SER` 两份蓝图哪些部分成立、哪些需要删除或修改，并基于本任务证据生成唯一的最终 submission 蓝图和下一 Controller 草案。

本任务允许额外的诊断训练和推理，但只允许使用当前已经运行的交互式 Slurm allocation：

```text
job_id: 60657290
partition: htzhulab
node: g1807htzh01
job_name: CAREInteractive3d
```

严格禁止：

```text
sbatch
salloc
新 Slurm job
validation upload
Docker upload
根据 hosted 分数反向搜索阈值
恢复 Route A/B/C worktree
写入 /overflow/htzhu/CARE
```

若 Controller 已经位于 `SLURM_JOB_ID=60657290` 内，GPU 命令直接顺序执行；否则只允许用：

```bash
srun --jobid=60657290 --overlap --ntasks=1 bash -lc '<command>'
```

进入该既有 allocation。不得请求额外 GPU，不得并行运行两个 GPU 训练或推理进程。启动时必须用 `squeue` 和 `scontrol show job` 确认 job 仍为 RUNNING、节点仍为 `g1807htzh01`、剩余时间足够，并写入 receipt。若 allocation 终止，不得提交替代 job；保留完成波次并返回精确缺口。

本任务以最新远端 `main` 为代码真值。当前 `prompts/routes/handoffs/CURRENT.md` 与 `wiki/README.md` 尚未反映最新 `87b7592...` SafeScar Step3 pause 和 `16cda44...` leaderboard alignment，因此在本任务范围内视为 stale；本 prompt 的显式用户授权覆盖其中旧的 SCR-R1 单主线描述。Controller 必须在最终波次修复 CURRENT/wiki，但不得把未验证方法写成 hosted success。

### 必读

启动前同步 `origin/main`，并读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

视觉门已经由 Planner 在当前 ChatGPT Project 中完成，Controller 仍需在 bootstrap 中记录：

```text
diagram_versions_read:
  SRR-v2
  SRR-v2.5
  SRR-v3
  CARE-MMRD
  CARE-SRR-Cascade
  MoSAIC
visual_read_status: PASS_FROM_PLANNER_HANDOFF
recovered_route_objective:
  observed-modality evidence
  -> pathology-specific candidate/error evidence
  -> anatomy-aware selection
  -> bounded correction
  -> pathology-specific identity fallback
```

同时读取以下当前证据和蓝图：

```text
results/20260726_mosaic_fold0_fairness_reaudit/
results/20260725_care_myops_mosaic_fold0_reproduction/
results/care_scf/step3_safescar_gate_pause/
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/
results/leaderboard/care2026_validation_submission_alignment_20260726.md
results/20260724_care_myops_batch10_deadline_rescue/
results/20260722_srr_batch7_minimal_pathology_decomposition/
results/20260721_srr_batch7_mechanism_closure_repair/
results/20260724_care_myops_srr_cascade_submission_rescue/
results/20260725_care_myops_mosaic_fold0_reproduction/scr_r1_predictions/
prompts/blueprints/CARE_SER_Lite_revised_blueprint_20260726.md
prompts/blueprints/CARE_SER_dual_pathology_submission_blueprint_20260726.md
third_party/MoSAIC/source/scripts/infer_and_submit.py
third_party/MoSAIC/source/myops/
scripts/training/run_mosaic_oof_fold.py
scripts/inference/export_mosaic_oof_evidence.py
scripts/evaluation/build_care_component_dataset.py
scripts/evaluation/train_care_safescar_gate.py
```

## 核心科学边界

### Hosted 行的命名边界

当前 leaderboard 记录只证明：

```text
OrganAgent
2026-07-06 09:13:49
scar Dice 0.6965
```

仓库尚未证明这一行对应某个 MoSAIC ZIP。除非本任务找到可复查的 package、command、hash、timestamp lineage，否则所有报告必须称它为：

```text
OrganAgent hosted row 2026-07-06
```

不得称为“MoSAIC validation 0.6965”。

### 可回答与不可回答的边界

15 例 validation 没有 GT。本任务可以通过 package lineage、target-matched OOF、推理配方消融、validation 图像域相似度、15-case 重采样和预测风险模型大幅缩小解释空间；但如果缺少 exact upload lineage 或 validation GT，仍可能存在不可识别残差。最终 attribution 必须为每个假设标记：

```text
CONFIRMED
REFUTED
PLAUSIBLE_UNRESOLVED
NOT_IDENTIFIABLE_WITH_AVAILABLE_EVIDENCE
```

禁止用自然语言把“可能”包装成“已证明”。

## 需要裁决的七个假设

```text
H1: all44 mixed-modality fold0 低分主要由缺模态病例拖累，而 hosted 15 例完整三模态更匹配 MoSAIC。
H2: validation 的中心、风格或几何分布更接近 MoSAIC 优势训练子群。
H3: full-data training 与完整三模态病例数量带来真实目标域增益。
H4: TTA、coarse 版本、threshold、containment、component cleanup、largest-component 等 inference recipe 导致显著提升。
H5: 0.6965 hosted 行被错误归因给 MoSAIC，或对应的本地包并非当前假定配方。
H6: 15 例小样本波动足以产生 nnU-Net/MoSAIC 排名翻转。
H7: 本地 evaluator、标签语义、pure-edema/edema-zone 或 export 口径与 hosted 指标不一致。
```

每个假设必须输出：证据、反证、效应量、置信区间或不确定性、最终状态，以及对 Docker 选择的影响。

## Controller Prompt

你是本任务的 Controller/Coordinator 和 acceptance owner。使用一个 Executor，按 executor plan 严格顺序执行。你必须检查真实代码 diff、每个命令、现有 allocation receipt、训练/推理预算、metric population、checkpoint hash、decode rule 和 required outputs。Executor 不得自行宣布任务完成。普通代码或数据处理缺口在同一 scope 内退回 Executor 修复；任何新 Slurm allocation、validation upload、Docker upload、外部数据或扩大到新 backbone 必须停止并返回用户。

### W0：Bootstrap、状态冻结与现有 allocation 绑定

必须输出：

```text
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/controller_context.json
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/controller_ledger.csv
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/controller_bootstrap_snapshot.md
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/existing_allocation_receipt.json
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/stale_state_audit.md
results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/input_asset_manifest.json
```

要求：

- 记录开始 SHA、git status、pre-existing untracked 分类。
- 验证 `60657290` 的 state、partition、node、remaining time、CUDA、Python、torch、磁盘和结果目录可写。
- 禁止新 `sbatch/salloc`；known-bad 测试必须能拒绝包含这些命令的执行计划。
- 冻结 training split、220 case list、15 validation image list、nnU-Net/MoSAIC checkpoint hashes、metric implementation 和蓝图文件 hashes。
- 明确记录旧 SafeScar Step3 只完成 OOF、一个初版 component dataset 和二分类 gate；Step4/5 不得恢复。

### W1：Hosted submission lineage forensic

目标是把 leaderboard row 与本地 package 绑定到能够绑定的最高证据等级。

搜索范围只读：

```text
/users/a/e/aereinh/CARE/results/submissions/
/users/a/e/aereinh/CARE/logs/
/users/a/e/aereinh/CARE/results/
/users/a/e/aereinh/MoSAIC/
/users/a/e/aereinh/ 下与 CARE upload 明确相关的命令历史或日志
```

只能搜索 package 名、ZIP SHA、upload 命令、submission 时间和模型路径；不得收集或提交密码、cookie、token、完整 shell history 或无关个人内容。报告中对敏感值做删除。

输出：

```text
submission_lineage_ledger.csv
submission_lineage_evidence.json
hosted_row_claim_boundary.md
package_prediction_hash_matrix.csv
```

证据等级固定为：

```text
CONFIRMED_EXACT_ZIP_HASH
CONFIRMED_PREDICTION_TREE_HASH
CONFIRMED_COMMAND_AND_TIMESTAMP
LIKELY_TIME_ALIGNMENT
UNRESOLVED
REFUTED
```

必须特别裁决 `2026-07-06 09:13:49` 与 `2026-07-08 19:08:16` 两行。若不能达到至少 `CONFIRMED_PREDICTION_TREE_HASH`，后续不得把 `0.6965` 当作 MoSAIC 方法事实，只能用于 OrganAgent hosted boundary。

### W2：220-case canonical OOF 与目标匹配评价

现有 MoSAIC OOF no-leakage audit 已覆盖 220/220，但当前 tracked packet 没有提供完整最终 mask 性能归因。必须使用同一 canonical evaluator 重算。

模型至少包括：

```text
nnU-Net OOF
MoSAIC OOF scar exact current recipe
MoSAIC OOF raw scar before cleanup
MoSAIC OOF pre-largest-component scar
Batch7 minimal（可用病例）
Batch10 MMRD（可用病例）
SCR-R1 generic cascade control（可用病例）
```

同时检查 fold1–4 edema checkpoint 是否 full-budget；若存在，导出 leakage-safe MoSAIC edema OOF。若不存在或不完整，记录明确缺口，不得补一个短训版本冒充。

固定总体：

```text
scar all cases
scar GT-positive
scar complete C0+LGE+T2
scar LGE-only
scar C0+LGE
scar CenterB
scar CenterC
pure-edema T2-present reliable GT-positive
edema-zone T2-present reliable GT-positive
no-T2 safety only
fold0..fold4 separately
```

固定指标：

```text
Dice
leaderboard-compatible HD if implementation exists
exact HD
HD95
precision
recall
remote FP mm3
component count
volume ratio
empty prediction
case-wise help/harm
```

输出：

```text
oof_casewise_metrics.csv
oof_model_summary.csv
oof_subgroup_summary.csv
oof_fold_stability.csv
oof_pairwise_help_harm.csv
metric_semantics_audit.md
label_export_roundtrip_audit.json
complete_case_primary_report.md
mosaic_edema_oof_availability_audit.json
```

必须区分 all-case、GT-positive 和 reliable T2 population。任何 empty-safe 平均不得代替 pathology 主指标。

### W3：排名翻转归因——target domain、recipe、15-case sampling 与匹配训练

#### W3A：Exact inference recipe decomposition

在同一 OOF cases、同一 held-out checkpoints 上运行预注册 variants：

```text
R0 raw probability decode, no TTA, no anatomy containment, no cleanup
R1 + TTA
R2 + anatomy containment
R3 + class-specific small-component cleanup
R4 + largest-scar-component
R5 exact native hosted-style scar recipe
R6 exact locally reconstructed package recipe, only if W1 resolves package lineage
```

不得根据结果新增阈值。threshold 只允许使用 upstream config/default 和已解析 package 中的冻结值。

输出：

```text
inference_recipe_casewise.csv
inference_recipe_summary.csv
inference_recipe_factor_effects.csv
inference_recipe_attribution.md
```

#### W3B：Validation-domain similarity，无 validation GT

从 220 训练病例、完整三模态训练子集和 15 validation 图像提取不依赖 GT 的固定特征：

```text
shape/spacing/slice count
per-modality robust intensity quantiles
inter-modality alignment summary
nnU-Net anatomy/pathology volume and confidence
MoSAIC anatomy/pathology volume and confidence
model disagreement
frozen MoSAIC embedding summary
```

使用低容量、带正则的 domain classifier 和最近邻分析判断 validation 更像哪些训练中心或风格群。训练时不得读取 validation leaderboard 分数。输出 bootstrap 不确定性。

输出：

```text
target_domain_feature_manifest.csv
validation_nearest_training_cases.csv
domain_classifier_cv.csv
domain_similarity_report.md
domain_weighted_oof_summary.csv
```

#### W3C：15-case rank-reversal simulation

只在 complete tri-modal OOF 病例中重复抽取 15 例，至少 10,000 次；另做按 validation-domain similarity 加权的 10,000 次抽样。报告：

```text
P(MoSAIC Dice > nnU-Net Dice)
mean/median delta
2.5/97.5 percentiles
HD/precision/recall rank reversal probability
center-composition sensitivity
```

输出：

```text
rank_reversal_bootstrap.csv
rank_reversal_summary.json
rank_reversal_interpretation.md
```

#### W3D：两个 matched target-distribution diagnostic fine-scar runs

此分支用于测试“训练目标分布”而不是生产模型。启动条件精确为：

```text
60657290 remaining time >= 14 hours
fold0 cache/coarse predictions/checkpoints complete
至少 50 GiB 可写空间
```

若任一条件失败，写 `NOT_RUN_RESOURCE_OR_ASSET_GUARD`，不得用短训替代。

条件满足时必须从同一个保存的初始 FinePathNet state 开始，使用同一 fold0 176 train / 44 val、同一 frozen coarse predictions、同一 architecture、optimizer、augmentation seed、300 epochs、validation cadence 和 decode，仅改变采样：

```text
T0: upstream standard sampler
T1: complete-trimodal samples weight=4, other samples weight=1
```

两者均为 full-budget；部分运行零 credit。评价 all44 与 complete16。输出：

```text
target_weighted_training_contract.json
target_weighted_training_attempts.csv
target_weighted_training_summary.csv
target_weighted_casewise_metrics.csv
target_weighted_training_interpretation.md
```

不得把这两个 fold0 diagnostic runs 作为 final Docker 权重。

### W4：历史 CARE 实现与机制复核

分别审计：

```text
Batch7 / SRR
Batch10 / MMRD
SCR-R1 / SRR-Cascade
```

每个组件必须回答：

```text
代码是否存在
production forward 是否真实消费
loss/gradient 是否到达
checkpoint 是否实际加载
on/off 是否改变 final logits/labels
是否有同 split 公平指标
是否只是 nnU-Net clone/context
是否对 nnU-Net/MoSAIC 错误提供独立信息
适合保留为 proposal/feature/safety 还是应删除
```

必须复核已知问题：

- Batch7 不得仅凭与 nnU-Net 接近就宣称 retrieval 有效。
- MMRD 可靠标签语义与 distillation 增益需和弱病理头分开。
- SCR-R1 control/SRR 曾无条件读取相同 prototype maps；不得把 generic cascade control 的结果归因给 retrieval。
- 任何历史模型只有 fold0 预测时，结论必须标为 secondary diagnostic。

输出：

```text
historical_component_code_audit.md
historical_component_runtime_matrix.csv
historical_model_casewise_complementarity.csv
historical_error_correlation_matrix.csv
historical_component_keep_delete_table.md
```

另外做低容量增量 probe。候选特征组固定为：

```text
B0: nnU-Net + MoSAIC probabilities, uncertainty, anatomy, morphology
B1: B0 + MMRD reliable-label/teacher evidence
B2: B0 + SRR positive/negative retrieval margin
B3: B0 + Cascade support/correction evidence
B4: all available evidence
```

使用 case-grouped nested CV；只接受 reconstructed final-mask metrics，不接受 probe AUC/F1 单独作为机制成功。输出：

```text
historical_feature_probe_nested_cv.csv
historical_feature_probe_final_mask_metrics.csv
historical_feature_incremental_value.md
```

### W5：审计并替换当前不充分的 component dataset / gate

必须先写：

```text
current_step3_scientific_validity_audit.md
```

该审计至少验证：

- 当前 dataset 为 220 cases / 220 scar components，原因是否是 native final mask 的 largest-component cleanup。
- 当前 candidates 是否只来自 MoSAIC final scar mask，而不是 nnU-Net/MoSAIC/raw low-threshold union。
- `component_label_positive` 是否仅定义为“与任意 GT scar 有一个以上 voxel overlap”。
- 当前 F1 0.9427 是否未评价组件边界质量、Dice、HD、remote FP 或最终重建 mask。
- 当前 gate 是否只有 retain/suppress，没有 recover。
- 当前所谓 prototype similarity 是否来自手工 component feature 均值，而非冻结网络 embedding。
- 当前 Step3 PASS 是否不满足原 controller 对 real embedding、multi-source candidates、replace/recover 和 final-mask safety 的要求。

若上述任一成立，旧 gate 只能作为工程 smoke，不得晋级。

随后构建 `candidate_dataset_v2`。候选来源固定为：

```text
nnU-Net argmax scar components
nnU-Net permissive scar components at frozen thresholds 0.15/0.20/0.25/0.30
MoSAIC raw scar components before largest-component cleanup at frozen thresholds 0.15/0.20/0.25/0.30
MoSAIC final components
双方 agreement/overlap union
可用历史模型 scar components，单独标 source
```

同一病例内对 IoU >= 0.5 的候选做 deterministic merge，并保留 source bitmask。每个病例允许多个候选。

对每个候选做真实 counterfactual：

```text
remove from anchor
add to anchor
replace overlapping anchor region
```

计算对最终 mask 的：

```text
delta Dice
delta HD95
delta exact HD
delta precision/recall
delta remote FP
delta component count
delta volume ratio
```

动作标签或效用由这些 counterfactual 产生，不得再用“任意 GT overlap”代替。`recover` 只对 non-anchor proposal 开放。

训练三个预注册低容量 gate：

```text
G0 global all-220
G1 complete-trimodal only
G2 domain-weighted all-220
```

外层按原 nnU-Net/MoSAIC fold 分组，内层选择正则和 threshold。不得用 validation leaderboard。比较：

```text
no gate
suppress-only
retain/suppress/recover
without prototype features
with real frozen-embedding prototype features, only if embeddings complete
with each historical evidence group
```

输出：

```text
candidate_dataset_v2_receipt.json
candidate_components_v2.csv
candidate_counterfactual_metrics.csv
gate_nested_cv_summary.csv
gate_ablation_summary.csv
gate_reconstructed_casewise_metrics.csv
gate_reconstructed_model_summary.csv
gate_help_harm.csv
gate_scientific_decision.md
edema_error_predictability_and_feasibility.md
```

Scar gate 只有满足以下 complete-case OOF 门才可进入最终蓝图：

```text
mean Dice gain >= 0.010 over nnU-Net anchor
HD95 <= 1.05 * anchor HD95
no catastrophic exact-HD outlier introduced
help cases >= harm cases
remote FP not increased
non-zero suppress and/or recover activation
final reconstructed masks differ from both anchors on at least one held-out case
```

Edema 本任务只允许完成 OOF export、error predictability probe 和 blueprint feasibility。除非已有简单低容量 signed correction 在 T2-present reliable OOF 上达到：

```text
pure-edema Dice gain >= 0.010
edema-zone Dice gain >= 0.010
HD95 non-worse
no-T2 changed voxels = 0
```

否则最终蓝图固定使用 nnU-Net edema，不得启动新的四尺度 EdemaZoneErrorNet。

### W6：两份蓝图裁决与最终 Controller 草案

逐模块比较：

```text
CARE-SER-Lite revised
CARE-SER full dual-pathology
```

必须特别审查：

- 是否依赖尚未确认的 “MoSAIC hosted 0.6965”。
- OOF fold-model probabilities 与 full-data deployment probabilities 是否校准错位。
- MoSAIC proposal 是否错误使用 largest-component 后的 final mask，从而失去 recover 多病灶能力。
- scar 修改对 pure edema subtraction 的耦合。
- exact HD 是否被错误描述成 validation 可直接观测风险。
- prototype 是否有真实 embedding 与 matched control。
- edema 样本量是否支持 3D ErrorNet。
- Docker 内同时运行五折 nnU-Net、MoSAIC 和新网络的时间或显存。
- 回退是否是统一 identity，而不是大量不透明规则。
- 每个组件是否有独立病例外证据。

输出：

```text
blueprint_module_adjudication.csv
blueprint_adjudication.md
final_submission_blueprint.md
final_submission_controller_draft.md
final_submission_executor_plan_draft.yaml
```

最终架构状态只能是以下之一：

```text
NNUNET_ONLY_DOCKER
DETERMINISTIC_MOSAIC_SCAR_NNUNET_EDEMA
CARE_SER_LITE_SCAR_GATE_NNUNET_EDEMA
CARE_SER_LITE_DUAL
BLOCKED_HOSTED_LINEAGE_OR_EVIDENCE_UNRESOLVED
```

决策规则：

1. `CARE_SER_LITE_SCAR_GATE_NNUNET_EDEMA`：仅当 W5 scar complete-case OOF 门全部通过。
2. `CARE_SER_LITE_DUAL`：scar 门通过，且 edema 的两个 Dice 增益与安全门全部通过。
3. `DETERMINISTIC_MOSAIC_SCAR_NNUNET_EDEMA`：只有 W1 至少达到 `CONFIRMED_PREDICTION_TREE_HASH`，且 exact hosted-style complete-case OOF 满足 $$DICE_{MoSAIC}-DICE_{nnU\text{-}Net}\ge -0.01$$、$$HD95_{MoSAIC}\le 1.05\,HD95_{nnU\text{-}Net}$$ 时允许。
4. `NNUNET_ONLY_DOCKER`：custom/deterministic 候选均不通过，或 hosted lineage 未解决且 MoSAIC target-matched evidence 不足时。不得凭 leaderboard 传闻选择 MoSAIC。
5. `BLOCKED_HOSTED_LINEAGE_OR_EVIDENCE_UNRESOLVED` 只允许用于关键本地 package、prediction 或 OOF 资产本身缺失，导致任何候选甚至 nnU-Net fallback 都无法绑定或复算的异常情况；普通 hosted lineage 未解决不得阻止输出 `NNUNET_ONLY_DOCKER` 安全结论。

`final_submission_controller_draft.md` 只写下一任务，不执行、不打包、不上传；它必须绑定本任务选中的唯一架构、精确模型、权重、threshold、训练预算、existing evidence、Docker equality 和失败回退，不得留下 `choose best` 或 `if needed`。

### W7：归因结论、Validator、Mapper 与终态

必须输出：

```text
hypothesis_attribution_matrix.csv
mosaic_hosted_gap_root_cause_report.md
scientific_conclusion.md
implementation_snapshot.md
mapper_report_draft.md
architecture_delta_draft.md
mapper_report_final.md
architecture_delta_final.md
finalizer_state.json
strict_validator_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

`mosaic_hosted_gap_root_cause_report.md` 必须先用自然中文回答：

- 0.6965 是否已证明属于 MoSAIC。
- 排名翻转中，目标模态结构、validation 风格、full-data/selection、inference recipe、15-case sampling、metric/export 各自解释了什么。
- 哪些因素已确认，哪些仍不可识别。
- 现有 SafeScar Step3 gate 为什么足够或不足。
- Batch7、MMRD、Cascade 哪些思想值得进入最终 Docker。
- 两份蓝图最终保留、删除和修改了什么。
- 下一 Controller 应执行哪个唯一架构。

Strict validator 必须 fail closed，至少包含 known-bad：

```text
把 unresolved hosted row 写成 confirmed MoSAIC
使用 full-data checkpoint 评价训练病例却标 clean OOF
只有 component F1 没有 reconstructed mask metrics
one-component-per-case dataset 冒充 retain/suppress/recover candidate set
prototype feature 不是 embedding 却称 representation prototype
no-T2 参与 edema negative
根据 leaderboard 分数选 gate threshold
出现 sbatch/salloc/new job
monitor/running 状态写 VERIFIED_COMPLETE
CURRENT/wiki 仍指向旧 SCR-R1 或把候选写成 hosted success
```

Controller 完全结束、所有 GPU 命令已终止、aggregation、validator 和 local commit 完成后，才可写 `notification_brief.json`，由既有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件。不得为本任务创建新 notifier，不得在中间波次通知。

## Executor Worker Contract

Executor 只能在本 prompt 与 executor plan 的 write scope 内实现分析、评价、必要的两个 matched fold0 fine-scar diagnostic runs、candidate dataset v2、低容量 gate、蓝图裁决和证据文件。Executor 不能：

- 新建 Slurm allocation；
- 上传 validation 或 Docker；
- 根据 hosted 分数调参数；
- 继续旧 SafeScar Step4/5；
- 把 full-data contaminated 指标写成公平结果；
- 把 component classification F1 写成最终分割收益；
- 自行选择最终架构；
- push。

The Executor performs authorized implementation and commands but cannot declare the whole task complete. Return every wave to the Controller/Coordinator for diff, evidence, validator, runtime and contract verification.

## Mapper Contract

Mapper 读取最终代码调用图、结果 packet、两份蓝图和历史实现。它必须：

- 将最新 220-case OOF、SafeScar Step3 科学边界、leaderboard lineage 边界和最终蓝图决策写入 root wiki；
- 将 `CURRENT.md` 从旧 SCR-R1 单主线更新为本任务终态；
- 只把实际运行并有 final-output evidence 的组件标为 verified；
- 未执行的 final controller 草案保持 planned，不得写成 implemented；
- 不写 `review.md`，不做 hosted claim，不做 route promotion。

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, controller-as-coordinator diff inspection and repair loop, strict validators and known-bad regressions, minimum effective training when training is required, terminal accounting and post-completion aggregation for all commands run in the existing allocation, mapper/wiki/fingerprint gates, and SRR diagram-bootstrap evidence. If any hard gate fails, continue same-scope repair when authorized or stop with NEEDS_REPAIR/NEEDS_EVIDENCE; do not claim VERIFIED_COMPLETE.
