# Lane A Round08 Next T2-Present Edema Expert And Separated Head Execution Plan

Plan metadata:
- Type: next/planned round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round08
- Status: next goal-mode controller, planning-only artifact
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round07_next_modality_presence_uncertainty_supervision_execution.md`
- Function: define the next staged, gated first-party route for a T2-present edema expert / separated edema supervision head after Round7 stopped before fold0 training
- Do not: execute experiments from this plan-writing pass; do not train; do not submit Slurm; do not create validation zip; do not upload; do not download weights; do not clone or train external repos; do not modify production code while creating this plan

## 1. 当前证据链和阶段判断

Lane A 目前的结论来自 Round2-Round7 的连续负证据和可复用工程证据：

1. **Round2: edema inference postprocess route fail.** Edema 小组件/ROI 后处理不能作为主线。删除 1-voxel edema 小岛后，component count 从 `3.3182` 降到 `1.7273`，但 GT-positive edema Dice 从 `0.3944` 降到 `0.3935`，HD95 从 `20.0115` 轻微变差到 `20.0234`。这说明简单小连通域删除和 ROI 阈值不能解决真实 T2-present edema localization/HD 问题。
2. **Round3: trainable wiring smoke pass, not performance proof.** Loss wiring、gradient、tiny-overfit 可以跑，`edema_focal_tversky + no_t2_edema_loss_downweighting` 被推进到 fold0 short train；但这只是工程 gate，不代表真实 fold0 性能。
3. **Round4: focal Tversky + no-T2 downweighting fold0 fail.** 真实 fold0 short train 失败，最终 gate 为 `fail_stop_no_longer_train`。失败模式包括 remote FP、no-T2 empty-GT 新增 edema FP、HD95 恶化、以及 class_5 scar guardrail 不干净。因此不能继续把单一 loss weight / Focal Tversky 当主线。
4. **Round5: mechanism audit.** Alignment 为 `watch`，boundary/distance 为 `watch`，anatomy soft prior 进入 bounded diagnostic。该轮提示 edema 错误和 remote/anatomy support 有关，但没有证明 hard ROI 或 postprocess 可以解决。
5. **Round6: current anatomy soft attenuation fail; missing-modality route go.** Anatomy soft attenuation 诊断为 `fail_stop_no_expand`。Missing-modality audit 说明 no-T2 empty-GT 不能当作强 negative；explicit modality presence 和 uncertainty-weighted supervision 是下一步信号，但 AdaMM/UniME/I-MMSeg 等完整外部 repo 仍应 postpone。
6. **Round7: first-party 6-channel modality-presence pipeline technically viable, but scalar no-T2 weighting fail.** Round7 证明了 6-channel channel injection、network init、validation/export hook、AMP-safe loss wiring可以运行；但 `modality-presence + fixed no-T2 weighting` policy 没通过 tiny gate。U1 太弱，在 T2-present GT-positive cases 上没有 edema signal；U2 有 edema signal，但引入 no-T2 empty-GT edema FP。因此 Round7 不能进入 fold0 training。

当前关键结论：

- Round7 **不是**证明 “modality-aware model 失败”。
- Round7 证明的是 “简单 presence channels + scalar no-T2 weighting 不够”。
- 下一阶段不能继续在 U1/U2 权重附近微调，也不能回到 Focal Tversky、small-component deletion、hard ROI deletion、anatomy attenuation。
- 下一阶段应升级为：

```text
T2-present edema expert + separated edema head/route + modality-conditioned supervision
```

核心思想：

- Scar class_5 主要由 LGE-driven signal 学，应继续利用所有合适的 LGE-containing cases。
- Edema class_4 主要依赖 T2，应从 T2-present / complete C0+LGE+T2 cases 中强监督学习，重点看 CenterB、CenterC。
- no-T2 empty-GT cases 不应作为 dense class_4 hard negative 污染 edema head；它们更适合作为 abstention、uncertainty、weak regularization 或 calibration signal。
- 模型必须显式知道 `C0/LGE/T2` 是否存在；presence channel 是基础设施，不是完整解决方案。

## 2. 输出根目录和命名约束

Round8 所有输出必须隔离到：

```text
results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert/
```

建议输出文件：

- `round8_goal_execution_readme.md`
- `round8_train_config.yaml`
- `round8_train_commands.txt`
- `round8_network_init_smoke.md`
- `round8_unit_gradient_smoke.csv`
- `round8_tiny_overfit_metrics.csv`
- `round8_fold0_very_short_metrics.csv`
- `round8_fold0_short_train_metrics.csv`
- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`
- `round8_decision_table.md`
- `round8_next_actions.md`

