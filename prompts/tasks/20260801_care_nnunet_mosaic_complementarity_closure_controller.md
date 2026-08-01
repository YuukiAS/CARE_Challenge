---
task_key: 20260801_care_nnunet_mosaic_complementarity_closure
task_kind: audit
task_type: frozen_same_case_nnunet_mosaic_complementarity_closure
status: AUTHORIZED_BY_USER
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: true
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
new_training_authorized: false
frozen_inference_authorized: true
one_gpu_inference_job_authorized: true
official_validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# nnU-Net 与 MoSAIC 同病例互补证据闭合 Controller

## Execution Contract

上一次四模型纠偏任务没有生成用户明确需要的第三项结果：**同一病例上，哪些错误由 MoSAIC 修复、哪些病例由 nnU-Net 保护、哪些病例两者都失败。** 这是 Planner 合同遗漏，不是执行者已经完成后又被追加的隐含要求。

本任务只补这一项证据，不重新训练任何模型，不设计下一代架构，不调阈值，不选择病例级部署模型，不访问隐藏测试标签，不上传 validation 或 Docker。

必须严格区分三类证据：

1. **Primary fair evidence**：220 例训练集上 `nnunet_oof` 与 `mosaic_clean_oof` 的同病例 held-out OOF 对比；这是唯一允许用于模型互补科学判断的主证据。
2. **Secondary in-sample mechanism diagnostic**：80 例 CenterB/CenterC 完整三模态病例上，nnU-Net OOF 与 MoSAIC repo-final/M10 full-data recipe 的同病例对比；只能解释 full recipe 改变了哪些错误，不能解释泛化或候选性能。
3. **Validation disagreement evidence**：15 例公开 validation 上冻结 nnU-Net 与 MoSAIC repo-final 的 fresh prediction disagreement；没有 GT，只能报告分歧，严禁写 help/harm、rescue 或优劣。

当前机器真值必须保持：

```text
FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE
M0R scar delta vs stock: -0.0020118904817150174
M0R pure-edema delta vs stock: -0.030114178203399733
M2 scar delta vs stock: -0.05011471399535905
M2 pure-edema delta vs stock: +0.018926404811234976, harm fraction 0.46875
```

本任务不得恢复任何 candidate 标签。

## Controller Prompt

### W0 — Bootstrap、同步与视觉门

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -15
git diff --check
```

若 main 落后且工作树干净，只允许：

```bash
git pull --ff-only origin main
```

不得 reset、clean、覆盖或 stash 用户改动。不得写 `/overflow/htzhu/CARE`。

完整读取：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/care-mapper/SKILL.md
.agents/skills/slurm-routing-partition/SKILL.md
```

视觉读取当前 ChatGPT Project 背景中的 `SRR-v2`、`SRR-v2.5`、`SRR-v3`。在 `controller_context.json` 中固定：

```text
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: PASS
recovered_route_objective: availability-aware evidence, shared/private/interaction representation, anatomy-guided pathology proposal, disease-specific refinement, negative-space control, and baseline safety
this_task_scope: evidence_only_no_architecture_design
```

### W1 — 冻结来源与人口语义

必须读取并绑定 SHA256：

```text
results/20260730_care_failure_forensics_deep_research_packet/standardized_casewise_metrics.csv
results/20260730_care_failure_forensics_deep_research_packet/standardized_model_summary.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_m0_m10_casewise.csv
results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_recipe_population_audit.json
results/20260730_care_failure_forensics_deep_research_packet/mosaic_recipe_decomposition_receipt.json
results/20260730_care_failure_forensics_deep_research_packet/case_oracle_summary.csv
results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json
results/20260731_care_metric_truth_reconciliation/metric_semantics_contract.json
results/20260801_care_four_lane_evidence_reconciliation/metric_contract.json
results/20260801_care_four_lane_evidence_reconciliation/all_outer_casewise.csv
```

