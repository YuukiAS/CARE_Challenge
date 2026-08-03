---
review_id: CARE_ASE_R2_EXTERNAL_GPT_INDEPENDENT_REAUDIT_ROUND2_20260803
reviewed_remote_main_sha: 4149c690ca646cede03cd4dff0145a71b9c6bf9a
reviewed_implementation_sha: e21a410d39e7d7e7c65ae566a62f13b0e06399fa
reviewed_review_request_sha: 5f20bdef2a62edfed147821018ee33b24d1560fd
independent_decision: PRETRAINING_EXTERNAL_REVIEW_REVISE
formal_training_authorized: false
formal_training_started_by_this_review: false
outer_access_authorized: false
review_scope: model_loss_target_sampler_checkpoint_resume_permit_lock_runtime_namespace_state_truth
---

# CARE-ASE 正式训练前独立复审

## 总体判断

当前版本仍然不能启动 fold1 / fold4 的 14,000-step 正式训练。架构主体没有再次降级成旧的简化版本：共享编码器、共享低中分辨率解码、解剖高分辨率路径、scar/edema 各自克隆的最高两级解码路径、独立命名证据投影和 no-T2 edema 子图排除都还在。但正式训练入口、合同绑定、checkpoint、精确恢复、物理 target 和采样语义仍存在直接错误；其中至少一项会让第一个正式 chunk 在保存 checkpoint 时必然失败，另一些会让错误 fold、错误合同或污染后的参数继续训练。因此本轮只能返修，不能签发训练许可。

本复审不是照抄已有 reviewer token，而是重新读取当前远端 main、当前正式入口和核心模型/训练源码后作出的独立结论。已有 `external_gpt_training_readiness_review_20260803.md` 的阻断方向成立；当前 main 没有出现关闭这些问题的新实现提交。

## 已直接确认的阻断问题

### 1. 第一个正式 checkpoint 会因合同哈希缺失而失败

正式入口调用 `save_care_ase_checkpoint(...)` 时没有传入 `effective_contract_sha256`。保存函数会把它写成 `UNSET`，而 `formal_resumable=true` 又明确拒绝该占位值。正式 chunk 每 1,000 步保存一次，所以代码可能先消耗约 1,000 个 optimizer steps，再在第一次保存时失败。

同时，v6 effective contract 曾在 `bd14fe5...` 加入，却又在实现提交 `e21a410...` 中删除。当前训练许可无法重新计算并绑定一个真实存在的唯一合同文件。

### 2. External permit 只检查字段存在，没有核验当前合同

`verify_external_review_permit()` 没有读取当前 effective contract、重新计算 SHA、比较 permit 中的值，也没有把合同纳入 critical-source manifest。任意非空的旧合同哈希仍可能通过 permit 入口，不能证明运行代码与被审阅合同一致。

### 3. Cross-fold resume 仍可混用

恢复路径只检查 global step 和少量历史无效 source SHA，没有强制比较：checkpoint fold、model config fold、stock checkpoint fold、split hash、actual-train case list、hard-negative manifest、area reference 和 effective contract。fold1 入口仍可能加载 fold4 checkpoint，再接 fold1 sampler 继续运行。

### 4. 所谓唯一 formal optimizer-step 并不覆盖完整正式管线

`run_formal_optimizer_step()` 只接收已经构造好的 microbatches。病例池选择、病例抽样、坐标抽样、数据读取、initial patch、stock augmentation、full-case target 切片和相应 RNG 消费都在函数外。这意味着 G2、atomic checkpoint probe、exact-resume oracle 与正式训练仍可走不同的数据路径。

该函数也没有逐 micro loss、梯度、参数和 Adam state 的 finite 检查；`clip_grad_norm_` 未启用 `error_if_nonfinite=True`，之后无条件 `optimizer.step()`。NaN/Inf 可以先污染参数和 optimizer state，再到后续步骤才暴露。

### 5. no-T2 的 step-0 parity 比较语义错误

当前 parity 把 stock class-4 logit乘以 availability 变成 0，再与 CARE-ASE 的约 `-1e4` 比较，并把该 0 放回六类 argmax。合同要求的语义应是双方共同从竞争集合中排除 class 4，只比较 `[0,1,2,3,5]` 的 decode，同时验证 edema-owned module call count 为 0。当前 PASS 不能证明 no-T2 解码等价。

### 6. Extent bias 仍会读取 padding 或全无效区域

`compute_slice_extent_statistics()` 虽支持 valid mask，但模型 `_extent_bias()` 调用时没有传入该 mask，model forward 也没有接收正式的 valid-spatial mask。并且 all-invalid fallback 最终会退回原始 `value.amax(...)`。从 ramp 开始生效后，padding 区域仍可能改变最终 scar/edema logits。

### 7. Full-edema 边界退化分支仍错误

`_edema_boundary_numpy()` 在整幅都是 edema 时返回 target=1、raw distance=0、valid=1。这相当于把没有可观察外边界的区域当成全部有效边界监督；应按完整病例上下文得到真实边界，无法观察时应为 target=0、raw=0、valid=0。

### 8. 物理距离 target 经过空间缩放后只插值，没有重新标定数值

