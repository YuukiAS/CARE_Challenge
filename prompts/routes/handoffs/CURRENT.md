# CARE 当前开发状态

## 2026-07-29 最新机器真值：CARE-PRISM v2 W3 足额完成，但 fold0 门失败，禁止进入 W4

CARE-PRISM v2 已从修复后的 fold0 stock nnU-Net checkpoint 重新完成 W1/W2，并执行 W3 fold0 6500-step formal v2。W3 训练本身、每 500 step checkpoint 审计、all-checkpoint inner selection、freeze receipt 和 fold0 outer 一次性评价链路完整；但是 frozen selected checkpoint 在 outer 上同时伤害 scar 和 edema-zone，相对同折 nnU-Net 明显下降，因此 W3 strict validator fail-closed，W4/fold1 clean training 不得启动，需返回 Planner 重新规划 calibration/refinement。

```text
state_id: care_prism_v2_w3_gate_failed_20260729
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_PRISM_V2_W3_RETURN_TO_PLANNER
method_name: CARE-PRISM v2
controller_is_coordinator: true
result_root: results/20260729_care_prism_v2_backbone_repair_and_resume
w1_w2_status: STRICT_PASS
w3_training_status: PASS_6500_STEPS
w3_inner_selection: PASS_ALL_13_CHECKPOINTS
w3_selected_checkpoint: results/20260729_care_prism_v2_backbone_repair_and_resume/runtime/fold0_w3_fold0_6500_formal_v2/checkpoints/checkpoint_step03000.pt
w3_selected_checkpoint_sha256: 33ce3dc6fa72b5bda9eca7489d01ec2ae12acf90edbba46eda3456ef5e5504e6
fold0_outer_accessed: true
fold0_outer_access_semantics: one_time_after_freeze
fold1_outer_accessed: false
w4_started: false
w3_strict_validator: FAIL
failure_classification: CALIBRATION
controller_verification_decision: NEEDS_REPAIR
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

关键证据：

```text
results/20260729_care_prism_v2_backbone_repair_and_resume/w1_w2_strict_validator_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_training_summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_checkpoint_audit_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_inner_select_formal_v2/summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/evaluation/fold0_w3_outer_once_formal_v2/summary.json
results/20260729_care_prism_v2_backbone_repair_and_resume/w3_strict_validator_report.json
results/20260729_care_prism_v2_backbone_repair_and_resume/controller_w3_return_packet.json
results/20260729_care_prism_v2_backbone_repair_and_resume/mapper_final_report.json
```

outer once selected checkpoint 结果：

```text
scar Dice: CARE-PRISM 0.4196441776 vs same-fold nnU-Net 0.5340911530, delta -0.1144469754, harm 37/44 cases
edema-zone Dice: CARE-PRISM 0.2471543848 vs same-fold nnU-Net 0.5592277699, delta -0.3120733851, harm 37/44 cases
remote_fp_count: 0 for scar and edema-zone
```

本状态覆盖下面旧的“自动继续 W3–W5”中间态。除非 Planner 明确授权新的 repair plan，不得继续 W4、不得访问 fold1 outer、不得重调 fold0 outer、不得上传 validation/Docker、不得作 hosted metric claim。

## 2026-07-30 最新机器真值：CARE-PRISM v2 持续 Controller，先修复 W1/W2，再自动继续 W3–W5

最新中间提交 `71717f0d7c6232cb8b68dd4d6442f8a5223ce297` 已解决同折 stock nnU-Net 主干定位、完整移植和 FP32 奇偶校验，并完成一次 400-step 真实病例 zero-credit 循环。Planner/Critic 随后发现标签语义、proposal/negative 直接梯度、anatomy exchange、负空间平衡、正式采样、exact resume、阶段训练、inner/outer lock、评价和 validator 仍未闭环。

用户现已明确授权：**Controller 不得再在修复中间态暂停等待人工验收。它必须在同一个 goal 内持续执行“实现—独立审计—修复—重跑”闭环；W1/W2 全部门独立通过后自动进入 W3，W3 通过后自动进入 W4，最终完成 W5。目标完整达到后推送轻量提交到 `origin/main`；目标真实阻塞时发送阻塞邮件。**

```text
state_id: care_prism_v2_continuous_controller_20260730
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_PRISM_V2_CONTINUOUS_W1_W2_REPAIR_THEN_W3_W4_W5
method_name: CARE-PRISM v2
controller_is_coordinator: true
planning_review_required: false
review_required: false
w1_intermediate_claim: REJECTED_PENDING_REPAIR
w2_intermediate_claim: REJECTED_PENDING_RERUN
w3_authorized_condition: W1_W2_INDEPENDENT_STRICT_PASS
w3_manual_planner_acceptance_required: false
fold0_outer_accessed: false
fold1_outer_accessed: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
terminal_verified_complete_push_authorized: true
terminal_email_on_verified_complete: true
terminal_email_on_true_block: true
result_root: results/20260729_care_prism_v2_backbone_repair_and_resume
```

## 当前最高权威

```text
continuous_controller:
prompts/tasks/20260729_care_prism_controller_v2.md

active_repair_controller:
prompts/tasks/20260730_care_prism_w1_w2_repair_controller.md

critic_repair_amendment:
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md

inherited_backbone_repair:
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml

