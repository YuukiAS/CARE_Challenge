# CARE 当前开发状态

## 2026-07-29 当前最高优先级：CARE-PRISM v2 主干资产修复与继续执行

PRISM v2 前一 Controller 在 W1 训练前阻塞，原因是旧合同把强同折初始化错误限定为必须找到 ResidualEncoderUNet checkpoint。仓库历史资产已证明 Dataset501 标准 `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` 的 fold0–4 checkpoint 均存在并有路径、大小和 SHA256；它们也是本地公平 nnU-Net baseline 的真实来源。因此当前授权改为：按同折 `nnUNetPlans.json + checkpoint_final.pth` 动态恢复实际 stock nnU-Net network class，并以其 encoder 作为 PRISM 唯一共享主干。禁止随机 ResEnc、外部下载和 MMRD/Batch9 自定义 checkpoint 替代。

```text
state_id: care_prism_v2_stock_backbone_repair_20260729
active_development_branch: main
active_worktree: /users/a/e/aereinh/CARE
single_active_scientific_line: CARE_PRISM_V2_BACKBONE_REPAIR_W1_THEN_W2_W3
method_name: CARE-PRISM v2
execution_code: CARE-PRISM-V2-REPAIR-R0-R2
controller_is_coordinator: true
planning_review_required: false
review_required: false
fold1_outer_accessed: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
runtime_git_push_authorized: false
result_root: results/20260729_care_prism_v2_backbone_repair_and_resume
```

## 当前最高权威

```text
repair_amendment:
prompts/tasks/20260729_care_prism_v2_backbone_and_w1_repair_amendment.md

repair_executor_plan:
prompts/tasks/20260729_care_prism_v2_backbone_repair_executor_plan.yaml

repair_controller:
prompts/tasks/20260729_care_prism_v2_backbone_repair_controller.md

inherited_scientific_contract:
prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md
prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md
```

```text
549dc4aed1a74682f8d35932f3d4fc7b7d61f564  backbone/W1 repair amendment
1f1f39264cf248fb11d0322f41d4fe4c2aae021d  repair executor plan
acbc44cea3c3d86882cd56e5faab5b1d72b642c6  repair controller
```

冲突优先级：

```text
backbone/W1 repair amendment
> repair executor plan
> repair controller
> PRISM v2 hardening amendment
> PRISM base blueprint
> previous PRISM v2 blocked packet
> ARC and historical routes
```

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

来源：

```text
results/20260727_care_dg_dual_pathology_validation/nnunet_oof_anchor_manifest.json
results/20260722_care_myops_batch9_reliable_label_distillation/standard_nnunet_baseline_contract.json
```

历史 manifest 只作定位。Controller 必须对当前本地文件重新 stat/hash，并检查 repo path、`nnUNet_results` 环境变量和 repo-local symlink；不得再次只搜索名称带 resenc 的目录。

## 前一 blocked packet 的正确解释

```text
results/20260729_care_prism_fold0_fold1_v2
status: preserved as superseded W1 blocked provenance
scientific training credit: 0
fold1 outer accessed: NO
```

该 Controller fail-closed 行为是正确的，但“PlainConv checkpoint 不合法”这一合同判断已被 Planner 修正。当前不得再次以缺少 ResEnc checkpoint结束。

## W1 必须继续修复的实现漏洞

1. 当前模型虽然计算四层 routed/anatomy features，但最终 scar/edema refiner 只消费 level0，深层共享主干和多尺度 router 实际被绕过；必须实现真实 top-down 多尺度 anatomy 与 pathology decoder。
2. 当前 anatomy decoder 只是逐尺度 1×1 projection，且只从 level0 输出 logits，不是真实 decoder。
3. slice correspondence flag 当前是 no-op；正式冻结 identity 并诚实记录，除非真实实现和独立门通过。
4. dataset 当前 synthetic-only；必须接入 Dataset501 真实完整病例、split guard、center×burden×positive/safe-negative采样和增强。
5. 正式 `run_care_prism.py`、`evaluate_care_prism.py`、`validate_care_prism_packet.py` 尚缺失。
6. surface 与 lesion/MIL 当前是 placeholder；必须实现真实损失。
7. 四通道 negative logits 当前 target 全零；必须使用正常心肌、血池、union外背景和伪影/远端FP安全 masks，edema只允许T2-present negatives。
8. burden 当前是 auxiliary-only；必须以零初始化 FiLM 调制 proposal/refiner，或从方法中删除。
9. prototype保持默认关闭，不得阻塞核心模型；若启用才要求完整cross-case state。
10. no-T2 probability/mask/loss/gradient和checkpoint/resume必须通过严格known-bad。

## 修复与继续执行图

```text
R0 actual stock checkpoint locate/stat/hash and authority repair
→ R1 plan-driven stock nnU-Net reconstruction + W1 implementation closure
→ W2 400-step real-case zero-credit preflight
→ W3 fold0 6500-step all-checkpoint inner selection and one-time outer
→ only if W3 passes: W4 fold1 8000-step clean one-time outer
→ W5 terminal accounting / aggregation / validator / Mapper / local commit / email
```

共享主干验收提高为：

```text
parameter-byte coverage >=0.99
FP32 per-scale max_abs_error <=1e-6
all declared deep scales causally affect final logits
```

W3/W4性能门沿用 PRISM v2 原合同。实现、数据、OOM、cache、sampler、loss、resume、evaluation和validator问题必须由Controller在同一目标内修复；只有忠实实现、充分训练、全部checkpoint重载评价后仍未过门，才返回Planner。

## 资源与未授权边界

先检查既有 allocation `61220581 / htzhulab / g1807htzh01`。若仍运行，只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

禁止 `sbatch`、`salloc`、新Slurm job、并行GPU、写 `/overflow/htzhu/CARE`、runtime push、validation/Docker upload、fold1 outer调参或二次评价。Allocation终止时只记录精确resume point并返回 `OPERATIONALLY_BLOCKED`。