Optional overlays, if generated without heavy dependencies:

```text
results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert/failure_overlays/
```

Experiment names and cache roots must be unique. Suggested train experiment prefix:

```text
laneA_t2_edema_expert_sephead_fold0_<budget>
```

Do not overwrite any nnU-Net501 baseline, Round4, Round6, or Round7 output/cache.

## 3. Phase 1: `round8_reproducibility_and_code_reuse_gate`

### Goal

复核并复用 Round7 已经通过的 6-channel channel-injection / network-init / validation-export 代码，建立 Round8 独立 trainer/config/output。不要重新发明数据通道逻辑。

### Allowed

- Read and reuse Round7 helpers from `src/care_myocardium/nnunet/laneA_round7_trainer.py`:
  - `MODALITY_PRESENCE_ORDER`
  - `load_case_modality_map`
  - `append_modality_presence_channels`
  - `append_modality_presence_to_case`
- Create Round8 first-party trainer/loss wrappers under `src/care_myocardium/nnunet/`.
- Create Round8 diagnostic/eval scripts under `scripts/diagnostics/`.
- Create one bounded Round8 job entrypoint under `jobs/nnUNet/` only after smoke gates pass.
- Check:
  - nnU-Net Dataset501 fold0 split unchanged.
  - Label semantics unchanged: background, myocardium, LV, RV, `edema=4`, `scar=5`.
  - First conv input channels are 6.
  - validation/export path injects modality presence channels.
  - baseline reference remains existing nnU-Net501 fold0, not retrained.
  - evaluator still reports `myops_edema` and `myops_scar` separately.

### Forbidden

- Do not rewrite Dataset501 preprocessing or label mapping.
- Do not modify baseline nnU-Net plans/cache.
- Do not create validation zip or upload.
- Do not train in this phase.
- Do not use external data, validation pseudo-label supervised training, or downloaded weights.

### Outputs

- `round8_goal_execution_readme.md`
- `round8_train_config.yaml`
- `round8_train_commands.txt`
- `round8_network_init_smoke.md`
- `round8_unit_gradient_smoke.csv` with setup rows if no gradient is run yet

### Pass Criteria

- Fold0 split, metadata, baseline prediction directory, and label semantics are found.
- 6-channel input path initializes a Round8 network with first conv input channel count `6`.
- validation/export helper can append modality presence channels to one preprocessed case.
- Output/cache roots are isolated under Round8-specific names.

### Fail Criteria

- Any silent label/evaluator/fold change is detected.
- Round8 trainer points at Round7/Round4 output folders.
- validation/export would feed 3-channel inputs into a 6-channel network.
- Any production baseline cache would be overwritten.

### Next Stage

If pass, proceed to `separated_edema_head_design`.

## 4. Phase 2: `separated_edema_head_design`

### Goal

把 class_4 edema 从 shared multiclass supervision 中功能性分离出来，避免 no-T2 empty-GT cases 对 edema head 施加强 dense negative，同时保留 scar/anatomy supervision。

### Candidate A: Functional Separation With Existing Segmentation Head

Minimum-risk first implementation.

Design:

- Shared encoder and existing nnU-Net segmentation head remain unchanged.
- Keep 6-channel inputs: original 3 modalities plus `C0_present/LGE_present/T2_present`.
- Replace or wrap the loss so class_4 supervision is case-aware:
  - T2-present cases use full 6-class supervision and a class_4 edema expert auxiliary term.
  - no-T2 cases train background/anatomy/scar through a reduced non-edema class loss, but do not apply dense class_4 hard-negative CE/Dice.
  - Scar class_5 remains supervised on all LGE-containing cases.
- A practical implementation is a `SeparatedEdemaLoss`:
  - for T2-present samples: standard multiclass Dice/CE plus class_4 expert auxiliary loss;
  - for no-T2 samples: compute non-edema Dice/CE over classes `[0,1,2,3,5]` with class_5 remapped inside the reduced loss, plus optional weak edema regularizer;
  - no-T2 weak regularizer must not be equivalent to dense hard negative.

