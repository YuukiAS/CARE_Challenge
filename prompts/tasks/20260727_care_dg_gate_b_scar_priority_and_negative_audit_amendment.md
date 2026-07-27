# CARE-DG Gate B 紧急修订：Scar 最终优先与负样本语义审计

本文件是 `20260727_care_dg_dual_pathology_validation` 当前 Gate B 运行的最高优先级同范围修订。它不改变 CARE-DG 主体架构、数据划分、loss 权重、训练总预算、candidate gate 或外部模型边界，只修复一个确定性的 scar/edema 组合语义错误，并补充不改变训练分布的 hard-negative 暴露审计。

继续遵守：

1. `prompts/blueprints/CARE_DG_dual_pathology_blueprint_20260727.md`
2. `prompts/tasks/20260727_care_dg_dual_pathology_validation_controller.md`
3. `prompts/tasks/20260727_care_dg_human_acceptance_email_gates_controller_prompt.md`
4. `prompts/tasks/20260727_care_dg_w2_fold0_critic_repair_amendment.md`

所有 GPU 工作仍只允许使用 interactive allocation `60657290`。禁止 `sbatch`、`salloc`、新 Slurm job、validation/Docker upload 和 runtime push。

## 一、立即处理当前 Gate B 运行

当前 repaired fold0 若仍在运行：

1. 在下一个已预注册 checkpoint 边界安全保存后停止 CARE-DG 训练进程；不得终止 allocation `60657290`。
2. 记录当前 stage、local step、total step、checkpoint 路径/SHA、训练曲线和进程 terminal receipt。
3. 将当前运行标为：

```text
PRE_SCAR_PRIORITY_HOTFIX_DIAGNOSTIC_ONLY
scientific_credit: 0
```

4. 不得把该 checkpoint 用于 repaired fold0 正式结果或 resume。
5. 若运行已完成但尚未形成 Gate B 邮件，同样将完整运行标为零科学信用并保留 provenance。

原因：当前 production 顺序为 scar correction 后再执行 edema correction，最终直接六类 argmax。正向 edema correction 可以在不降低 scar logit 的情况下超过 scar，违反冻结蓝图的 scar-priority composition。

## 二、固定唯一修复：Edema 先修正，Scar 最后拥有病理优先权

不得增加新网络、selector、组件模型或后处理器。只允许以下固定组合顺序：

```text
anchor logits
-> bounded edema-zone competitive correction
-> bounded scar competitive correction
-> final six-class argmax
```

形式化：

```text
after_edema = Correct(anchor, delta_edema, edema_support, pathology=edema,
                      competitors=anatomy classes)
final_logits = Correct(after_edema, delta_scar, scar_support, pathology=scar,
                       competitors=all non-scar classes including edema)
```

语义：

- edema branch 学习 injured-tissue zone，但不能在 scar branch 完成之后再次覆盖 scar；
- scar branch 最后执行，可保留、恢复或抑制 scar；
- 这不是冻结 anchor scar。若 scar branch 给出负修正，scar 仍可被改为 edema 或 anatomy；
- scar priority 指最终 scar branch 拥有最后病理类别裁决权，而不是无条件保留 anchor scar；
- `edema_zone = final_scar union final_pure_edema`；
- `pure_edema = edema_zone minus final_scar`；
- zero correction 仍逐体素等于 anchor；
- no-T2 edema correction 仍严格为零。

必须输出中间 tensor：

```text
after_edema_logits
final_logits_after_scar_priority
```

供 Gate B 机制审计使用。

## 三、必须新增的 scar-priority known-bad tests

至少加入以下测试并 fail closed：

1. `test_strong_edema_correction_cannot_overwrite_post_scar_decision`
   - 构造 edema-last 旧实现会把 scar 改为 edema 的 logits/delta；
   - 新顺序最终必须为 scar。
