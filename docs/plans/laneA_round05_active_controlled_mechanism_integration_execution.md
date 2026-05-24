# Lane A Round05 Active Controlled Mechanism Integration Execution

Plan metadata:
- Type: active round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round05 controlled high-upside mechanism integration
- Status: active; first low-risk audit batch in progress
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round03plus_controller_myops_modality_aware_src_plan.md`
- Function: move Lane A from failed minor loss/postprocess tweaks into CARE-specific mechanism audits for alignment, soft anatomy prior, and conservative boundary/HD objectives
- Do not: train, submit Slurm, create validation zip, upload, download pretrained weights, expand folds 1-4, pull large external repos, or treat foreground mean as a success metric

## 1. 当前状态

Round2 已经证明 edema inference/postprocess route 失败。删除 1-voxel edema 小岛后 component count 下降，但 GT-positive edema Dice 略降、HD95 略恶化，因此小连通域删除、ROI 阈值和推理端 suppression 不能继续作为主线。

Round3 只是 gradient/tiny-overfit smoke pass。它证明 class_4 edema loss candidates 没有 NaN/Inf，class_5 interference 为 0，并把 `edema_focal_tversky + no_t2_edema_loss_downweighting` 推入 bounded fold0 short train。这个结论不是性能提升结论。

Round4 bounded fold0 short train 已完成 20 epoch，并导出 44/44 fold0 validation predictions。最终 gate 是：

```text
fail_stop_no_longer_train
```

`edema_focal_tversky + no_t2_edema_loss_downweighting` 不进入 longer fold0 train、fold1-4 或 validation submission。关键失败原因：

- T2-present GT-positive edema Dice 只小幅改善，但 HD95 和 remote FP 变差。
- CenterC edema 只小幅改善，但 remote FP 变差。
- no-T2 empty-GT 出现新增 edema false positives。
- all-case edema Dice 大幅下降。
- scar class_5 HD95 guardrail 不干净。

## 2. Round5 Strategic Decision

Lane A 的主要瓶颈已经不是简单 class imbalance，不是 inference 小碎片，也不是单一 loss weight 可以解决的问题。当前难点是：

- 缺失模态不是随机缺失，而是和 center 绑定。
- Edema 依赖 T2，但完整 C0+LGE+T2 cases 只有少数。
- No-T2 empty-GT 不能作为可靠强负样本。
- CenterC complete cases 的 edema 仍差，说明问题不只是缺 T2，还可能包含 alignment、boundary、spatial support 或 supervision reliability 问题。
- Anatomy prior 必须是 soft constraint，不能是 hard deletion。
- Loss-only tweak 已经不足；Round4 的 recall/imbalance 方向带来了 HD95、remote FP 和 no-T2 FP 回退。

Round5 因此进入 controlled high-upside mechanism integration：先用 CARE-only audit 判断机制槽位是否有证据，再决定是否做下一轮 one-mechanism smoke。Deep Research 可以更积极使用，但必须按机制槽位接入：

| Deep Research idea | Round5 mechanism slot | Round5 rule |
| --- | --- | --- |
| CAA-Seg / SSA | multi-sequence alignment | 先做 CARE-only alignment feasibility audit；不得直接复现或接入完整 repo。 |
| Cascaded FSN / PT-Net | anatomy-guided prior | 先证明 soft anatomy support 能解释 remote FP/HD95 outlier；不得 hard-delete lesion。 |
| InverseForm / surface loss / differentiable HD | boundary/HD objective | 先区分 boundary overreach、remote component、volume error、undersegmentation；下一步只允许 conservative small-weight loss。 |
| AdaMM / UniME / I-MMSeg | missing-modality / intensity prior | 本轮只作为机制备选和 metadata audit 对象；不得下载权重或大规模集成。 |

## 3. 本轮允许边界

允许：

- 读取现有 Dataset501 fold0 validation GT、baseline nnU-Net501 predictions、Round4 candidate predictions、原始 C0/LGE/T2 图像和已有诊断 CSV。
- 生成 case-level CSV/Markdown audit。
- 做 metadata-level repo/method reasoning，但不 clone/build/train。
- 生成少量 failure overlay PNG，仅当现有依赖足够且不会引入长任务。

禁止：

- 训练或继续 Round4 candidate。
- 提交 Slurm。
- 创建 validation zip 或上传。
- 下载权重或外部数据。
- 扩展 fold1-4。
- 一次性拉取大量 repo。
- 用 foreground mean 或 all-case aggregate 掩盖 `myops_edema` / `myops_scar` 单项失败。

所有 Round5 第一批输出写入：

```text
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/
```

## 4. Route A: CAA-Seg / SSA-style Multi-sequence Alignment Audit

目标：判断 CenterC complete-case edema failure 是否和 C0/LGE/T2 slice mismatch、spacing/orientation、registration drift 或序列间 anatomy mismatch 有关。

本轮不实现 CAA-Seg，不接入其 repo。先做 CARE-only audit：

- 对 fold0 validation 的 complete-modality cases，尤其 CenterC，读取 C0、LGE、T2。
- 统计各 modality 的 shape、spacing、origin、direction、slice count。
- 计算跨 modality geometry mismatch、nonzero/body bbox mismatch、bbox center distance、body-mask overlap proxy。
- 在 myocardium/anatomy bbox 内计算 LGE-T2、LGE-C0、T2-C0 intensity correlation/summary。
- 将 alignment proxies 与 baseline/Round4 edema Dice、HD95、remote FP、volume ratio 关联。
- 比较 CenterC failure cases 和 non-failure complete cases。

输出：

- `alignment_feasibility_audit.csv`
- `alignment_feasibility_audit.md`

Go/watch/stop rule：

- `go`：alignment proxy 与 CenterC/complete-case edema HD95 failure 明显相关，或存在明确 geometry/slice mismatch。
- `watch`：有弱信号或样本太少但 CenterC failure 集中，下一步可做 one-case SSA preprocessing smoke。
- `postpone`：geometry/proxy 基本一致，且和 HD95 failure 不相关。
- `stop`：审计证明现有数据已经严格同几何且 failure 与 alignment proxy 反向或无关。

## 5. Route B: Anatomy-guided Cascade / Soft Prior Feasibility Audit

目标：判断 edema FP、remote FP 和 HD95 是否可以用 soft anatomy support 改善。禁止 hard deletion。

本轮基于已有 nnU-Net501 baseline prediction、Round4 candidate prediction、GT 和 anatomy labels，构建 case-level 统计：

- edema prediction 与 GT myocardium、LV、RV、combined anatomy ROI 的 overlap ratio。
- edema prediction 到 myocardium / anatomy 的 distance-map summary。
- edema components 与 dilated myocardium support 的关系。
- remote FP 与 anatomy bbox / myocardium distance 的关系。
- no-T2 empty-GT 新增 edema FP 是否远离 myocardium/anatomy。

输出：

- `anatomy_soft_prior_feasibility.csv`
- `anatomy_soft_prior_feasibility.md`

Go/watch/stop rule：

- `go`：anatomy distance/overlap 能解释 remote FP 和 HD95 outlier，且不要求硬删除。
- `watch`：soft anatomy support 只能解释部分 failure，但足够支持 distance-map auxiliary input 或 soft penalty smoke。
- `postpone`：remote FP 主要不由 anatomy support 解释，优先做 alignment/boundary。
- `stop`：anatomy soft prior 会系统性误判 GT-positive edema 或只能通过 hard deletion 改善。

## 6. Route C: Conservative Boundary / Distance Objective Audit

目标：为下一轮 trainable loss 设计提供证据。Round5 不继续 Focal Tversky 主导训练。

本轮分析 baseline 和 Round4 candidate 的 edema boundary/HD95 failure：

- remote component：远离 GT edema 或 myocardium/anatomy 的小/孤立预测。
- boundary overreach：没有明显 remote component，但 edema 预测边界超出 GT 较远。
- volume overprediction：pred/GT volume ratio 明显偏高。
- undersegmentation：pred/GT volume ratio 明显偏低或 Dice 低且预测不足。
- empty-GT FP：no-T2 empty-GT 中新增 edema。

输出：

- `boundary_distance_failure_audit.csv`
- `boundary_distance_failure_audit.md`

Go/watch/stop rule：

- `go`：failure 主要是 smooth boundary overreach，下一步用 baseline Dice/CE + small-weight surface distance loss。
- `watch`：boundary loss 可作为小权重辅助，但必须同时加 anatomy/remote-FP guard。
- `postpone`：failure 主要是 alignment 或 anatomy support 问题。
- `stop`：boundary objective 只会继续扩大 recall 或损伤 scar guardrail。

## 7. 第一批执行任务

本次立即执行以下低风险 audit：

1. 创建本正式 plan：
   - `docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md`
   - copy summary: `results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/round5_laneA_plan.md`
2. 运行 `alignment_feasibility_audit`。
3. 运行 `anatomy_soft_prior_feasibility`。
4. 运行 `boundary_distance_failure_audit`。
5. 生成 `round5_laneA_decision_table.md` 和 `round5_next_implementation_prompt.md`。

不执行：

- 训练。
- Slurm。
- validation zip / upload。
- fold1-4。
- external repo clone/build/train。
- weight download。

## 8. Required Outputs

```text
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/round5_laneA_plan.md
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/alignment_feasibility_audit.csv
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/alignment_feasibility_audit.md
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/anatomy_soft_prior_feasibility.csv
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/anatomy_soft_prior_feasibility.md
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/boundary_distance_failure_audit.csv
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/boundary_distance_failure_audit.md
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/round5_laneA_decision_table.md
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/round5_next_implementation_prompt.md
```

Optional, only if cheap:

```text
results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/failure_overlays/
```

## 9. Promotion Gate

Round5 第一批 audit 不直接 promote 到 training。下一步只能是 one-mechanism smoke：

- alignment `go` -> SSA/alignment preprocessing smoke on fold0 complete cases only.
- anatomy `go` -> anatomy-guided cascade/soft-prior smoke, no hard deletion.
- boundary `go` -> conservative Dice/CE + small-weight surface/distance auxiliary smoke.
- all `postpone/stop` -> controlled repo portfolio metadata audit for CAA-Seg, Cascaded FSN, I-MMSeg/UniME/AdaMM by mechanism slot, with license/compliance, input-output, label mapping, and one-case smoke before any fold0 smoke.

## 10. Active Execution Record

Status before audit: plan created; first audit batch selected; no training/Slurm/submission/zip/weights/repo-clone has been run.

Status after first audit batch: completed first low-risk audit batch.

Executed:

- Created formal plan: `docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md`.
- Copied plan summary to `results/diagnostics/phase0_phase1/laneA_myops/round5_mechanism_integration_audit/round5_laneA_plan.md`.
- Added and ran diagnostic-only script: `scripts/diagnostics/laneA_round5_mechanism_audit.py`.
- Generated:
  - `alignment_feasibility_audit.csv` / `.md`
  - `anatomy_soft_prior_feasibility.csv` / `.md`
  - `boundary_distance_failure_audit.csv` / `.md`
  - `round5_laneA_decision_table.md`
  - `round5_next_implementation_prompt.md`

Not executed:

- No training.
- No Slurm submission.
- No validation zip or upload.
- No fold1-4 expansion.
- No external repo clone/build/train.
- No pretrained weight download.

Decision table summary:

| route | status | key evidence | next action |
| --- | --- | --- | --- |
| CAA-Seg/SSA-style alignment | `watch` | No geometry mismatch; weak body-bbox/HD95 correlation; 6 CenterC cases still have HD95 >= 20. | Do small visual/metadata review before SSA; current proxies alone are not enough. |
| Anatomy-guided cascade / soft prior | `go` | Round4 has 8 no-T2 empty-GT edema FP cases; remote/soft anatomy support explains important outliers. | Prototype soft anatomy support/penalty, explicitly no hard deletion. |
| Conservative boundary/distance objective | `watch` | Round4 has 13 remote-or-empty-FP modes versus 3 boundary-overreach modes. | Boundary loss only as small auxiliary after anatomy/remote-FP guard. |

Recommended next step: one bounded Lane A Round5 anatomy-guided soft prior smoke. The smoke should use soft distance/support features or penalties, preserve baseline Dice/CE, avoid hard deletion, keep class_5 scar as guardrail, and continue reporting T2-present GT-positive, complete-modality, CenterC, and no-T2 empty-GT subsets.