必须机器核对：

```text
MyoPS total cases = 220
scar population = all scar-evaluable OOF cases, with positive-GT and all-case rows separately reported
pure-edema primary denominator = exactly 80 T2-present reliable-label cases
no-T2 cases cannot enter pure-edema positive/negative denominator
mosaic M0/M1 = clean held-out OOF evidence
mosaic M2-M10 = full-data recipe diagnostic only
case IDs are unique within model/pathology/evidence tier
```

若 core OOF 文件缺少任一病例、模型或病种，不得用 M10 替代，终态为 `OPERATIONALLY_BLOCKED_MISSING_CORE_CASEWISE`。

### W2 — Primary fair OOF complementarity matrix

实现：

```text
scripts/evaluation/complementarity/build_nnunet_mosaic_complementarity.py
scripts/validation/validate_nnunet_mosaic_complementarity.py
tests/complementarity/test_bucket_semantics.py
```

输入主表必须来自：

```text
model_id = nnunet_oof
model_id = mosaic_clean_oof
```

对 scar 与 pure edema 分别生成同病例宽表。每行至少包含：

```text
case_id
center
modality_pattern
T2_present
pathology
gt_positive
nnunet_dice
mosaic_dice
delta_mosaic_minus_nnunet
nnunet_pred_volume_mm3 or BOUND_METRIC_NOT_AVAILABLE
mosaic_pred_volume_mm3 or BOUND_METRIC_NOT_AVAILABLE
nnunet_components
mosaic_components
model_disagreement_dice
bucket
bucket_reason
source_row_hashes
```

若冻结原始预测 NIfTI 可被现有 manifest 精确定位，或能够由冻结 OOF checkpoint 在一个授权 inference job 内重新生成，则额外计算：

```text
HD95_mm
exact_HD_mm
lesion_recall
small_lesion_recall with lesion volume <1000 mm3
remote_FP_count and volume with distance >10 mm
blood_pool_adjacent_FP
```

若 raw prediction 无法绑定，不得伪造这些字段，也不得因此省略核心 Dice/component matrix；字段必须写成 `BOUND_METRIC_NOT_AVAILABLE`，并在 `physical_metric_extension_receipt.json` 说明资产搜索与重放结果。

#### 固定 bucket 规则

每个病例、每个病种只能进入一个 bucket，按以下优先级执行：

```text
1. BOTH_FAIL:
   max(nnunet_dice, mosaic_dice) < 0.40

2. BOTH_GOOD:
   min(nnunet_dice, mosaic_dice) >= 0.65

3. MOSAIC_RESCUES:
   mosaic_dice - nnunet_dice >= 0.05

4. NNUNET_PROTECTS:
   nnunet_dice - mosaic_dice >= 0.05

5. NEAR_TIE:
   abs(mosaic_dice - nnunet_dice) < 0.05

6. MIXED_TRADEOFF:
   all remaining valid rows
```

不得按最终结果重新移动阈值。不得把 `lesion_union` 当 `pure_edema`。

必须输出：

```text
results/20260801_care_nnunet_mosaic_complementarity_closure/oof_complementarity_casewise.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/oof_complementarity_bucket_summary.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/oof_center_subgroup_summary.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/oof_modality_subgroup_summary.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/oof_case_oracle_bounds.csv
```

Case-oracle只表示非部署上界：

$$
\Delta_{oracle}=
\frac{1}{N}\sum_i \max(D_i^{NN},D_i^{M})-
\frac{1}{N}\sum_i D_i^{NN}.
$$

严禁由此构造病例级 selector candidate。

### W3 — 80例 full-recipe diagnostic matrix

从 `v4_mosaic_m0_m10_casewise.csv` 提取：

```text
M0/M1 clean OOF
M10 repo-final/full recipe
80 complete-trimodal CenterB/CenterC cases
```

与同病例 `nnunet_oof` 连接，生成：

