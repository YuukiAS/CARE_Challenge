---
task_key: 20260726_care_scf_v1
task_kind: scientific_milestone
task_type: care_selective_component_fusion_v1
controller_mode: coordinator_acceptance_owner
milestone_number: null
milestone_id: null
status: READY_FOR_CONTROLLER_AFTER_NNUNET5F_CONTROL
risk_level: high
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260726_care_scf_v1_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: none
reviewer: none
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: NOT_AUTHORIZED
experiment_adequacy_gate: "CARE-SCF v1 must use train-side OOF evidence, real frozen feature embeddings, component-level retain/suppress/replace decisions, and pathology-specific safety gates before packaging."
route_negative_gate: NOT_AUTHORIZED
scientific_completion_gate: "Controller may recommend whether the v1 candidate is worth one manual validation attempt, but upload remains user decision."
diagnostic_publication_gate: LOCAL_LIGHTWEIGHT_PACKET_ONLY
diagnostic_publication_scope: ["source/config/tests", "Markdown", "CSV", "JSON", "SHA256 text", "local package manifest"]
blocked_after_diagnostic_publication: ["validation_upload", "docker_upload", "hosted_metric_claim", "route_promotion", "scientific_stop", "git_push"]
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# 第 2 次：CARE-Selective Component Fusion v1

## Execution Contract

本任务生成第一个真正的 CARE-SCF validation candidate。CARE-SCF 不是 nnU-Net 与 MoSAIC 的简单类别拼接，也不是选择历史分数更高的模型。nnU-Net 和 MoSAIC 只能作为冻结 anchor / proposal source；最终候选必须由组件级检索证据、可靠标签约束和病种独立安全回退共同决定。最终产物是 `CARE-SCF-v1` upload-ready ZIP 和完整本地证据，供用户手动上传。