Why this is first:

- It can reuse the Round7 trainer channel logic.
- It does not require invasive access to decoder internals.
- It directly targets the Round7 failure: fixed scalar no-T2 weighting still let supervision conflict leak into class_4.

Risk:

- The main segmentation head still outputs class_4 for all cases, so weak regularization and inference stability must be monitored.

### Candidate B: Shared Encoder + Scar/Anatomy Main Head + Edema Auxiliary Head

Enhanced implementation only if A passes wiring and one-batch gates, or if it can be implemented without a large nnU-Net rewrite.

Design:

- Main segmentation head keeps anatomy and scar training stable.
- Add an edema-specific auxiliary head or auxiliary logits path trained strongly only on T2-present / complete cases.
- During inference:
  - either fuse edema auxiliary logits into main class_4 logits with a fixed conservative rule;
  - or use the auxiliary head only as a training signal while exporting the main segmentation logits.
- Class_5 scar must not route through the edema auxiliary head.

Implementation constraints:

- Avoid rewriting nnU-Net trainer/dataloader.
- Prefer a shallow wrapper only if final decoder features or segmentation logits are accessible cleanly.
- If decoder-feature access is brittle, postpone B and continue with Candidate A.

Risk:

- More moving parts can destabilize validation export and checkpoint loading.
- Auxiliary head fusion can create no-T2 FP if not gated by modality presence.

### Candidate C: Modality-Conditioned Head / FiLM-Like Conditioning

Optional only after A or B shows clean signal.

Design:

- Use modality presence vector to generate lightweight feature scale/shift or head bias.
- T2-present branch can emphasize edema features; no-T2 branch can abstain/calibrate.

Why not first:

- Round8 should not jump into MoE/AdaMM/UniME/CoPeDiT-style complexity before a first-party separation route shows value.

### Allowed

- Implement Candidate A first.
- Implement B only as a small auxiliary signal if easy and gated.
- Write unit tests for class_4/class_5 gradient isolation.

### Forbidden

- Do not implement full MoE, AdaMM, UniME, CoPeDiT, I-MMSeg, or external repo distillation in Round8 first pass.
- Do not add hard ROI deletion.
- Do not change label semantics.

### Outputs

- `round8_train_config.yaml` with selected candidate `A`, `A+B`, or postponed status.
- `round8_network_init_smoke.md`
- `round8_unit_gradient_smoke.csv`

### Pass Criteria

- Import/py_compile pass.
- Network forward works with 6-channel input.
- For no-T2 samples, class_4 receives no dense hard-negative loss path.
- Class_5 scar gradients remain finite and nonzero where scar labels exist.
- T2-present class_4 gradients are finite and nonzero.

### Fail Criteria

- class_4 masking also suppresses class_5 scar.
- no-T2 loss is still equivalent to dense edema hard negative.
- output channel count or label mapping changes.
- validation/export cannot load or save predictions.

### Next Stage

If Candidate A passes, proceed to `t2_present_edema_expert_supervision`. If A fails because nnU-Net loss wrapping is too invasive, stop and record implementation blockers before attempting B.

## 5. Phase 3: `t2_present_edema_expert_supervision`

### Goal

重新设计 class_4 edema supervision，使 edema expert 主要学习 “T2 present 时如何分 edema”，同时避免 no-T2 inference 完全发散。

### Supervision Policy

#### T2-present / complete cases

- Use strong class_4 edema supervision.
- Include both Dice/CE-style voxel supervision and optional small auxiliary T2-present edema expert term.
- Focus reporting on:
  - T2-present GT-positive edema
  - complete-modality cases
  - CenterB
  - CenterC
- CenterC is a hard diagnostic subset because baseline CenterC edema Dice/HD95 remains poor.

#### no-T2 empty-GT cases

- Do not use dense hard-negative BCE/Dice for class_4.
- Do not treat empty edema labels as certain “no edema” pathology truth.
- Allowed weak controls:
  - `abstention_regularization`: weakly discourage high-confidence class_4 only when T2 is absent.
  - `very_weak_negative_regularization`: small penalty on extreme class_4 probability, not full voxelwise negative CE.
  - `confidence_penalty`: discourage overconfident edema logits in no-T2 cases without enforcing zero edema everywhere.
  - `loss_masking`: remove class_4 from no-T2 dense loss, used as a baseline.
  - `background_calibration`: calibrate non-edema classes while leaving class_4 uncertain.