```text
results/20260801_care_nnunet_mosaic_complementarity_closure/m10_diagnostic_casewise.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/m10_diagnostic_bucket_summary.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/m0_to_m10_recipe_transition.csv
```

每一行必须带：

```text
evidence_tier = IN_SAMPLE_FULL_RECIPE_DIAGNOSTIC
trained_on_case_possible = true
not_valid_for_generalization_claim = true
```

不得把 M10 优于 M0 或 nnU-Net 的病例写成 held-out rescue。

### W4 — 15例 validation fresh disagreement

本任务允许本地冻结推理，不允许训练。

固定来源：

```text
nnU-Net: historical frozen 5-fold Dataset501 fullres ensemble and frozen production decode
MoSAIC: /users/a/e/aereinh/MoSAIC/code/source at commit d334bd1fb2a99dbbc230510590cd8e3ee08cc377 with repo-final MyoPS weights and decode
```

先检查是否已有本轮 fresh 15/15 outputs 且源 SHA、权重 SHA、输入 SHA 完全匹配。只有全部匹配时才可复用。否则触发一个且仅一个 frozen-inference job：

```text
partition: htzhulab
GPU: 1
CPU: 12
memory: 96G
time: 06:00:00
training: forbidden
threshold search: forbidden
checkpoint selection: forbidden
```

正式 wrapper必须使用：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

不得使用裸 `python`。若已有可用 interactive allocation，可用 `srun --overlap`；否则允许提交一个 `sbatch` frozen-inference job。必须由 `care_nnunet_mosaic_complementarity` tmux watcher持续到 terminal accounting、aggregation和validator，不能停在 submitted/running。

15例没有GT，输出只能包含：

```text
case_id
nnunet_scar_voxels
mosaic_scar_voxels
scar_intersection/union/disagreement
nnunet_pure_edema_voxels
mosaic_pure_edema_voxels
edema_intersection/union/disagreement
component counts
geometry equality
label validity
```

固定 validation 分歧 bucket：

```text
EXACT_OR_NEAR_SAME: pathology disagreement fraction <0.01
MOSAIC_ADDS_SCAR: mosaic-only scar volume > nnunet-only scar volume by >=1000 mm3
NNUNET_ONLY_SCAR_DOMINANT: nnunet-only scar volume > mosaic-only scar volume by >=1000 mm3
EDEMA_MAJOR_DISAGREEMENT: pure-edema disagreement fraction >=0.10
MULTI_PATHOLOGY_DISAGREEMENT: scar and edema both fail the near-same criterion
OTHER_DISAGREEMENT: remaining cases
```

这里严禁出现 `help`、`harm`、`rescue`、`better`、`candidate`。

必须输出：

```text
results/20260801_care_nnunet_mosaic_complementarity_closure/validation_disagreement_casewise.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/validation_disagreement_summary.csv
results/20260801_care_nnunet_mosaic_complementarity_closure/validation_frozen_inference_receipt.json
```

### W5 — Hard-case evidence packet

必须覆盖：

```text
Top 10 MOSAIC_RESCUES scar cases
Top 10 NNUNET_PROTECTS scar cases
Top 10 BOTH_FAIL scar cases
all pure-edema MOSAIC_RESCUES if fewer than 10, otherwise top 10
all pure-edema NNUNET_PROTECTS if fewer than 10, otherwise top 10
all pure-edema BOTH_FAIL if fewer than 10, otherwise top 10
CenterB/CenterC separate counts
small/multi-component scar subgroup
```

生成：

```text
hard_case_bucket_index.csv
hard_case_atlas.md
hard_case_visual_receipt.json
```

优先复用已绑定 V4 atlas与冻结图像，不得重新挑选病例来美化结论。若生成运行时PNG，保留在 Git忽略的 runtime目录，Markdown只引用相对 evidence path和hash；不得提交大量原始NIfTI。

### W6 — 科学判断