inherited_scientific_contract:
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
prompts/tasks/20260729_care_prism_fold0_fold1_executor_plan_v2.yaml
```

```text
b8c373eab27a8a958e6b6731c867eb7087922fa7  continuous self-auditing controller
addb54793751699ba5515c2860830c40e37ba94d  W1/W2 repair and auto-continue controller
a76f3fd639ce09b900ce232bf65550fa4be37120  W1/W2 critic repair amendment
71717f0d7c6232cb8b68dd4d6442f8a5223ce297  rejected intermediate W1/W2 packet
```

冲突优先级：

```text
本 CURRENT 中的用户连续执行/终态推送授权
> updated continuous controller
> updated W1/W2 repair controller
> 20260730 W1/W2 critic repair amendment 的科学与实现要求
> 20260729 backbone/W1 repair amendment
> inherited executor plans
> PRISM v2 hardening/base blueprint
> intermediate W1/W2 packet
> previous blocked packet
> ARC and historical routes
```

`20260730_care_prism_w1_w2_critic_repair_amendment.md` 中“修复后返回 Planner”的中间停止要求已被本次用户授权覆盖；其标签、梯度、loss、采样、resume、评价和 known-bad 要求仍全部有效。

## 已验证可保留部分

- fold0/fold1 checkpoint 文件、大小和 SHA256 当前核验通过；
- 按 `nnUNetPlans.json` 恢复真实 `PlainConvUNet`；
- encoder 参数字节覆盖率 1.0，FP32 各尺度误差 0；
- 输入顺序 `[LGE,T2,C0]` 正确；
- pathology level1–3 干预会改变最终 logit；
- prototype 默认关闭，slice correspondence 冻结 identity；
- no-T2 前向概率和 mask 为零。

## 当前必须修复的问题

1. `edema_zone_target` 必须取 label 4 或 5；`myocardium_union` 必须为标签 1/4/5。
2. proposal/negative 未 detach 的直接 loss 必须进入总损失并对对应 head 产生直接梯度。
3. anatomy exchange 不得 gate/projection 双零初始化形成死分支，且必须单独验证。
4. scar 必须有真实 component/lesion-level 监督；scar/edema 必须有真实双侧 surface/distance loss。
5. 四类 negative 必须病例内平衡；edema negative 只允许 T2-present。
6. 必须使用 canonical metadata 的 center×burden×positive/safe-negative sampler。
7. 必须实现正式 exact resume，而非只检查 checkpoint key。
8. A/B/C/D 必须真实切换 active loss、冻结范围与 LR。
9. 必须实现 actual-train/inner-select/outer、all-checkpoint selection、freeze receipt 和 one-time outer lock。
10. evaluator 必须覆盖 Dice、HD95、exact HD、lesion recall、remote FP、component、volume ratio、help/harm 和同划分 nnU-Net。
11. W2 PASS 必须来自训练充分性证据，不得无条件写入。
12. known-bad 与 strict validator 必须能拒绝上述所有语义绕过。

完整科学要求见：

```text
prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md
```

## 持续执行图

```text
R3 semantic/data/loss/exchange/sampler/resume/evaluator repair
→ Controller independent code/tensor/gradient/known-bad audit
→ rerun W1
→ rerun W2 400-step zero-credit from fold0 stock checkpoint
→ independent strict W1/W2 gate
→ if PASS automatically start W3 fold0 6500 from fold0 stock checkpoint
→ every 500 steps continuous stage/loss/LR/sampler/gradient/reload audit
→ all-checkpoint inner selection and atomic one-time fold0 outer
→ only if W3 passes start W4 fold1 8000 clean
→ W5 terminal accounting / aggregation / strict validator / Mapper / CURRENT/wiki / lightweight commit
→ VERIFIED_COMPLETE only: push origin/main, verify remote SHA, send completion email
```

旧 W2 step400 checkpoint只能作为诊断，禁止续接 W3。标签、loss、sampler、architecture 或 stage 语义修复后，受污染训练必须从同折 nnU-Net 初始化重跑；纯启动/环境故障才允许 exact resume。

Controller 不能依赖 Executor 自产的 `PASS` 或单一 validator。每个 gate 必须同时具备：

```text
代码语义审计 + executable known-bad + 独立重载/重算
```

普通实现、数据、OOM、cache、sampler、augmentation、loss、resume、evaluation、validator和notifier问题必须在同一 goal 内持续修复。只有以下情况允许停止：

- 既有 allocation 或必要资产在所有合法定位后真实不可用；
- 缺少外部权限且无法在现有授权内解决；
- 必须改变冻结科学设计、数据划分、预算或 outer 语义；
- 忠实实现、充分训练、全部 checkpoint 重载评价后仍发生机制失败。

## 冻结同折主干资产

```text
fold0 checkpoint:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth
sha256: 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111
size_bytes: 357381749

fold1 checkpoint:
data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth
sha256: 5310569ff62f2f9a6ff2bc7dd3754404140071427a2025caf5e25d2916cfe400
size_bytes: 357381813

plans:
data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
```

## 资源、推送与邮件

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

禁止 `sbatch`、`salloc`、新 Slurm job、并行 GPU、写 `/overflow/htzhu/CARE`、validation/Docker upload、hosted claim和任何 outer 调参。Runtime 期间禁止 push。

只有 `controller_verification_decision: VERIFIED_COMPLETE`，且所有进程终态、aggregation、strict validator、Mapper、CURRENT/wiki、轻量 commit 全部确认后，才允许自动推送轻量代码与结果到 `origin/main`。不得推送 checkpoint、NIfTI、raw data、大日志、cache、secret或上传包。Push 后必须核对远端 SHA，再发送中文完成邮件。

若出现真实终态阻塞或忠实机制失败，同范围修复已穷尽并写好稳定阻塞 packet 后，发送一次中文阻塞邮件；修复中、submitted、pending、running、monitor或中间 PASS 不得通知。