- Every policy must record the exact formula, coefficient, and whether class_4 logits receive gradients on no-T2 cases.

#### class_5 scar

- Continue LGE-driven all-case supervision.
- Treat scar as hard guardrail:
  - class_5 Dice must not materially regress;
  - class_5 HD/HD95 must not materially worsen;
  - scar gradients must not be accidentally masked.

#### background/anatomy classes

- Keep original background/myocardium/LV/RV supervision where possible.
- Do not degrade anatomy segmentation just to improve edema.

### no-T2 FP Gate Logic

no-T2 edema FP should no longer be an automatic one-voxel veto, but it must be tightly bounded.

Suggested thresholds:

- Tiny-overfit smoke:
  - preferred: `0` no-T2 class_4 FP voxels;
  - watch: total no-T2 class_4 FP voxels `<= 5` and no component larger than `5` voxels;
  - fail: total no-T2 class_4 FP voxels `> 10`, any remote FP component, or more than one no-T2 smoke case with class_4 FP.
- Fold0 very-short / short:
  - preferred: no-T2 FP case count `0/28`;
  - watch: no-T2 FP case count `<= 1/28`, total no-T2 edema FP voxels `<= 100`, component count `<= 1` in the FP case, and no remote component;
  - fail: no-T2 FP case count `> 1/28`, total no-T2 edema FP voxels `> 100`, any large/remote component, or any no-T2 FP that drives all-case metric improvement artifact.

These thresholds must be recorded in `round8_train_config.yaml` and `round8_decision_table.md`.

### Outputs

- `round8_unit_gradient_smoke.csv`
- `round8_tiny_overfit_metrics.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_guardrail_table.csv`

### Pass Criteria

- T2-present GT-positive edema cases show a nonzero positive signal in tiny-overfit.
- CenterB and CenterC selected cases both show class_4 learning signal.
- no-T2 FP stays within the strict bound.
- class_5 scar gradients and tiny metrics remain stable.

### Fail Criteria

- T2-present edema signal remains zero, as in Round7 U1.
- T2-present signal appears only by causing no-T2 FP instability, as in Round7 U2.
- scar class_5 is masked, destabilized, or degraded.
- implementation silently changes background/anatomy labels.

### Next Stage

If pass, proceed to `bounded_training_ladder`.

## 6. Phase 4: `bounded_training_ladder`

### Goal

允许后续 goal-mode 在资源充足时尽可能推进，但推进方式必须 staged, gated, and evidence-driven。不能因为 GPU/token 充足就跳过 gate。

### Ladder

1. **import / py_compile / config smoke**
   - Allowed: static imports, config materialization, output-root checks.
   - Forbidden: training, Slurm, validation zip.
   - Outputs: `round8_train_config.yaml`, `round8_train_commands.txt`.
   - Pass: imports clean, output roots isolated.
   - Fail: any import/runtime dependency blocker.

2. **one-batch forward + backward**
   - Allowed: one or a few in-memory batches on selected fold0 training cases.
   - Forbidden: epoch training.
   - Outputs: `round8_unit_gradient_smoke.csv`.
   - Pass: finite loss, finite class_4/class_5 gradients, expected no-T2 class_4 behavior.
   - Fail: NaN/Inf, class_4 no T2 hard-negative leakage, class_5 interference.

3. **tiny-overfit**
   - Cases should include:
     - at least one CenterB complete T2-present GT-positive edema case;
     - at least one CenterC complete T2-present GT-positive edema case;
     - at least one C0+LGE no-T2 empty-GT case;
     - at least one LGE-only no-T2 empty-GT case.
   - Outputs: `round8_tiny_overfit_metrics.csv`, `no_t2_empty_gt_fp_table.csv`.
   - Pass: T2-present edema signal and no-T2 FP within threshold.
   - Fail: no positive edema signal, no-T2 FP above threshold, scar guardrail regression.