必须在 `complementarity_interpretation.md` 先回答：

1. 公平 OOF 条件下，MoSAIC 真正救了多少 scar / pure-edema 病例？
2. nnU-Net 保护了多少病例？
3. 两者共同失败集中在哪些中心、模态组合、病灶尺度或 component 模式？
4. case-oracle 增益有多大，是否足以支持未来学习型互补机制？
5. M10 full recipe 相比 clean OOF 改变了什么，但为什么不能解释成泛化？
6. validation 上两者在哪些病例明显分歧，但为什么无法判断优劣？

固定判断规则：

```text
ACTIONABLE_COMPLEMENTARITY_EVIDENCE:
- 至少一个病种的 fair OOF case-oracle Dice gain >=0.030
- 且 MOSAIC_RESCUES fraction >=0.10
- 且该病种 MOSAIC_RESCUES mean Dice delta >=0.10

LIMITED_COMPLEMENTARITY_EVIDENCE:
- 未达到 actionable
- 但至少一个病种的 fair OOF case-oracle Dice gain >=0.010
  或 MOSAIC_RESCUES fraction >=0.05

NO_USEFUL_COMPLEMENTARITY_EVIDENCE:
- 两个病种均未达到 limited
```

这只是下一次架构讨论的输入，不授权selector、ensemble、validation package或训练。

### W7 — Strict validator 与 known-bad

必须拒绝：

```text
结果包完全没有 MoSAIC 行却写 complete
M10/full-data病例混入 fair OOF 主表
M10病例被写成 held-out rescue
lesion_union 冒充 pure edema
no-T2病例进入 pure-edema denominator
同一case/model/pathology重复或缺失
bucket counts不等于有效病例数
只挑 top disagreement，不生成全病例矩阵
validation无GT却写 help/harm/rescue/better
bucket阈值在看结果后改变
voxel distance冒充mm
small lesion使用voxels而非<1000 mm3
case-oracle被包装成可部署selector
不同几何直接比较数组
fresh inference无terminal accounting
新训练或checkpoint修改
上传validation或Docker
CURRENT/wiki被前移成candidate
```

必须输出：

```text
strict_validator_report.json
known_bad_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

允许终态：

```text
ACTIONABLE_COMPLEMENTARITY_EVIDENCE
LIMITED_COMPLEMENTARITY_EVIDENCE
NO_USEFUL_COMPLEMENTARITY_EVIDENCE
OPERATIONALLY_BLOCKED_MISSING_CORE_CASEWISE
```

### W8 — Commit、push、通知

只允许写入：

```text
scripts/evaluation/complementarity/**
scripts/validation/validate_nnunet_mosaic_complementarity.py
tests/complementarity/**
results/20260801_care_nnunet_mosaic_complementarity_closure/**
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

不得提交 checkpoint、NIfTI、raw data、运行时PNG、大日志或secret。

终态完成后：

```bash
exec 9>/users/a/e/aereinh/.care-main-push.lock
flock -x 9

git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_nnunet_mosaic_complementarity.py --phase final
git diff --check
git commit -m "audit: close nnU-Net MoSAIC complementarity evidence"
git push origin HEAD:main
```

禁止force push和task branch push。验证local SHA等于remote main SHA。

随后写终态 `notification_brief.json` 并运行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

若 notifier 生成跟踪receipt，commit/push main并再次验证远端SHA。

## Executor Worker Contract

Executor只允许做冻结证据连接、必要的冻结推理、全病例互补矩阵、分桶、可视化索引与validator。不得训练、调阈值、创建selector或决定下一代架构。

## Mapper Contract

Mapper必须只读追踪：

```text
case/split -> frozen checkpoint/recipe -> prediction -> metric semantics -> complementarity bucket
```

并检查 fair OOF、in-sample M10与 no-GT validation 三层证据没有混写。Wiki只记录本任务证据终态，不得写候选或上传授权。