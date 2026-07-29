# CARE 当前开发状态

## 2026-07-30 最新机器真值：CARE-PRISM v2 W1/W2 需要修复，W3 未授权

最新中间提交 `71717f0d7c6232cb8b68dd4d6442f8a5223ce297` 已解决同折 stock nnU-Net 主干定位、完整移植和 FP32 奇偶校验，并完成一次 400-step 真实病例 zero-credit 训练循环。但 Planner/Critic 复核发现：当前标签语义、proposal/negative 直接梯度、anatomy exchange、负空间平衡、正式采样、checkpoint resume、阶段训练、inner/outer lock、评价与 W2 validator 均未达到合同要求。

因此当前状态不是科学失败，也不是可继续 W3，而是：

```text
state_id: care_prism_v2_w1_w2_critic_repair_20260730
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_PRISM_V2_W1_W2_REPAIR_ONLY
method_name: CARE-PRISM v2
controller_is_coordinator: true
w1_intermediate_claim: REJECTED_PENDING_REPAIR
w2_intermediate_claim: REJECTED_PENDING_RERUN
w3_authorized: false
fold0_outer_accessed: false
fold1_outer_accessed: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
result_root: results/20260729_care_prism_v2_backbone_repair_and_resume
```

当前最高权威：

```text
critic_repair_amendment:
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md

repair_controller:
prompts/tasks/20260730_care_prism_w1_w2_repair_controller.md

inherited_backbone_repair:
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml
prompts/tasks/20260729_care_prism_v2_backbone_repair_controller.md
```

```text
a76f3fd639ce09b900ce232bf65550fa4be37120  W1/W2 critic repair amendment
03a0690a74f48a5a38cb11913f091fdc272f3ae5  W1/W2 repair controller prompt
71717f0d7c6232cb8b68dd4d6442f8a5223ce297  rejected intermediate W1/W2 packet
```

冲突优先级：

```text
20260730 W1/W2 critic repair amendment
> 20260729 backbone/W1 repair amendment
> repair executor/controller
> PRISM v2 hardening amendment
> PRISM base blueprint
> intermediate W1/W2 packet
> previous blocked packet
> ARC and historical routes
```

## 已验证可保留部分

- fold0/fold1 checkpoint 文件、大小和 SHA256 当前核验通过；
- 按 `nnUNetPlans.json` 恢复真实 `PlainConvUNet`；
- encoder 参数字节覆盖率 1.0，FP32 各尺度误差 0；
- 输入顺序 `[LGE,T2,C0]` 正确；
- pathology level1–3 干预会改变最终 logit；
- prototype 默认关闭，slice correspondence 冻结 identity；
- no-T2 前向概率和 mask 为零。

## 当前阻断问题

1. `edema_zone_target` 当前只取 label 4，必须取 label 4 或 5；否则与 scar-in-edema soft relation 冲突。
2. anatomy union 当前使用 `seg>0`，错误包含 LV/RV blood pool；myocardium union 应为标签 1/4/5。
3. proposal/negative loss在外层总损失中使用 detached tensor，日志有数值但没有直接目标梯度。
4. anatomy exchange 的 gate 与 projection 同时零初始化，是永久零梯度死分支；当前 intervention 没有单独验证 exchange。
5. lesion MIL仍是病例级 max-BCE，surface loss不是正确双侧距离/边界监督。
6. 四类 negative 用全体积未平衡 BCE，`outside_union` 会支配训练。
7. training loop只是索引轮询；未执行真实 center×burden×positive/safe-negative采样，safe-negative bucket未使用。
8. checkpoint只检查key存在；没有正式 `--resume`，未恢复optimizer/scheduler/scaler/sampler/augmentation/RNG等并证明连续一致。
9. A/B/C/D只改变一个stage字符串；W3 optimizer、学习率、冻结范围与active loss没有按阶段切换。
10. dataset/evaluator没有 actual-train/inner-select/outer 三分、checkpoint selection、freeze receipt与one-time outer lock。
11. evaluator只做少量病例Dice；缺少HD95、exact HD、lesion recall、remote FP、component、help/harm和同划分nnU-Net比较。
12. W2 summary无条件写PASS；strict validator只覆盖W1，known-bad仅两项；没有验证两病理loss下降、真实机制梯度、采样平衡和exact resume。

完整修复要求见：

```text
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md
```

## 冻结同折主干资产

```text
fold0 checkpoint:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
sha256: 8bceb20cae8920e87d43b14665a0db9dfd4f1204533cd6e40ad9de74111
size_bytes: 357381749

fold1 checkpoint:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth
sha256: 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400
size_bytes: 357381813

plans:
data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

注意：fold0 SHA256 上一行若与 `backbone_asset_resolution.json` 不一致，以该 JSON 中完整值 `8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111` 为准；Controller修复CURRENT时必须消除该文本截断风险。

## 修复与继续执行图

```text
R3 semantic/data/loss/exchange/sampler/resume/evaluator repair
→ rerun W1
→ rerun W2 400-step zero-credit from fold0 stock checkpoint
→ strict W1/W2 validator and Planner-facing repair packet
→ only after explicit Planner acceptance: W3 fold0 6500
→ only if W3 passes: W4 fold1 8000 clean
→ W5 terminal aggregation / Mapper / local commit / email
```

旧 W2 step400 checkpoint只能作为诊断，禁止直接续接 W3。修复期间禁止访问 fold0 outer 和 fold1 outer。

## 唯一计算资源与权限

先检查既有 allocation：

```text
jobid: 61220581
partition: htzhulab
node: g1807htzh01
```

若仍运行，只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU、写 `/overflow/htzhu/CARE`、runtime push、validation/Docker upload、hosted claim和任何outer调参。普通实现、数据、OOM、cache、sampler、loss、resume、evaluation和validator问题必须在同一Controller goal内修复。