前置要求：第 1 次 control 包必须已完成，且存在：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/completion_check.md
results/20260726_care_fullinfo_nnunet_and_care_scf/nnunet5f_control/nnunet5f_package_manifest.json
```

如果前置不存在，停止为 `BLOCKED_NNUNET5F_CONTROL_REQUIRED`。不得跳过 control 直接包装 CARE-SCF。

本任务写入：

```text
results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/
results/submissions/care_myocardium_validation/workspaces/<timestamp>__CARE-SCF-v1/
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__CARE-SCF-v1/
```

## Controller Prompt

你是 CARE-SCF v1 的 Controller。启动前如果当前界面支持 Plan Mode，先进入 Plan Mode；若不支持，在 bootstrap 中记录原因。先同步 `origin/main`，读取第 1 次 control packet、MoSAIC fold0 公平复现证据、Batch10/Batch7/SCR-R1 历史结果、`third_party/MoSAIC/source/scripts/infer_and_submit.py`、`third_party/MoSAIC/source/myops/inference/`、submission 入口、Slurm skill 和 Mapper skill。Route A/B/C 只作为历史证据，不恢复分支开发。

CARE-SCF v1 的业务逻辑：

1. nnU-Net 5-fold ensemble 提供 myocardium / LV / RV anatomy、scar 和 edema probability、ensemble disagreement 或 entropy uncertainty，以及冻结 decoder feature representation。
2. full-data MoSAIC 提供 scar candidate probability/components 与 edema-zone candidate probability/components，但不拥有最终决定权。
3. SRR 思想只保留在组件级：正原型判断候选是否像真实 scar/edema，负原型判断是否像常见假阳性或安全负空间；决策单位必须是 connected component，允许 retain/suppress/replace；禁止 dense voxel-wise retrieval 直接生成整张 segmentation。
4. MMRD 思想保留为可靠标签约束：edema 原型、校准和评价只能使用 T2-present 且 edema label reliable 的训练病例；无 T2 病例不得作为 edema 强阴性；无 T2 推理不得由 CARE-SCF 新增激进 edema 组件；scar 与 edema 使用独立监督语义。
5. SCR 思想保留为病种独立安全回退：scar 与 edema 分开做组件决策；一个病种失败不能拖累另一个病种；组件证据不足、运行异常、几何异常或安全门失败时，对该病种 exact fallback 到冻结 anchor；fallback 必须有逐病例 receipt。

原型构建不能使用官方 validation 调阈值、建原型或选规则。必须从 220 个训练病例建立训练证据。nnU-Net 原型必须 cross-fitted：每个训练病例只能由 held-out fold 模型产生 OOF prediction 和 feature，禁止用训练过该病例的 fold 生成该病例原型证据。

scar 和 edema 分别构建 positive prototype bank 与 negative prototype bank。每个 prototype 至少记录 pathology、positive/negative、source case、source fold、center、modality availability、component id、embedding hash 和 GT relationship。禁止只用坐标、Dice 或手写规则冒充 representation prototype；必须至少包含真实冻结网络 feature embedding。

候选组件来自 nnU-Net permissive-threshold pathology candidates、nnU-Net argmax components、MoSAIC scar/edema candidates，以及必要时 anchor 周围低阈值 contiguous region。每个候选组件至少计算 nnU-Net mean/max probability、MoSAIC mean/max probability、nnU-Net uncertainty、myocardium overlap、myocardium shell distance、component size、compactness、positive prototype similarity、negative prototype similarity、positive-minus-negative retrieval margin、source agreement、scar/edema conflict。

可以使用低容量可解释线性分数或分段规则，但不得训练 MLP、Transformer 或新的深层 gate。参数和阈值只能由训练集 OOF 结果选择，小规模 grid 必须完整保存，不得根据官方 validation 成绩事后改阈值。

组件操作定义：

- retain：保留 nnU-Net 或双方一致且正原型证据充分的组件。
- suppress：删除负原型占优、远离 myocardium、极高 uncertainty 或明显 remote-FP 的组件。
- replace：当 nnU-Net 组件缺失或形状差，而 MoSAIC 候选具有强正原型证据、低负原型相似度并满足解剖约束时，用 MoSAIC 组件补充或替换。

最终标签规则：scar 优先于 edema；pure edema = accepted edema zone minus accepted scar；pathology 必须限制在合理 myocardium shell；不允许硬裁剪导致大规模真实病灶丢失；所有 suppress/replace 都要写组件级 decision receipt。

禁止“假 CARE”回退。必须生成 `mechanism_activation_audit.csv`，逐病例逐病种记录 anchor components、proposal components、retained/suppressed/replaced/added components、changed voxels、fallback reason、output hash、nnU-Net hash 和 MoSAIC hash。CARE-SCF 必须在训练 OOF audit 中真实触发非零组件操作，最终 candidate predictions 必须至少在部分病例上与两个 anchor 都不同。如果机制完全不激活，返回 `BLOCKED_MECHANISM_INACTIVE`。

评价按 pathology 分开。scar 报告 GT-positive 主 Dice、HD95、exact HD、precision/recall、help/harm、remote FP 和 component count。edema 主评价只使用 T2-present 且 reliable edema label 病例；无 T2 病例只报告 predicted edema volume、安全违规和新增组件，不进入主 Dice；同时报告 pure edema 和 edema-zone diagnostic，官方最终标签仍为 pure edema。

候选进入 upload-ready 的最低安全要求：

- scar：mean Dice 不得明显退化，HD95 不得恶化超过 anchor 的 5%，remote FP 不得显著增加，help/harm 必须逐病例报告。
- edema：T2-present reliable subset Dice 至少不低于 anchor，HD95 不得恶化超过 5%，无 T2 新增 edema 必须受严格限制，不得通过扩大 edema volume 虚增 recall。

允许最多两轮 repair，只能改组件阈值、prototype selection 或确定性后处理；不得扩展成新的大型训练任务。每轮必须保留前一轮结果。若两轮后仍未过安全门，状态必须是 `BLOCKED_CARE_SCF_NOT_SAFE_FOR_VALIDATION`，不得把 baseline 冒充 CARE-SCF。

如果安全门通过，使用与 control 完全相同的 Cine prediction tree，生成：

```text
results/submissions/care_myocardium_validation/upload_ready/<timestamp>__CARE-SCF-v1/CARE-Myocardium-OrganAgent.zip
```

本任务至少输出：

```text
care_scf_config.yaml
care_scf_prototype_manifest.json
care_scf_component_decisions.csv
care_scf_casewise_audit.csv
care_scf_geometry_audit.csv
care_scf_label_audit.json
care_scf_package_manifest.json
care_scf_zip_sha256.txt
care_scf_vs_nnunet5f_local_report.md
care_scf_vs_mosaic_local_report.md
validation_upload_instruction.md
mechanism_activation_audit.csv
oof_casewise_metrics.csv
oof_model_summary.csv
help_harm.csv
slurm_attempts.csv
strict_validator_report.json
controller_report.md
completion_check.md
```

Controller 最终回传必须先用中文回答：CARE-SCF 是否真实激活，是否退化成 anchor；正原型、负原型、retain、suppress、replace 是否都有真实证据；scar 和 edema 分别改善、持平还是恶化；哪些病例被帮助或伤害；CARE-SCF v1 是否值得占用一次 validation submission；两个 ZIP 路径；仍未授权的上传和 push。

完全结束、validator/aggregation/commit 状态确认后，写 `results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1/notification_brief.json`，并由既有 notifier 向 `1155246312@link.cuhk.edu.hk` 发送一封中文短邮件；不得在 submitted、pending、running、monitor 包或未完成 aggregation 阶段通知。

## Executor Worker Contract

Executor 实现并运行 CARE-SCF v1 的 OOF 原型、MoSAIC proposal 接入、组件候选生成、组件仲裁、病种 fallback、本地 OOF 评价、安全门、validation prediction 生成、package 和 validator。Executor 不能上传 validation，不能 claim hosted metrics，不能静默 fallback 后仍称 CARE-SCF，不能引入新大型训练。

## Mapper Contract

Mapper 必须核对 CARE-SCF v1 的真实生产调用图：nnU-Net 5-fold anchor/probability/feature、MoSAIC proposal source、cross-fitted prototype bank、component decision、pathology-specific fallback、official raw label export、same Cine tree 和 package 入口。若 wiki 更新会把未上传候选写成已验证 hosted 方法，必须拒绝；只能记录 `candidate_unreviewed_local_only` 或等价状态。
