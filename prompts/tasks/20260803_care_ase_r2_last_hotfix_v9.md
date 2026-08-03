---
task_key: 20260803_care_ase_r2_last_hotfix_v9
task_kind: hotfix
task_type: final_pretraining_and_deployment_fidelity_closure
controller_mode: controller_supervised
milestone_number: null
milestone_id: null
status: ACTIVE
risk_level: critical
route_change: false
scientific_decision_scope: none
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260803_care_ase_r2_last_hotfix_v9_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
route_promotion_gate: false
experiment_adequacy_gate: code_and_short_gpu_probe_only
route_negative_gate: false
scientific_completion_gate: false
diagnostic_publication_gate: true
diagnostic_publication_scope: lightweight_review_packet_only
blocked_after_diagnostic_publication: formal_training_outer_validation_upload_docker_upload
---

# CARE-ASE R2 最后一次训练前热修 v9

## 结论和边界

这是 CARE-ASE 正式训练前最后一次代码热修。不要重新设计模型，不要继续增加审计体系，不要用长训练调试，也不要把已经完成的 v8 工作重新跑一遍。

本轮只关闭当前 v8 源码中仍能直接确认的训练、续跑、采样、推理和部署阻断。完成后返回外部 GPT 做最后一次许可判断；本任务自身不得签发训练许可，不得访问 outer，不得启动 14,000-step 正式训练。

当前已审对象：

```text
v8 implementation Commit A:
648bb4d79da255438469aa9acfa939616aebf251

v8 review packet Commit B / origin/main:
8d01cd4c4a5caa3ab1eb44f365bd830a69a34664
```

v8 已完成的大部分正确实现必须保留：共享 encoder/bottleneck/low-mid decoder、anatomy/scar/edema 三条高分辨率路径、单行 pathology classifier、独立命名证据投影、no-T2 五类竞争、full-edema 退化边界修复、direct preprocessed-grid stock OOF producer、schema-4 checkpoint、canonical full-volume inference 入口和正式 runtime 类。

本轮不得把任何功能删除、绕过或降级来获得 PASS。

## Execution Contract

```yaml
task_key: 20260803_care_ase_r2_last_hotfix_v9
task_kind: hotfix
task_type: final_pretraining_and_deployment_fidelity_closure
status: ACTIVE
risk_level: critical
route_change: false
scientific_decision_scope: none
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260803_care_ase_r2_last_hotfix_v9_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
formal_training_authorized: false
formal_training_started: false
outer_access_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
```

成功终态只能是：

```text
PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY
```

不得输出：

```text
PRETRAINING_EXTERNAL_REVIEW_PASS
FORMAL_TRAINING_AUTHORIZED
W3_STARTED
OUTER_READY
VALIDATION_READY
DOCKER_READY
```

## 一、启动和重新落地

仓库：

```text
/users/a/e/aereinh/CARE
```

远端：

```text
YuukiAS/CARE_Challenge
```

分支：

```text
main only
```

执行：

```bash
cd /users/a/e/aereinh/CARE
source .care-codex-env.sh
source env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch origin main --prune
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
git status --short --branch
git log --oneline -15
```

最新 `origin/main` 必须是 `8d01cd4...` 的后继，并包含本任务文件。不要回滚其后的提交。不要写 `/overflow/htzhu/CARE`，不要创建 route/task/codex 分支，不要修改 Docker submission 邮件、Drive、challenge upload 或历史 route 结果。

