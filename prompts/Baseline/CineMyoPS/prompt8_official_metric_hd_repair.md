# CineMyoPS round8 prompt: hosted-metric calibration and HD repair

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续 CineMyoPS。本轮是 baseline 去留判定的第 8 轮，目标不是盲目训练，而是解释并修复 round7 hybrid submission 在 hosted validation 上的 CineMyoPS 结果。

## 背景与硬事实

已提交的 hybrid zip：

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip
```

官方 validation 返回：

| metric | OrganAgent | rank context |
| --- | ---: | --- |
| `myocardium_cinemyops` Dice | 0.1748 | rank 6/9 |
| `myocardium_cinemyops` HD | 75.2130 | HD 很差，说明存在远端离群/空间错位/label 语义问题 |

本地 protocol fold0 对照：

| variant | class_1 | class_2 | class_3 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| nnU-Net Dataset502 5-fold | 0.6808 | 0.8874 | 0.2586 | - |
| CineMyoPS R6 `pathology_direct` | 0.6933 | 0.9316 | 0.4378 | 0.6876 |

结论：本地 class_1/class_3 proxy 与 hosted metric 存在明显错位；不要再直接用本地 class_1 高分判断 validation 成功。

## 必须先读

- `docs/notes/CineMyoPS_improvement_round7.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `docs/notes/Dice_HD.md`
- `scripts/submission/README.md`
- `scripts/submission/prepare_care_myocardium_validation.py`
- `prompts/DeepResearch/DeepResearch_prompt.md`
- `prompts/DeepResearch/Result1.pdf`
- `prompts/DeepResearch/Result2.pdf`
- `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv`
- `AGENTS.md`

DeepResearch 相关提示：Cine 方向优先考虑 motion/strain 特征（MTI-MyoScarSeg, StrainNet），但 round8 先做 hosted metric/HD calibration；不要在还没解释官方失败前直接重构新模型。

## Round8 主要假设

> 官方 CineMyoPS 低分不是单纯训练不足，而是 validation output 的 label/metric 语义、pathology volume、空间 outlier 或 anatomy-pathology routing 与 hosted metric 不匹配。通过官方包级 QA、协议集 HD/Dice 双指标评估、pathology component/ROI 约束和 baseline comparison，可以判断 CineMyoPS 是否还有第 9-10 轮继续价值。

## 任务

1. **复盘官方提交**
   - 读取当前 hybrid zip 的 CineMyoPS validation prediction label counts、每例 2221 体素数、连通域数量、最大连通域占比、bbox 与 myocardium/LV bbox 的距离。
   - 输出 `results/diagnostics/CineMyoPS_round8_validation_zip_qc.{csv,md}`。
   - 明确是否存在远端离群小组件；结合 `Dice_HD.md` 判断 HD=75 的最可能原因。

2. **建立 protocol fold0 的 Dice+HD 评估**
   - 当前 unified eval 主要看 Dice；请补充或复用 HD/HD95 评估，至少覆盖 class_1/class_3。
   - 对比 variants：`pathology_direct`, `class1_primary_overlay`, `cardiac_only`, nnU-Net Dataset502 fold0。
   - 输出 `results/metrics/unified/CineMyoPS_R8_hd_audit/fold_0/`。

3. **做 export-only HD repair variants，不训练**
   - `pathology_largest_component`: 2221 只保留最大或前 K 个合理组件。
   - `pathology_myocardium_roi`: 2221 限制在 anatomy myocardium/LV 邻域内，允许小 dilation，禁止远端漂移。
   - `pathology_volume_guard`: per-case 2221 体积按 protocol train distribution clip，防止大面积误报。
   - `nnunet_cine_baseline_package`: 如还没有官方 nnU-Net-only submission 记录，准备一个纯 nnU-Net 5-fold baseline package 供用户后续一次性上传对照，但不要自动上传。

4. **只在有证据时准备新 validation package**
   - 如果某个 variant 在 protocol fold0 上 Dice 不明显下降且 HD/HD95 明显改善，准备 upload-ready package。
   - 包名/manifest 必须写清楚 Cine combine/postprocess mode。

## 判定标准

- Success: 找到导致 hosted HD=75 的具体预测模式，并产出一个 protocol HD 明显改善、Dice 不崩的 validation candidate。
- Partial: 证明 `pathology_direct` 本地高分主要来自 class_1 proxy，而 hosted metric 更接近 pathology/HD；给出第9轮 motion/strain 新模型计划。
- Failure: 如果所有 export-only repair 都不能改善，停止 CineMyoPS baseline 小修，转入 `src/` 新模型路线：CineMA/StrainNet/MTI-style motion-texture fusion。

## 禁止事项

- 不要直接训练新 CineMyoPS。
- 不要用 `cardiac_only` 当 final candidate；它只能是 anatomy upper bound。
- 不要只汇报 Dice，必须同时汇报 HD/HD95 或至少 outlier component diagnostics。
- 不要自动上传新的 zip。
- 不要把 hosted `myocardium_cinemyops` 再假定为本地 class_1，必须用结果反推 metric 语义。

## 交付物

- `docs/notes/CineMyoPS_improvement_round8.md`
- 追加 `results/experiments/CineMyoPS_iteration_log.md`
- 新诊断/指标目录和候选 package 路径（如生成）
- 如果判断需要新模型，写出 `src/` 方案草案而不是继续 baseline 后处理
