# CARE Challenge: Myocardium 当前状态与 TODO

更新时间：2026-05-19

本文件只保留当前决策所需内容；历史细节见：

- `docs/notes/*_improvement_round*.md`
- `results/experiments/*_iteration_log.md`
- `results/metrics/nnUNet.md`

当前官方 validation leaderboard 已刷新：

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

最新文件：`results/leaderboard/care2026_myocardium_latest.json`。本次 hybrid zip 已返回，提交时间 `20260519 00:06:58`，用户名 `OrganAgent`。

---

## 1. 提交与评估口径

CARE-Myocardium validation 是 **一次上传一个 zip**，zip 同时包含：

- `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`
- `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`

一次上传会返回三个指标：

| hosted metric | zip branch | 本地主要对照 |
| --- | --- | --- |
| `myops_scar` | `MyoPS/` | Dataset501 class_5 |
| `myops_edema` | `MyoPS/` | Dataset501 class_4 |
| `myocardium_cinemyops` | `CineMyoPS/` | Dataset502 class_1 proxy；class_3 scar 作 sanity |

已提交的 hybrid zip：

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip
```

含义：

- MyoPS branch：nnU-Net baseline。
- CineMyoPS branch：CineMyoPS `pathology_direct`。
- 这个 zip 一次性返回三个分数；MyoPS 两项按 nnU-Net baseline 解读，CineMyoPS 项检验 CineMyoPS `pathology_direct`。

本地 pre-upload QA 已通过：两个 branch 均 15/15 cases，且每例均含 pathology label；没有复现 `Case1009` missing-label 问题。

官方返回结果：

| hosted metric | OrganAgent Dice | HD | rank | 解读 |
| --- | ---: | ---: | ---: | --- |
| `myops_scar` | 0.5969 | 16.2536 | 4/5 | nnU-Net MyoPS baseline；Dice 中等，HD 优于部分提交但远低于 rank1 |
| `myops_edema` | 0.6496 | 22.0125 | 4/5 | nnU-Net MyoPS baseline；Dice 高于 zxz，但 HD 略差于 zxz |
| `myocardium_cinemyops` | 0.1748 | 75.2130 | 6/9 | CineMyoPS `pathology_direct`；Dice 有一定提升但 HD 很差，需优先诊断 |

Dice/HD 观察：当前 MyoPS 的 Dice 与 HD 存在错位，说明后处理/空间约束可能清除了部分 outlier 但仍有边界或体积偏差；CineMyoPS 的 HD=75 更像远端离群、空间错位或 hosted metric 语义不匹配，不能只靠本地 Dice 判断成功。

---

## 2. 参考基线

### 2.1 本地 nnU-Net 5-fold reference

| 任务 | nnU-Net 5-fold mean Dice | 备注 |
| --- | ---: | --- |
| `myops_scar` / class_5 | **0.5592** | MyoPS-Net、U-MyoPS 需要超过 |
| `myops_edema` / class_4 | **0.4197** | MyoPS-Net、U-MyoPS 需要超过 |
| `myocardium_cinemyops` / class_1 proxy | **0.6808** | CineMyoPS 本地目标 |
| Cine scar sanity / class_3 | 0.2586 | 检查 pathology head 是否有信号 |

### 2.2 官方 validation leaderboard 最新公开 best

| hosted metric | rank 1 | time | Dice / score | HD |
| --- | --- | --- | ---: | ---: |
| `myops_scar` | ZQH | 20260515 16:16:04 | **0.8390** | 6.2775 |
| `myops_edema` | ZQH | 20260515 16:16:04 | **0.8536** | 8.6853 |
| `myocardium_cinemyops` | NCC1H | 20260515 16:16:58 | **0.2594** | 38.1004 |

注意：官方 validation 与本地 protocol validation 不可直接等同；尤其 MyoPS validation 全部为三序列完整，而本地 fold0 包含大量 LGE-only / 缺 T2 训练分布。

---

## 3. 三个模型当前进展

| 模型 | 当前最好本地结果 | 对 nnU-Net 结论 | 当前定位 |
| --- | --- | --- | --- |
| CineMyoPS | round6 `pathology_direct`: local class_1 `0.6933`, class_3 `0.4378`; hosted Dice `0.1748`, HD `75.2130` | local 高于 nnU-Net，但 hosted 一般且 HD 很差 | round8 必须做 hosted metric/HD 诊断 |
| MyoPS-Net | round4/round7 `combined_safe`: edema `0.3733`, scar `0.5048` | 两项均低于 nnU-Net edema `0.4197` / scar `0.5592` | 不适合作为当前 MyoPS 提交 branch；后续必须做模型级 missing-modality/T2-aware 改造 |
| U-MyoPS | round7 LGE+dilated prior: edema `0.7039` all-case, scar `0.5539` | scar 接近但仍低于 nnU-Net `0.5592`；edema all-case 被 empty-GT inflated | 最强 pure U-MyoPS scar 结果，但仍不足以替换 nnU-Net |

### 3.1 CineMyoPS

已解决的问题：

- 早期 eval/export 全背景的问题已定位到 inference/combination 语义。
- `pathology_direct` 使用 Cine temporal/motion、ED anatomy 与 pathology branch，保留论文核心思想。
- 本地 fold0 class_1 `0.6933` 超过 nnU-Net 5-fold `0.6808`；class_3 scar sanity `0.4378` 也超过 nnU-Net `0.2586`。
- validation package 已打包并提交：MyoPS=nnU-Net，Cine=CineMyoPS `pathology_direct`。
- 官方 hosted CineMyoPS 返回 Dice `0.1748`, HD `75.2130`，只排到 rank 6/9。

当前问题：

- hosted `myocardium_cinemyops` 与本地 class_1/class_3 proxy 明显错位；现在必须反推 metric 语义。
- HD 很差，优先怀疑远端离群组件、空间/label 语义错位或 pathology routing 过宽。
- 目前只有 fold0 CineMyoPS；没有 5-fold ensemble。

改进方案：

1. round8 先做 validation zip prediction QA：每例 2221 体素、连通域、bbox、远端 outlier、体积比例。
2. 在 protocol fold0 增加 HD/HD95 或 component-distance proxy，不能只看 Dice。
3. 做 export-only `pathology_largest_component` / `pathology_myocardium_roi` / `pathology_volume_guard`，如果 HD 明显改善且 Dice 不崩，再准备新 package。
4. 如果 round8 证明 baseline 小修无效，第9轮开始按 DeepResearch 走 CineMA/StrainNet/MTI-style motion-texture 新模型路线。

### 3.2 MyoPS-Net

已解决的问题：

- Challenge3 变体已避免不存在的 T1m/T2* mapping 分支污染。
- round4/round7 的 best export route 稳定在 scar `0.5048`、edema `0.3733`。

当前问题：

- postprocess / calibration 已基本到头：round7 多个 export-only edema 变体没有超过 round4。
- scar 和 edema 仍都低于 nnU-Net。
- 训练数据缺模态影响明显：edema 依赖 T2，但只有完整三序列病例有可靠 T2；LGE-only 训练占比过大。

改进方案：

1. round8 只允许做一次模型级尝试：T2-present edema expert + modality mask + HD/boundary-aware loss。
2. 同步做 nnU-Net/MyoPS-Net 的 Dice/HD component profile，解释官方 MyoPS Dice/HD 错位。
3. 如果 round8 仍不能接近 nnU-Net，round9/10 不再继续 MyoPS-Net，转 `src/` 新模型（CAA-Seg/SSA + anatomy/pathology cascade）。

### 3.3 U-MyoPS

round7 结果：

| checkpoint | all-case edema | all-case scar | scar-positive scar | complete/T2-present scar | missing-modality scar |
| --- | ---: | ---: | ---: | ---: | ---: |
| `model_best` | 0.7039 | **0.5539** | 0.5668 | 0.6571 | 0.4949 |
| `model_final_checkpoint` | 0.7039 | 0.5538 | 0.5667 | 0.6571 | 0.4948 |

已解决的问题：

- round7 LGE+dilated prior 比 round5 LGE-only/no-prior scar `0.5307` 和 round6 pure best `0.5352` 明显更好。
- 说明 Stage1 prior 并非完全无用；CARE-aware dilation/gating 方向比原始 full prior 更合理，也更接近 U-MyoPS 论文思想。

当前问题：

- all-case scar `0.5539` 仍低于 nnU-Net 5-fold `0.5592` 和 nnU-Net fold0 `0.5602`，差距很小但没有越线。
- edema 不可信：all-case edema `0.7039` 主要来自 empty-GT case；GT-positive/T2-present edema 只有约 `0.1858`。
- 低分病例仍集中在 prior/pathology overlap 弱或体积偏差明显的 case，如 `Case7005`, `Case1045`, `Case1029`, `Case5005`, `Case3004`, `Case3038`。

改进方案：

1. 不扩展 U-MyoPS folds；fold0 尚未稳定超过 nnU-Net。
2. round8 只做小范围 prior reliability/gating：
   - 对 prior support Dice / pathology overlap 极低的 case 降低 prior 权重；
   - missing-modality 与 complete-modality 使用不同 prior dilation 或 gate；
   - 分析低分病例是否是 false positive scar 体积过大还是 under-segmentation。
3. 如果 gating 后 scar 仍不能超过 `0.5592` 且 HD/outlier 不改善，停止 U-MyoPS 主线，把它保留为论文适配/ablation 结果。

---

## 4. 当前执行优先级

1. **Round8 prompts 已准备**：
   - `prompts/CineMyoPS/prompt8_official_metric_hd_repair.md`
   - `prompts/MyoPS-Net/prompt8_t2aware_hd_loss_exit_gate.md`
   - `prompts/U-MyoPS/prompt8_prior_reliability_gate.md`
2. **第10轮前做 baseline 去留判定**：
   - Round8-10 内若 CineMyoPS/MyoPS-Net/U-MyoPS 仍不能稳定超过 nnU-Net 或解释 hosted metric，就停止第三方 baseline 小修。
   - 停止后根据 `prompts/DeepResearch/` 结果，在 `src/` 内开发新模型：Cine 走 motion/strain/CineMA，MyoPS 走 CAA-Seg/SSA + anatomy/pathology cascade + HD-aware loss。
3. **当前提交策略**：
   - MyoPS branch 暂用 nnU-Net baseline。
   - CineMyoPS 需要先修 hosted HD/metric 语义，再考虑新提交。

---

## 5. 运行规则

- 每轮训练/评估 job walltime 目标不超过 **8 小时**。
- 每轮只验证一个主要假设，并记录到 `results/experiments/*_iteration_log.md`。
- 不使用 1000/2000 epoch 长训补弱结果。
- 不复用 stale prediction cache；prediction / metric dir 必须包含模型、round、trainer、checkpoint 或 config tag。
- 每次查官方 validation 分数前先运行 `python scripts/leaderboard/fetch_care2026_scores.py`。
- submission zip 生成后必须通过 layout + raw label + pathology label QA。
