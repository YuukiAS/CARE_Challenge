# CineMyoPS 改进 Prompt：修复 Task026 全 0 并校准 leaderboard 口径

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中改进 CineMyoPS，使其至少形成可信的 Task026 paper-style 训练/导出/评估闭环，然后再追求超过 nnU-Net。

当前本地状态：

| metric | nnU-Net 5-fold mean | 当前 CineMyoPS fold0 |
| --- | ---: | ---: |
| `myocardium_cinemyops` / class_1 | 0.6808 | 0.0000 |
| scar sanity / class_3 | 0.2586 | 0.0000 |

官方 validation 最新 rank1：

| task | rank1 Dice |
| --- | ---: |
| `myocardium_cinemyops` | 0.2594 |

## 背景

必须先阅读：

- `docs/literature/Ding 等 - 2025 - CineMyoPS Segmenting Myocardial Pathologies from Cine Cardiac MR.pdf`
- `prompts/Baseline_report.md`
- `prompts/CineMyoPS/improvement_suggestion.md`
- `results/metrics/nnUNet.md`
- `results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json`
- `jobs/CineMyoPS/README.md`
- `TODO.md`

论文要点：

- CineMyoPS 是 cine-only 模型，不使用 LGE/T2 作为 inference 输入。
- 论文核心是 motion estimation + anatomy segmentation + time-series aggregation。
- ED frame 是 reference；论文建议使用从 reference 开始的 4/6 cardiac-cycle frames。
- 论文输出 scar/edema pathology；CARE 当前本地 Dataset502 还包含 myocardium/LV/scar compact labels。

当前实现状态：

- 旧 `Task025_Cine_Seg` 是 single-frame / middle-frame legacy baseline，不是论文主路径。
- 新 `Task026_Cine_4D` 已采用 ED-first t=0 + sampled frames。
- `CARECineMyoPSTrainer` 和 `CARECineSegLoss` 已存在，但当前 fold0 unified eval 全 0。
- 必须先确定全 0 来自训练失败、checkpoint/export 找错、label remap 错误、Task025/Task026 混用，还是预测后处理。

## 任务目标

第一目标不是调参，而是恢复非空、语义正确、空间对齐的 fold0 predictions。

## 运行预算与迭代策略

本 prompt 是多轮改进任务，不允许一次性提交超长训练。每一轮必须遵守：

- 单个 Slurm 训练/评估 job walltime 目标不超过 **8 小时**；当前首轮优先是修全 0，必要时训练可以只跑 smoke/短训。
- 每轮只验证一个主要假设，例如 Task026 export、checkpoint 路径、label remap、trainer 输出语义、motion/anatomy loss，不要一次混入多个无法归因的改动。
- 当前 prediction 全 0 时，不允许先增加训练时长；必须先证明 checkpoint、export、prediction unique labels 和 geometry 正常。
- 不要跑 1000/2000 epoch；如果 8 小时内 class_1/class_3 或非零预测没有改善，停止并定位 pipeline。
- 如果 `CARECineMyoPSTrainer` 没有合适的 early stopping 或 checkpoint selection，本轮优先加上：
  - max runtime / max epoch 双限制；
  - validation class_1/class_3 或 hosted-like metric plateau patience；
  - 保存并导出 best checkpoint；
  - 日志中记录实际 epoch、elapsed time、best metric、停止原因。
- 三个模型之间的实验预算要尽量公平：每轮先用近似 **8 小时 walltime** 的 fold0 预算比较方向，再决定是否扩展。
- 除非发现会影响数据合规、label 定义或 leaderboard 提交口径的关键问题，不要停下来问用户；直接做下一轮可回滚的小改动并记录结果。

必须完成：

1. 全 0 定位：
   - 检查 `results/predictions/CineMyoPS/fold_0/*.nii.gz` 是否存在 13 个 protocol val cases。
   - 对每个 prediction 统计 unique labels、非零体素数、shape、spacing/origin/direction。
   - 检查 export 读取的是 `Task026_Cine_4D` + `CARECineMyoPSTrainer` 的 checkpoint，而不是 Task025 或空目录。
   - 若 checkpoint 不存在或训练未完成，要明确报告，不要用全 0 当模型性能。