signed endocardial/epicardial distance、component center 和 edema boundary 等连续 target 先在 full-case grid 计算，随后作为普通 regression maps 进入 stock spatial transform。旋转可插值，scale 不能只插值旧毫米值；尺度变化后距离数值本身也应变化。当前 target 与变换后 segmentation/effective spacing 不再严格一致。

### 9. Full-case target provenance 仍只是配方哈希

checkpoint 中的 target-cache manifest SHA 只绑定 builder 名称、case IDs 和 spacing source，不绑定每病例 segmentation SHA、properties SHA、shape、spacing、每个 cache array SHA 和 schema。当前 cache 还是进程内 LRU 临时生成；相同配方哈希可能对应不同实际 target arrays，无法支持精确恢复和审计。

### 10. Hard-negative OOF grid proof 仍有自证路径

`read_prediction_from_anchor()` 会在读取 probability artifact 后自行写入 `preprocessed_grid_binding=true` 和 array shape；随后 `probability_npz_exact` 又使用这些当前函数刚生成的字段证明 exact grid。原 anchor entry 未必提供独立的 per-case geometry 与实际生成 checkpoint 绑定。shape 不同分支也主要依赖 spacing/shape resampling，没有完整 orientation、crop bbox、round-trip 或 array-equality 证明。

### 11. Sampler 的 eligible-pool 与 fallback 统计可能名实不符

OOF/small-component eligible pool 为空时，代码退回整个 group；若抽到的病例没有对应坐标，descriptor 仍可能保留原 requested/within-focus 类别，而实际中心来自 GT component、remote background、wall 或其他 fallback。edema positive/boundary 等类别也没有统一的病例级 eligibility 过滤。因此采样账本可能声称完成某类 hard focus，实际没有。

### 12. Chunk lock 没有完整的 step ownership 和 heartbeat

lock owner 缺少 `SLURM_STEP_ID`，训练循环没有每 300 秒更新 heartbeat，live-owner 判断主要依赖 allocation job ID。stale recovery 采用普通 move 后重建目录，没有原子 recovery claim。具体 srun step 已死但 allocation 仍活时可能无法恢复；并发恢复也可能导致重复训练或覆盖。

### 13. 正式证据仍写入共享 preflight 目录

模型正式 runtime/checkpoint 使用 source-SHA-specific 目录，但 augmentation binding、parameter coverage 等文件仍写入固定的 `results/20260803_care_ase_r2_final_code_blocker_closure`。不同 source、smoke、preflight 和 formal run 可能覆盖或混用证据。

### 14. 当前机器真值仍停在 v5

`prompts/routes/handoffs/CURRENT.md` 与 `wiki/README.md` 仍把 CARE-ASE 写成 v5、implementation `f4ecd...`、review packet `51b9...`，没有反映 `e21a...`、当前外部复审或 `formal_training_authorized=false`。任何 Controller 若只读 CURRENT，会得到过期状态。

## 当前已保留、不得在返修中降级的部分

- 完整 stock encoder / bottleneck 与单次 shared low-mid decoder forward；
- anatomy、scar、edema 三条最高两级高分辨率路径；
- scar class-5 与 edema class-4 的单输出 stock classifier row；
- 每个病理、尺度、证据源独立的零初始化投影；
- scar 与 edema 的 modality-specific adapters 与约定 gate；
- no-T2 行不构造 edema-owned branch forward；
- Stage A/B/C 的 2,000 / 8,000 / 4,000 预算和 stage-local scheduler；
- 每个 optimizer step 四个 microbatches；
- full-case target-first、stock initial-patch augmentation 的总体方向；
- 14,000-step fixed checkpoint 和 fold1/fold4 的实验边界。

返修只能关闭上述 fidelity 缺口，不得通过删除 loss、减少 target、缩短训练、改回 complete-only sampler、取消 exact resume 或绕过 formal permit 来获得 PASS。

## 训练许可条件

只有同一个不可变 source SHA 同时满足以下条件，才允许再次提交外部训练前审阅：

1. 当前 main 中存在唯一有效的 effective contract，并被 permit、critical source manifest、checkpoint save/load/resume 共同重新计算和核验；
2. formal checkpoint 真实保存、SHA sidecar、reload 与跨 fold/source/contract known-bad 均 fail closed；
3. G2 使用与正式训练完全相同的 sampler→load→augment→target→forward→loss→backward→optimizer-step 函数；
4. non-finite、no-T2 五类 decode、padding/all-invalid extent、full-edema boundary、物理 target scale、OOF grid proof和 sampler fallback 都有真实 known-bad 回归；
5. fold1/fold4 真实 GPU fixture 重跑，augmentation RNG 发生并可精确恢复；
6. CURRENT/wiki 与新的 source/review packet/外部决定一致；
7. 外部 GPT 对该精确 source SHA 返回 `PRETRAINING_EXTERNAL_REVIEW_PASS`。

在此之前：

```text
formal_training_authorized: false
fold1_14000_step_started: false
fold4_14000_step_started: false
outer_access_fold1: 0
outer_access_fold4: 0
```

本轮不生成正式训练 Goal，也不签发 external PASS permit。