4. **fold0 very-short train**
   - Allowed only after tiny gate passes.
   - Suggested budget: `3-5` epochs, `5-10` iterations/epoch, one candidate only.
   - Use `htzhulab` by default; if queue is materially long, follow AGENTS.md fallback rules.
   - Outputs: `round8_fold0_very_short_metrics.csv`, `baseline_vs_candidate_by_subset.csv`.
   - Pass: at least watch-level clean signal on T2-present/CenterC without no-T2 FP instability.
   - Fail: training instability, no positive signal, no-T2 FP above threshold, scar guardrail regression.

5. **fold0 short train**
   - Allowed only if fold0 very-short is clean.
   - Suggested budget: within normal <=8h round budget; do not use long 1000/2000 epoch runs.
   - Outputs: `round8_fold0_short_train_metrics.csv`, updated subset tables.
   - Pass: clean positive signal vs nnU-Net fold0 baseline.
   - Fail: any gate regression.

6. **fold0 longer train**
   - Allowed only if fold0 short train passes and user resources are available.
   - Still fold0 only unless the user explicitly authorizes fold1-4 after reviewing the decision table.

### Hard Forbidden Throughout Round8

- fold1-4 or 5-fold training without explicit later authorization.
- validation zip creation.
- hosted submission/upload.
- direct jump from one-batch to full train.
- external repo clone/build/train.
- downloaded large pretrained weights.
- external data training.
- validation pseudo-label supervised training.
- hard ROI deletion or postprocess-only promotion.

## 7. Phase 5: `evaluation_and_decision_gate`

### Goal

统一评估 Round8 candidate 是否值得继续。不要用 foreground mean 或 all-case aggregate 掩盖失败。

### Required Metrics And Subsets

Report separately:

- `myops_edema` class_4
- `myops_scar` class_5

Subsets:

- all-case
- T2-present GT-positive
- complete-modality
- CenterB
- CenterC
- no-T2 empty-GT
- C0+LGE no-T2
- LGE-only
- all center groups
- modality groups

Metrics:

- Dice
- HD
- HD95
- component count
- small FP
- remote FP
- pred/GT volume ratio
- no-T2 edema FP voxel count
- no-T2 edema FP case count
- scar guardrail Dice/HD95
- case-level failure flags

### Decision Labels

#### `go`

Eligible to advance to the next bounded ladder stage if all are true:

- T2-present GT-positive edema or CenterC complete-case edema shows clean positive signal.
- Dice and HD95 do not show a severe trade-off.
- component count and remote FP do not materially worsen.
- no-T2 empty-GT FP remains within the strict upper bound.
- class_5 scar Dice/HD95 does not materially regress.
- improvement is not driven by empty-GT artifact or all-case aggregate only.

#### `watch`

Hold or repeat a bounded smoke if:

- T2-present edema signal is positive but small;
- no-T2 FP is within watch threshold, not fail threshold;
- scar guardrail is clean;
- HD95/component are neutral, not clearly improved.

`watch` does not authorize fold expansion or submission.

#### `fail`

Stop current candidate if any are true:

- no T2-present edema signal.
- CenterC does not improve or worsens.
- Dice improves but HD95/component/remote FP clearly worsens.
- scar guardrail is not clean.
- no-T2 empty-GT FP exceeds threshold.
- training has NaN/Inf or unstable loss.
- cache/label/evaluator/preprocessing changes silently.

#### `stop`

Stop the current Round8 route, not just the candidate, if:

- Candidate A and a minimally feasible Candidate B both fail the same gate.
- The only improvements are all-case/empty-GT artifacts.
- First-party separated edema route cannot be implemented without rewriting nnU-Net internals or changing label semantics.

### Outputs

- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`
- `round8_decision_table.md`
- `round8_next_actions.md`

## 8. Controlled External Method Readiness

This is not part of the first Round8 execution. It is only a readiness branch for later controlled integration.

External methods are mechanism sources, not default pipelines:

| mechanism slot | candidates | Round8 stance |
| --- | --- | --- |
| missing-modality routing / student-teacher / modality-conditioned representation | AdaMM, UniME, CoPeDiT, MoE, MMPL-Seg | watch/postpone until first-party separated edema route gives a clean signal or clearly fails |
| modality/intensity prior for edema/scar | I-MMSeg | watch; can inspire prompt/intensity priors, but no CLIP/GPT/foundation stack in first Round8 pass |
| alignment | CAA-Seg, SSA | watch from Round5; only metadata/one-case audit if CenterC failure remains alignment-like |
| anatomy prior | Cascaded FSN, PT-Net | watch; do not hard-delete edema |
| boundary/HD | InverseForm, surface loss, HD loss | watch; consider only as small auxiliary after remote/no-T2 FP is controlled |
| pretrained backbone | BiomedParse, MedNeXt, nnU-Net Task114/M&Ms | watch; pretrained weights require compliance and source-data audit |

Before any external repo enters a later goal-mode implementation, it must pass:

1. license/compliance screen;
2. pretrained data source screen;
3. external data risk assessment under CARE rule: pretrained weights may be allowed, external training data is not;
4. input-output shape compatibility;
5. label mapping compatibility with `edema=4`, `scar=5`;
6. one-case smoke;
7. fold0 smoke.

Do not clone/train all repos indiscriminately. Do not use external data training or validation pseudo-label supervised training.

## 9. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请按计划执行 Lane A Round8：

`docs/plans/laneA_round08_next_t2_present_edema_expert_separated_head_execution.md`

目标是尽可能推进 first-party 的 `T2-present edema expert + separated edema supervision/head` 路线，但必须 staged/gated。资源充足时可以从实现推进到 smoke、tiny-overfit、fold0 very-short、fold0 short；但每个阶段必须通过 gate，失败即停，不得自动扩大规模。

请先读取：

- `docs/plans/care_myocardium_plan_registry_rules.md`
- `docs/plans/laneA_round07_next_modality_presence_uncertainty_supervision_execution.md`
- `results/diagnostics/care_myocardium/laneA_myops/round07_modality_uncertainty/`
- `src/care_myocardium/nnunet/laneA_round7_trainer.py`
- `scripts/diagnostics/laneA_round07_modality_uncertainty.py`
- `jobs/nnUNet/laneA_round7_fold0_very_short_train.sh`
- Round2-Round6 Lane A plan/output files referenced in the Round8 plan

执行边界：

- 复用 Round7 6-channel modality-presence pipeline，不要重新发明通道注入逻辑。
- 新建 Round8 独立 trainer/config/output，不能覆盖 nnU-Net501 baseline、Round4、Round6、Round7 cache。
- 优先实现 Candidate A：functional separated edema supervision。
- T2-present / complete cases 对 class_4 edema 强监督。
- no-T2 empty-GT cases 不作为 dense class_4 hard negative；使用 masking/abstention/very weak regularization/confidence penalty，并明确记录公式和系数。
- class_5 scar 继续 all suitable LGE-containing cases 监督，并作为 hard guardrail。
- 如果 Candidate A 通过 one-batch/tiny gates，再考虑最小 Candidate B auxiliary edema head；不要实现复杂 MoE/AdaMM/UniME/CoPeDiT/I-MMSeg 或外部 repo。

必须输出到：

`results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert/`

至少生成：

- `round8_goal_execution_readme.md`
- `round8_train_config.yaml`
- `round8_train_commands.txt`
- `round8_network_init_smoke.md`
- `round8_unit_gradient_smoke.csv`
- `round8_tiny_overfit_metrics.csv`
- `round8_fold0_very_short_metrics.csv`（若进入该阶段）
- `round8_fold0_short_train_metrics.csv`（若进入该阶段）
- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_fp_table.csv`
- `centerB_centerC_edema_table.csv`
- `scar_guardrail_table.csv`
- `case_level_failure_flags.csv`
- `round8_decision_table.md`
- `round8_next_actions.md`

训练梯度：

1. import / py_compile / config smoke
2. one-batch forward + backward
3. tiny-overfit on CenterB/CenterC T2-present GT-positive cases plus no-T2 empty-GT cases
4. fold0 very-short train only if tiny gate passes
5. fold0 short train only if very-short gate passes
6. fold0 longer train only if short train passes and user later authorizes

禁止：

- 不要创建 validation zip。
- 不要上传或 submission。
- 不要训练 fold1-4 或 5-fold，除非用户在本 goal 后另行授权。
- 不要下载权重。
- 不要拉取或训练大型外部 repo。
- 不要使用 external data training。
- 不要使用 validation pseudo-label supervised training。
- 不要 hard ROI deletion。
- 不要通过 foreground mean 或 all-case aggregate 判定成功。