2. Task026 数据链路：
   - 运行并修复 `code/CineMyoPS/sanity_check_task026.py`。
   - 运行并解释 `code/CineMyoPS/verify_ed_at_t0.py`。
   - 确认 `CINE_NUM_FRAMES` 在 prepare、train、export 中一致。
   - 确认 split 来自 `data/benchmarks/protocol/splits_CineMyoPS.json`，val case id 和 export case id 一致。

3. 输出语义校准：
   - 本地 compact label 应为 `0=background`, `1=myocardium`, `2=LV_blood`, `3=scar`。
   - 确认 `CARECineMyoPSTrainer` 是否输出 anatomy classes 1/2 与 scar class 3。
   - 若 trainer 只输出 scar-only pathology，则必须修 export/eval 或报告主 metric 不可比。
   - 同时报告 class_1 和 class_3，分别对应当前 leaderboard 口径与论文 pathology 口径。

4. 论文机制验证：
   - 确认 motion branch 输出非零且无 NaN。
   - 确认 anatomy branch 在 ED frame 上受监督。
   - 确认 pathology head 使用 motion/anatomy features，而不是退化成普通 nnU-Net。
   - 如果实现与论文仍有偏差，报告偏差并给最小修复。

5. 评估与 submission：
   - fold0 非空后重新跑 unified eval。
   - 若 class_1 或 hosted-like metric 仍不可信，先做 validation dry-run package，再提交一次 official validation 以校准 hosted metric。
   - 只有 fold0 闭环可信后再跑 5 folds。

## 推荐实现范围

优先编辑：

- `code/CineMyoPS/task026_utils.py`
- `code/CineMyoPS/prepare_task026_cine_4d.py`
- `code/CineMyoPS/export_protocol_val_predictions.sh`
- `code/CineMyoPS/run_train.sh`
- `jobs/CineMyoPS/run_task026_paper_steps.sh`
- `jobs/CineMyoPS/sbatch_fold0_pipeline.sh`
- `third_party/CineMyoPS/code/nnunet/training/network_training/CARECineMyoPSTrainer.py`
- `third_party/CineMyoPS/code/nnunet/training/loss_functions/care_cineloss.py`

不要做：

- 不要继续使用 Task025 作为主结论。
- 不要在 prediction 全 0 时调学习率或加 epoch。
- 不要把官方 validation `myocardium_cinemyops` 直接等同论文 scar，必须同时报告 class_1 和 class_3。
- 不要引入外部训练数据。

## 验证命令建议

```bash
cd /overflow/htzhu/CARE

# 当前全 0 指标
python -m json.tool results/metrics/unified/CineMyoPS/fold_0/evaluation_summary.json

# Task026 sanity
./env_CARE/bin/python code/CineMyoPS/sanity_check_task026.py
./env_CARE/bin/python code/CineMyoPS/verify_ed_at_t0.py

# fold0 paper path train + export + eval
FOLD=0 CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainer \
  CINE_NNUNET_EPOCHS=<budgeted_epoch_or_earlystop> \
  sbatch -t 08:00:00 jobs/CineMyoPS/sbatch_fold0_pipeline.sh

# export/eval only
FOLD=0 CINE_NNUNET_TASK=Task026_Cine_4D CINE_NNUNET_TRAINER=CARECineMyoPSTrainer \
  sbatch jobs/CineMyoPS/sbatch_export_eval.sh
```

## 交付物

1. 代码改动，保持 Task026 为主路径。
2. 新的中文报告：`docs/notes/CineMyoPS_improvement_round2.md`
3. 更新或追加实验记录：`results/experiments/CineMyoPS_iteration_log.md`
4. 更新 `results/metrics/unified/CineMyoPS/aggregate.md/json`

报告必须明确列出：

- 全 0 的真实原因。
- `Task025` 与 `Task026` 是否仍有混用。
- prediction unique labels 是否包含 `1/2/3`。
- class_1 与 class_3 分别相对 nnU-Net 的差距。
- 本轮 walltime、实际 epoch、best checkpoint、停止原因。
- 是否值得做官方 validation submission 校准。