2. `test_negative_scar_correction_can_release_false_scar_to_edema`
   - 证明 scar priority 不是冻结 anchor scar；
   - scar branch 明确 suppress 时允许最终为 edema。
3. `test_scar_priority_preserves_edema_zone_union_semantics`
   - final scar 必须包含在 edema zone；
   - pure edema 与 scar 无交集。
4. `test_zero_correction_identity_after_priority_reorder`
5. `test_no_t2_identity_after_priority_reorder`
6. 旧的 edema-last composition fixture 必须被 known-bad validator 拒绝。

修复后运行完整 `pytest tests/care_dg -q`、Gate A known-bad、strict validator、consistency validator，以及 Stage A 1 step + Stage B 1 step 的零信用 preflight。新的 source/config/resolved-contract hash 必须全部冻结。

## 四、Hard-negative 当前只补审计，不改变采样合同

本轮不得临时改变预注册 50% error / 25% pathology / 25% random 比例，也不得根据 fold0 held-out 指标设计新采样器。

在 restarted fold0 开始前，对 Stage A 和 Stage B 各自固定抽取 1000 个 `random` mode patch，生成：

```text
random_negative_semantics_audit_stage_a.json
random_negative_semantics_audit_stage_b.json
```

每个 patch 至少记录：

- case ID、center、patch hash；
- center anchor class；
- patch 中 LV/RV blood-pool voxel count；
- patch 中 scar-support < 0.1 的 voxel count；
- patch 中 anchor scar FP voxel count（训练审计可用 GT，但不得作为模型输入）；
- patch 中 anchor edema-zone FP voxel count（只限 T2-present reliable cases）；
- patch 中 LGE standardized intensity >= 2.5 且 scar-support < 0.1 的 voxel count；
- 是否命中 blood pool、remote background、historical anchor FP、bright remote LGE island；
- ordinary-random 标记。

聚合报告各语义类别的 patch 比例。该报告只用于解释 fold0 remote FP/component/exact-HD，不作为当前训练输入或 checkpoint selection 条件。

预注册后续分支：

- 若 Gate B 中 remote FP、component count 或 exact-HD tail 安全，保持当前 sampler，不增加复杂度；
- 若出现明确 remote/component 恶化，且审计显示定向 hard-negative 暴露不足，则在 Gate B 人工验收后由 Planner 决定是否重训一个显式 hard-negative 版本；Controller不得自行改变采样。

## 五、重跑 fold0 与 Gate B 包

Scar-priority 修复、测试和零信用 preflight全部 PASS 后，不设置新的人工 Gate A。该修复属于确定性同范围 bug repair，Controller可以直接从原 seed 重新运行：

```text
runtime label: repaired_formal_scar_priority
fold: 0
Stage A: 5000 optimizer steps
Stage B: 3000 optimizer steps
```

旧 `runtime/formal`、`runtime/repaired_formal` 和所有 pre-hotfix 路径保持只读 provenance，不得覆盖或 resume。

完成 44 例 outer-held-out 和 16 例 complete-trimodal评价后，按原 Gate B 邮件门暂停 folds 1–4。Gate B 证据除原要求外必须新增：

- scar-to-edema 与 edema-to-scar conflict transition matrix；
- post-scar decision 被后续操作覆盖的 voxel count，必须为 0；
- scar-priority tests/known-bad receipt；
- random-negative semantics audits；
- scar、edema-zone、pure-edema component count；
- new infinite exact-HD case count；
- exact-HD tail 与 remote FP case list；
- 每个 help/harm case 的 changed components 和最远新组件距离。

Gate B 的判断边界：

- 不因单 fold 平均 Dice 暂时较低而自动终止；
- 但若存在 post-scar overwrite、new infinite exact-HD、明显 component explosion、远端 FP 灾难或机制近似 identity，必须在邮件中明确标为需人工决定/修复，不得自动启动 folds 1–4。

只有用户明确发送 `APPROVE_GATE_B` 后，才允许运行 folds 1–4。