评估必须分别报告 `myops_edema` class_4 和 `myops_scar` class_5，并按 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、C0+LGE no-T2、LGE-only、center groups 报告 Dice、HD、HD95、component count、small/remote FP、pred/GT volume ratio、no-T2 FP voxel/case count、scar guardrail 和 case-level flags。

最终更新 Round8 active execution record 和 `round8_decision_table.md`，给出 `go`、`watch`、`fail` 或 `stop`。如果任一 gate fail，停止当前 candidate 并记录原因，不得自动扩大训练。
```

## 10. Active Execution Record

Execution status: Round8 implementation, low-risk gates, and bounded fold0 very-short train/eval completed.

Execution date: 2026-05-22.

Implemented first-party files:

- `src/care_myocardium/nnunet/laneA_round8_trainer.py`
- `scripts/training/run_laneA_round8_nnunet_train.py`
- `scripts/diagnostics/laneA_round08_t2_edema_expert.py`
- `scripts/diagnostics/laneA_round8_fold0_eval.py`
- `jobs/nnUNet/laneA_round8_fold0_very_short_train.sh`

Generated output root:

```text
results/diagnostics/care_myocardium/laneA_myops/round08_t2_edema_expert/
```

Executed:

- Setup/reproducibility gate.
- Reuse of Round7 6-channel modality-presence channel injection.
- Round8 network-init smoke.
- Round8 validation/export channel helper smoke.
- Unit/gradient smoke for functional separated edema supervision.
- Tiny-overfit and policy screen for Candidate A.

Not executed:

- no fold0 short/longer training;
- no fold1-4 or 5-fold;
- no validation zip;
- no upload;
- no pretrained weight download;
- no external repo clone/build/train;
- no external data training;
- no validation pseudo-label supervised training.

Key implementation details:

- Candidate A uses a shared nnU-Net segmentation head with functional class_4 edema separation in the loss.
- T2-present samples receive full segmentation supervision plus a positive-weighted class_4 edema expert auxiliary term.
- no-T2 samples train dense non-edema classes `[0,1,2,3,5]` and do not provide dense class_4 hard-negative CE/Dice.
- A small modality-conditioned T2-absent class_4 logit bias is applied as an abstention mechanism; T2-present samples are not biased.
- class_5 scar remains supervised through the non-edema/full segmentation route and remains a hard guardrail.

Current gate results:

| stage | status | evidence | next action |
| --- | --- | --- | --- |
| setup/reproducibility | pass | Required plan, metadata, preprocessed Dataset501, fold0 baseline, and labels found. | Continue. |
| network/init/export | pass | Round8 network first conv expects 6 channels; validation/export helper injects modality-presence channels. | Continue. |
| unit/gradient | pass | class_4/class_5 gradients finite; no-T2 dense class_4 hard negative disabled. | Continue. |
| tiny-overfit | pass | Selected `A1_mask_class4_no_t2_boost3`: CenterB edema Dice `0.3415`, CenterC edema Dice `0.4117`, no-T2 edema FP voxels `0`, no-T2 FP cases `0`. | Fold0 very-short train allowed. |
| fold0 very-short | fail | Job `51995027` completed 3 epochs, exported 44/44 fold0 validation predictions, and ran evaluator. all-case edema Dice delta `-0.3688`; T2-present edema HD95 improvement delta `-137.7621`; scar Dice delta `-0.5531`. | Stop current candidate; do not train longer. |

Current decision:

```text
fail_stop_no_longer_train
```

Executed command:

```bash
sbatch jobs/nnUNet/laneA_round8_fold0_very_short_train.sh
```

Interpretation:

- Round8 improved over Round7 at the smoke level: the model had T2-present edema signal while keeping no-T2 empty-GT FP at zero on the tiny smoke cases.
- The real fold0 very-short path failed severely. T2-present edema, CenterC edema, HD95/component/remote FP, and scar guardrail all regressed.
- no-T2 edema FP control alone is insufficient and cannot justify further training.
- The current candidate must not proceed to fold0 short/longer, fold1-4, validation zip, or submission.
- If Lane A continues, the next route should preserve nnU-Net representation quality, for example baseline-initialized fine-tuning or adding separated edema supervision without training the whole model from scratch under this short budget.