必须读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/handoffs/CURRENT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
routes/README.md
wiki/README.md
```

以及：

```text
prompts/blueprints/CARE_ASE_R2_effective_contract_v8_20260803.yaml
prompts/tasks/20260803_care_ase_r2_final_pretraining_closure_v8_addendum.md
results/20260803_care_ase_r2_final_pretraining_closure_v8/**

src/care_myocardium/models/care_ase.py
src/care_myocardium/training/care_ase_runtime.py
src/care_myocardium/training/care_ase_trainer.py
src/care_myocardium/training/care_ase_sampler.py
src/care_myocardium/training/care_ase_augmentation.py
src/care_myocardium/inference/care_ase_r2_decode.py
src/care_myocardium/inference/care_ase_r2_full_volume.py
scripts/training/care_ase/run_care_ase_r2_chunk.py
scripts/evaluation/care_ase/build_stock_oof_preprocessed_grid_predictions.py
scripts/evaluation/care_ase/build_care_ase_r2_hard_negative_manifest.py
scripts/evaluation/care_ase/build_care_ase_r2_full_case_target_manifest.py
scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py
jobs/care_ase_r2/run_fold_chunk_htzhulab.sh
tests/care_ase/**
```

读取：

```text
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

Planner 已视觉读取：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-ASE
```

恢复的最终模型目标：

```text
完整 stock nnU-Net 成熟全体积能力
+ scar 的 LGE 主导证据
+ pure-edema 的 T2 主导证据
+ C0 弱支持
+ anatomy/context/component/extent 结构监督
+ no-T2 五类竞争和 edema 子图排除
+ single end-to-end checkpoint
+ 14,000-step fixed staged training
+ exact resume
+ canonical full-volume inference
```

## 二、绝对禁止回退

不得：

- 增加 Transformer、Mamba、第二个 backbone 或第二个完整 U-Net；
- 增加局部 crop/refiner、ensemble、selector 或 largest-component-only 后处理；
- 删除现有 loss、component、context、geometry、boundary 或 extent 监督；
- 缩短未来正式 14,000 optimizer steps；
- 改变 Stage A/B/C 的 2,000/8,000/4,000；
- 改变每 optimizer step 四个 microbatch；
- 恢复多输出 pathology classifier 死参数；
- 恢复 stock class4/5 normal-forward fallback；
- 将 no-T2 edema 映射成 background；
- 使用 v5/v6/v7/v8 diagnostic checkpoint 开始正式训练；
- 访问 outer；
- 运行 2,000-step chunk 或 14,000-step training；
- 用静态 JSON、文件存在或 synthetic mock 冒充真实代码通过。

## 三、统一创建 v9 合同

创建：

```text
prompts/blueprints/CARE_ASE_R2_effective_contract_v9_20260803.yaml
```

v9 完整继承 v8 模型、loss、split、stage、optimizer、decode 和评价边界，但必须删除 v8 中互相矛盾的 5/20-step 描述，并统一冻结：

```yaml
probe_budget:
  namespace: 20260803_care_ase_r2_last_hotfix_v9
  max_reserved_optimizer_steps: 10
  max_completed_optimizer_steps: 10
  reservations_are_atomic: true
  failed_or_cancelled_reservations_are_not_reusable: true
  reserve_before_materialization_or_forward: true

v8_status: superseded_by_v9_final_hotfix
v8_formal_training_credit: zero
v8_diagnostic_reservations: 20
v8_diagnostic_reservations_count_against_v9: false
```

v9 是后续 permit、critical-source manifest、checkpoint 和 resume 的唯一合同。v8 合同保留历史，不得删除。

## 四、P0：正式 runtime 的动态写入和连续 chunk

当前 `care_ase_runtime.py` 仍把多项动态证据写入固定、已被 Git 跟踪的 v8 review 目录。正式第一个 chunk 运行后会污染 worktree，后续 permit 的 clean-worktree 检查可能拒绝第二个 chunk。

必须将路径拆成：

```text
STATIC_REVIEW_INPUT_DIR
  只读：v9 tracked manifests、runtime input bundle、permit inputs

FORMAL_RUNTIME_DIR
  results/20260803_care_ase_r2_formal_training_<implementation-short>/runtime/fold_<fold>/

PROBE_RUNTIME_DIR
  /users/a/e/aereinh/.tmp/codex-CARE/20260803_care_ase_r2_last_hotfix_v9/
```

正式模式下以下内容全部只能写 `FORMAL_RUNTIME_DIR`：

```text
environment manifest
hardware receipt
critical source runtime manifest
augmentation receipt
parameter registry
sampler receipt
training log
lock/heartbeat
checkpoint/sidecar
reload receipt
checkpoint verified receipt
RNG transparency
chunk terminal/failure receipt
```

禁止正式模式写：

```text
results/20260803_care_ase_r2_last_hotfix_v9/ tracked review packet
results/20260803_care_ase_r2_final_pretraining_closure_v8/
任何共享 RESULT_DIR
```

clean-worktree 检查必须：

1. fail closed 检查 critical source、contract、tests、static manifests 和 tracked files；
2. 明确允许当前 source/fold 的正式 runtime namespace；
3. 不得因为 authorized runtime checkpoint/log/lock 是 untracked 而拒绝下一 chunk；
4. 其他任何 dirty/untracked path 继续拒绝。

推荐实现：

```text
critical_worktree_dirty_paths(authorized_runtime_root)
```

不要简单关闭 clean-worktree 检查，也不要忽略整个 `results/`。

新增测试：

```text
tests/care_ase/test_formal_runtime_writes_only_fold_runtime.py
tests/care_ase/test_next_chunk_accepts_authorized_runtime_outputs.py
tests/care_ase/test_dirty_critical_source_still_rejected.py
tests/care_ase/test_fold_runtime_namespace_isolation_v9.py
```

## 五、P0：修复 canonical full-volume inference 的双重计数

当前 `predict_care_ase_r2_full_volume_logits()` 对每个 tile 的共享 `count` 增加两次，导致 base logits、p_wall 和 extent evidence 被错误除以约 `2N`。

重构聚合逻辑：

```text
每个 tile：
  base += tile_base
  p_wall += tile_wall
  extent_component += tile_extent
  count += 1   # 只能一次

最后：
  average = sum / count
```

`_aggregate_patch_tensor()` 不得隐式修改全局 count，或只允许一个明确调用修改 count；禁止同时 helper + 手工各加一次。

新增强测试，禁止继续用全零模型掩盖问题：

```text
tests/care_ase/test_full_volume_nonzero_single_tile_exact_value.py
tests/care_ase/test_full_volume_nonzero_overlap_average.py
tests/care_ase/test_full_volume_extent_nonzero_expected_value.py
tests/care_ase/test_full_volume_tiled_whole_parity_nonconstant_model.py
```

测试模型必须输出已知非零、位置相关 logits、p_wall 和 extent evidence，并验证数值，不只验证 shape 或两个同样错误的路径互相一致。

outer evaluator 和未来 Docker 只能 import canonical module，不得另写第二套 sliding-window。

## 六、P0：训练 resume 必须独立绑定 requested fold 的 stock checkpoint

禁止继续：

```text
从待恢复 payload 的 config.checkpoint_path
-> 计算 expected SHA
-> 再验证同一个 payload
```

正式 runtime 必须从 requested fold 独立推导：

```python
CAREASEConfig.for_fold(requested_fold).checkpoint_path
```

并核对：

```text
payload.fold
payload.config.fold
payload.config.checkpoint_path
payload.stock_checkpoint_sha256
磁盘 canonical checkpoint SHA
requested fold
```

正式 runtime 必须调用：

```text
load_care_ase_checkpoint_for_training_resume(...)
```

或等价的单一权威 API。删除 runtime 中由 `prior_payload` 生成 expected SHA 的路径。

`_write_full_reload_receipt()` 也必须接收显式 requested fold、canonical stock checkpoint 和显式 hard-negative manifest path，不得回到默认 v8 manifest。

新增：

```text
tests/care_ase/test_runtime_uses_training_resume_loader.py
tests/care_ase/test_resume_expected_stock_not_from_payload.py
tests/care_ase/test_cross_fold_resume_path_and_sha_spoof_rejected_v9.py
tests/care_ase/test_reload_sampler_uses_explicit_manifest_path.py
```

## 七、P0：full-case target manifest 必须在正式 materialization 中真实核验

当前 formal runtime 不能只检查 manifest 文件存在。

扩展 full-case target manifest，每个病例绑定：

```text
case_id
image_path/image_sha256
segmentation_path/segmentation_sha256
properties_path/properties_sha256
plans_path/plans_sha256
shape_zyx
spacing_zyx
cache_schema
每个 target array SHA
full_cache_payload_sha256
```

Runtime 初始化时解析 manifest并验证：

```text
schema
task key
fold
payload SHA
case set == actual-train case set
```

每病例第一次 materialize、在任何 forward 和 probe reservation 前验证：

```text
image SHA
segmentation SHA
properties SHA
plans SHA
shape
spacing
现场 build_full_case_target_cache 的每个 array SHA
full payload SHA
```

验证通过后缓存 `case_id -> verified cache`。同一病例后续可复用，不重复计算。任一不一致在 forward 前失败。

Checkpoint 中：

```text
full_case_target_cache_manifest_sha256
full_case_target_profile_manifest_sha256
```

都必须绑定真实 v9 manifest 或真实 profile payload，不得再使用 `builder + case IDs + spacing source` 配方哈希。

新增：

```text
tests/care_ase/test_formal_runtime_parses_target_manifest.py
tests/care_ase/test_target_array_sha_mismatch_fails_before_forward.py
tests/care_ase/test_properties_sha_mismatch_fails_before_forward.py
tests/care_ase/test_checkpoint_uses_real_target_manifest_sha.py
```

## 八、P0：scar component center 不得被 patch 边缘重算

当前 full-case `scar_center_fullres` 已随 stock spatial transform 同步变换，但随后又从 `final_seg` patch-local component 重新计算并覆盖。

修复规则：

- full-case component ID、volume、centroid 和 center heatmap 为 authority；
- `scar_center_fullres` 使用与 image/seg相同的 spatial transform 后结果；
- `_recompute_augmented_physical_targets()` 不得覆盖 transformed full-case center heatmap；
- geometry、context 和 edema boundary 可以从最终 segmentation 重算；
- component 跨 patch 边缘时不得产生新的 patch-local centroid；
- component metadata 的坐标如保留，必须转换到最终 patch坐标或明确标记只用于 lookup，不能以原 full-case坐标冒充 transformed target。

新增：

```text
tests/care_ase/test_transformed_full_case_center_preserved.py
tests/care_ase/test_component_center_crossing_z_patch_edge.py
tests/care_ase/test_no_patch_local_center_relabel.py
```

## 九、P0：extent H/W coverage 使用变换后的真实 footprint

禁止继续只用 augmentation 前 `initial_origin + initial_patch_size` 的一个布尔值决定 augmentation 后所有 slice 的 extent validity。

必须将 source footprint/coverage metadata 与 stock spatial transform 同步。可以采用以下任一精确实现，但不能用猜测：

### 允许实现 A

stock transform 返回可复现的 affine/crop/scale 参数；解析完整源 H/W 四角和边界在最终 patch 中是否完整可见。

### 允许实现 B

建立带唯一边界/坐标编码的 source footprint，使用相同空间变换，并从变换结果证明完整源 H/W 均保留。

### 保守失败分支

若无法证明某输出 slice 完整覆盖源 H/W：

```text
extent area valid = 0
area loss = 0
area-derived final bias = 0
wall-derived extent final bias = 0
```

Presence 只依赖合法 source-z mapping，不能因为 partial H/W 自动全部关闭；presence 与 area validity 必须分开。

新增：

```text
tests/care_ase/test_extent_presence_and_area_validity_are_separate.py
tests/care_ase/test_transformed_source_footprint_controls_area.py
tests/care_ase/test_partial_hw_area_and_wall_bias_zero.py
tests/care_ase/test_partial_hw_presence_still_uses_full_case_z_profile.py
```

## 十、P0：Sampler requested/resolved/coordinate 必须完全真实

为所有 focus 构建真实 eligible pools，而不只是 OOF 和 small-component：

```text
scar gt_component
scar small_component
scar oof_fn
scar oof_fp
scar random_wall/background
edema positive
edema boundary
edema oof_fn_or_low_volume
edema safe_fp
edema random_wall/background
```

每个 pool 必须有：

```text
eligible case IDs
每病例 candidate coordinates
coordinate semantic validation
```

如果 requested pool 为空：

1. 在抽病例前按冻结 fallback 顺序解析下一个非空 category；
2. 从 resolved category 的 eligible pool抽病例；
3. 用 micro_patch_rng 从 resolved coordinates抽坐标；
4. descriptor 写真实 resolved category、fallback reason和坐标。

正式 descriptor 中 `selected_target_coordinate` 必须非空。正式 runtime 不得再由 `deterministic_center()` 静默搜索另一个 mask。

允许保留 `deterministic_center()` 作为显式 unit-test helper，但 formal mode 调用它且 descriptor 无冻结坐标必须失败。

必须保证：

```text
requested_category
resolved_category
hard_negative_category
coordinate_selection_source
selected_target_coordinate
candidate_coordinate_count
eligible_case_count
fallback_reason
manifest_sha256
```

与实际中心一致。

新增：

```text
tests/care_ase/test_sampler_all_focus_categories_have_pools.py
tests/care_ase/test_sampler_resolves_before_case_draw.py
tests/care_ase/test_formal_descriptor_requires_selected_coordinate.py
tests/care_ase/test_sampler_logged_category_matches_coordinate_semantics.py
tests/care_ase/test_edema_positive_boundary_pool_filter.py
```

## 十一、P1：Slurm step-specific lock 和 heartbeat 错误传播

Lock liveness 优先检查具体 step：

```text
SLURM_JOB_ID + SLURM_STEP_ID
```

使用：

```text
squeue --steps
或 sacct -j <job>.<step>
```

allocation 仍 RUNNING，但具体 step 已 FAILED/CANCELLED/COMPLETED 时，不得判为 live owner。

`HeartbeatTicker` 必须捕获线程异常：

```text
self.error
```

主线程在每个 step 前后及 stop 后检查；heartbeat 写失败必须：

- 写 failure receipt；
- 停止继续训练；
- 不保存新的 checkpoint；
- exit nonzero。

新增：

```text
tests/care_ase/test_slurm_step_dead_allocation_live_recoverable.py
tests/care_ase/test_heartbeat_thread_exception_propagates.py
tests/care_ase/test_atomic_stale_lock_single_winner_v9.py
```

## 十二、P1：推理 checkpoint 和快速 Docker 路径

推理 loader 不得打开 stock checkpoint，也不得隐式读取仓库全局 `DEFAULT_PLANS`、`DEFAULT_DATASET_JSON` 或调用训练期 `nnUNetTrainer._build_loss()`。

改造：

- checkpoint payload 保存 architecture signature；
- 保存 pathology deep-supervision weights；
- 保存或显式绑定 relocation-safe plans topology payload/SHA；
- inference constructor 接收 payload 中的 deep-supervision weights override；
- inference path 跳过 `stock_pathology_deep_supervision_weights()`；
- 所有 plans/dataset 读取必须来自显式部署 bundle路径，不能回退 repo default；
- Docker 需要的最小静态文件清单在训练前冻结。

新增：

```text
tests/care_ase/test_inference_loader_does_not_call_nnunet_trainer_loss.py
tests/care_ase/test_inference_loader_does_not_read_default_dataset_json.py
tests/care_ase/test_inference_loader_uses_checkpoint_ds_weights.py
tests/care_ase/test_deployment_bundle_minimal_files.py
```

生成轻量：

```text
results/20260803_care_ase_r2_last_hotfix_v9/deployment_bundle_contract.json
```

至少列出：

```text
checkpoint
checkpoint sidecar
v9 plans/topology JSON
dataset label/modality JSON
canonical inference module
decode module
preprocessing/export entrypoint
required Python package lock/fingerprint
```

不得构建 Docker，不得复制 checkpoint。

## 十三、P1：runtime input bundle 和 area reference 实值绑定

`formal_runtime_input_bundle.json` 中所有 path/SHA 必须现场重算：

```text
hard-negative manifest fold1/fold4
full-case target manifest fold1/fold4
direct stock OOF provenance manifest
area-reference receipt
effective contract
```

禁止只检查 SHA 字符串非空。

area-reference receipt 必须包含每折真实：

```text
scar_reference
edema_reference
actual_train_case_ids_sha256
split SHA
source function/source commit
payload SHA
```

正式 runtime 在模型构建前重算 actual-train references并与 receipt比较。Checkpoint 的 `area_reference_receipt_sha256` 必须绑定 receipt payload/file，而不是另一个未追踪的 `json_sha(area)` 语义。

新增：

```text
tests/care_ase/test_bundle_recomputes_all_path_shas.py
tests/care_ase/test_area_reference_values_bound_by_receipt.py
tests/care_ase/test_area_reference_mismatch_fails_before_model_build.py
```

## 十四、P1：checkpoint reload 使用完整正式语义

Reload validation 必须：

- 使用与 runtime 相同的显式 hard-negative manifest；
- 使用 verified full-case target cache；
- 传入相同 extent valid masks；
- 比较 base logits、extent statistics、final logits 和 conditional decode；
- 不推进 Python/NumPy/Torch/CUDA/sampler/case/patch/augmentation RNG；
- 仅在全部通过后写 `.verified.json`。

`_write_full_reload_receipt()` 禁止写 static review目录。

增加一个无 optimizer 的 checkpoint recovery validator：若进程在 checkpoint 原子保存后、verified receipt 写入前崩溃，可以在相同 source/contract/manifest 下重新执行 reload validation并补写 verified receipt；不得重新训练 1,000 步。

新增：

```text
scripts/validation/verify_care_ase_checkpoint_for_resume.py
tests/care_ase/test_checkpoint_verification_recovery_without_training.py
tests/care_ase/test_reload_compares_extent_and_decode.py
```

## 十五、P1：no-T2 mixed batch 证据真实逐行

实际 forward 继续使用 T2-present subset indexing。改进测试/receipt：

- 记录 edema-owned module 输入 batch size；
- mixed batch 中必须等于 T2-present row count，而不是 full batch size；
- no-T2-only batch call count为0；
- mixed batch各行输出与对应单行运行一致；
- 不得用 `if no_t2.all() else 0` 直接写零冒充 row-wise proof。

新增：

```text
tests/care_ase/test_no_t2_mixed_batch_module_input_rows.py
tests/care_ase/test_no_t2_mixed_vs_single_row_equivalence.py
```

## 十六、Permit 的环境绑定避免节点偶然差异

将环境证据拆为：

```text
software_determinism_manifest
runtime_hardware_receipt
```

Permit 必须绑定：

- Python/Torch/CUDA/cuDNN 版本；
- package source hashes；
- determinism flags；
- BF16/FP32 contract；
- final accepted GPU family或最低 compute capability。

不得因为 GPU index、device count 或同系列设备名称的非语义差异使第二折/下一 chunk 无法启动；也不得允许低于合同能力的设备静默运行。

新增：

```text
tests/care_ase/test_environment_manifest_stable_across_device_index.py
tests/care_ase/test_disallowed_gpu_capability_fails_before_step0.py
```

## 十七、避免重新跑两小时无关工作

允许复用 v8 direct stock OOF arrays/manifests，仅当全部满足：

```text
stock checkpoint SHA未变
preprocessed image SHA未变
plans SHA未变
producer script SHA未变
array SHA和manifest payload SHA可现场复算
held-out fold proof仍成立
```

满足时写 v9 inheritance receipt，不重新推理所有病例。

任一不满足才重新生成对应病例，不得无条件全量重跑。

Full-case target manifest因本轮 center/footprint/manifest语义变化必须重建轻量 manifest，但不提交大数组。

不得重复运行历史 v8 20-step probes。

## 十八、测试和真实 known-bad

运行：

```bash
./envs/env_CARE/bin/python -m pytest tests/care_ase -q
```

运行 G1：

```bash
./envs/env_CARE/bin/python \
  scripts/validation/validate_care_ase_r2_g1.py \
  --output-dir results/20260803_care_ase_r2_last_hotfix_v9
```

G1 必须检查语义，不只检查文件存在。

至少注入并拒绝以下真实 known-bad：

1. formal runtime写 tracked review目录；
2. authorized runtime outputs使下一 chunk被 clean-worktree误拒绝；
3. full-volume count每 tile加两次；
4. nonzero inference模型被错误除以2；
5. resume expected stock SHA来自payload；
6. target manifest只检查文件存在；
7. scar center从patch残片重算；
8. pre-augmentation H/W boolean冒充 transformed coverage；
9. empty focus pool退回整个group并保留requested category；
10. descriptor无坐标时formal runtime静默fallback；
11. allocation live但step dead仍判lock live；
12. heartbeat thread异常被忽略；
13. inference loader调用nnUNetTrainer loss或默认dataset JSON；
14. direct OOF/area receipt只检查非空SHA；
15. checkpoint reload使用默认旧manifest；
16. mixed batch no-T2 row-wise receipt硬编码为0；
17. probe第11个reservation被接受；
18. v8 contract/manifest被formal v9 runtime接受。

每个 mutation 记录：

```text
mutation_id
source/function
actual mutation
test command
exit code
detection reason
```

## 十九、GPU probe 总预算统一为最多 10 步

新 v9 namespace 的原子 reservation 总上限：

```text
10 optimizer steps
```

推荐主计划只使用 8 步：

```text
fold1 uninterrupted 0 -> 2          2 steps
fold1 exact resume 0 -> 1           1 step
fold1 independent resume 1 -> 2     1 step
fold4 uninterrupted 0 -> 2          2 steps
fold4 exact resume 0 -> 1           1 step
fold4 independent resume 1 -> 2     1 step
-------------------------------------------
planned total                         8 steps
```

剩余 2 个 reservation 仅用于最终 Commit A 上一次明确失败后的同范围重试。不得因为“还有额度”主动多跑。

规则：

- reservation 在 materialization/forward 前原子占用；
- crash/OOM/cancel 后不可复用；
- 第 11 个 reservation 在 forward 前失败；
- 所有有效 probe 必须运行在最终 Commit A；
- probe 后不得再修改 critical source；
- Stage B/C 只做无 optimizer 的 transactional oracle；
- 禁止 50-step throughput、2,000-step chunk 和正式训练；
- 所有 probe `formal_training_credit=zero`、`formal_resumable=false`、`outer_access=0`。

比较 uninterrupted 与 resume：

```text
descriptor bundles
requested/resolved category
case IDs
coordinates
augmentation seeds
augmented image/seg hashes
target hashes
loss
model tensors
optimizer moments
scheduler
sampler/case/patch/augmentation RNG
next bundle hash
```

## 二十、两阶段提交

### Commit A：最终实现

只包含：

```text
source
tests
v9 effective contract
v9 executor plan
validators
必要 mapper/fingerprint source
```

提交信息：

```text
care-ase-r2: close final v9 training and inference gaps
```

Commit A 后冻结 critical source。在 detached Commit A 上运行 CPU gates、manifest验证和最多10步probe。

### Commit B：轻量 review packet

只允许：

```text
results/20260803_care_ase_r2_last_hotfix_v9/**
prompts/routes/handoffs/CURRENT.md
wiki/**
```

Commit B 不得修改 source、tests、contract、wrapper、inference或validator。

提交信息：

```text
care-ase-r2: publish final v9 pretraining packet
```

Push：

```bash
git push origin main
git fetch origin main --prune
```

验证：

```text
Commit A是Commit B祖先
origin/main == Commit B
Commit A/B critical source manifest完全一致
worktree clean（除明确授权的runtime外）
```

Tracked packet 中禁止字符串：

```text
reported_after_push
```

由于文件不能自引用自己的 commit SHA，统一使用：

```text
review_packet_sha_binding_mode: external_review_and_permit_bind_actual_origin_main_head
review_packet_commit_sha: BOUND_BY_EXTERNAL_REVIEW
```

外部 GPT 以实际 `origin/main` HEAD 作为 Commit B，并在 permit 中写精确 SHA。

## 二十一、CURRENT 和 Wiki

更新为：

```text
v8 implementation 648bb4d... superseded
v8 review packet 8d01cd4... superseded
v8 20 reservations are zero-credit diagnostics
v9 Commit A is current implementation candidate
v9 final origin/main is current review packet
formal training not authorized
formal training not started
outer fold1/fold4 = 0
next action = external GPT final review
```

不要删除历史状态，但最新 v9 段必须放在顶部。

## 二十二、结果目录

```text
results/20260803_care_ase_r2_last_hotfix_v9/
```

至少包含：

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
v8_supersession_receipt.json
effective_contract_receipt.json
critical_source_manifest.json
runtime_write_isolation_receipt.json
clean_worktree_runtime_allowlist_receipt.json
full_volume_counting_receipt.json
full_volume_nonzero_oracle.json
resume_stock_checkpoint_binding_receipt.json
full_case_target_cache_manifest_fold1.json
full_case_target_cache_manifest_fold4.json
target_manifest_runtime_verification_receipt.json
scar_center_transform_receipt.json
extent_transformed_footprint_receipt.json
sampler_focus_resolution_receipt.json
lock_step_heartbeat_receipt.json
deployment_checkpoint_receipt.json
deployment_bundle_contract.json
runtime_input_bundle.json
area_reference_receipt.json
checkpoint_formal_reload_receipt.json
no_t2_rowwise_receipt.json
environment_binding_receipt.json
oof_inheritance_or_regeneration_receipt.json
real_mutation_detection_report.json
pytest_receipt.json
g1_receipt.json
gpu_probe_budget_receipt.json
gpu_probe_fold1_uninterrupted.json
gpu_probe_fold1_exact_resume.json
gpu_probe_fold4_uninterrupted.json
gpu_probe_fold4_exact_resume.json
gpu_probe_summary.json
mapper_report_draft.md
mapper_report_final.md
architecture_delta_final.md
controller_report.md
completion_check.md
MANIFEST.md
pretraining_external_review_request.json
notification_brief.json
```

不得提交：

```text
checkpoint
NIfTI
probability arrays
full target arrays
raw logs
Slurm stdout/stderr
Docker image/archive
secret
upload package
```

## 二十三、Controller 最终检查

Controller 必须直接读最终源码和 diff，不能只相信 receipt。

逐项确认：

- formal动态输出不污染 tracked review packet；
- 下一逻辑chunk允许已有 authorized runtime outputs；
- critical source dirty仍拒绝；
- full-volume count每tile一次且非零数值oracle通过；
- resume expected stock来自requested fold canonical source；
- full-case manifest逐病例逐array现场核验；
- scar center不从patch残片重算；
- extent presence/area validity分离且使用transformed footprint；
- sampler在case draw前解析resolved category；
- formal descriptor始终有冻结坐标；
- step-specific lock和heartbeat异常传播；
- inference loader不依赖stock checkpoint/default dataset/trainer loss；
- runtime bundle全部path/SHA现场核验；
- area references含真实数值并绑定；
- reload使用正式manifest、target和extent语义；
- mixed batch no-T2证据不是硬编码；
- v9 probe reservation不超过10；
- 所有有效probe在最终Commit A；
- formal training未启动；
- outer access为0；
- Commit B未修改critical source；
- origin/main push完成；
- CURRENT/wiki最新段正确。

全部通过时：

```text
controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: CODE_AND_MAX10_STEP_PROBE_ONLY_ZERO_FORMAL_CREDIT
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
formal_training_authorized: false
formal_training_started: false
outer_access_fold1: 0
outer_access_fold4: 0
next_required_action: RETURN_TO_EXTERNAL_GPT
```

仍有任何明确 P0/P1 缺口时，在同一 task scope 内修复；不得开启 v10，不得增加新设计。若10步预算耗尽仍不能闭合，停止并如实列出剩余问题，不得继续训练调试。

## 二十四、通知和最终回传

Commit、push、validator和packet全部完成后写 `notification_brief.json`，再调用：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

不得手写SMTP。

最终用户回传先用自然中文说明：

1. 关闭了哪些问题；
2. 哪些问题仍未关闭；
3. 新增实际 optimizer steps；
4. 是否启动正式训练；
5. Commit A / Commit B / origin main；
6. push状态；
7. 下一步是否只剩外部 GPT 最终许可。

最终一行只能是：

```text
PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY
```

若无法闭合：

```text
NEEDS_REPAIR
```
