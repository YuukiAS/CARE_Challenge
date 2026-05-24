# Lane A Round07 Next Modality Presence Uncertainty Supervision Execution

Plan metadata:
- Type: next execution controller
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round07 modality presence conditioning and uncertainty-weighted edema supervision
- Status: active; first implementation/diagnostic pass completed
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round06_next_anatomy_soft_prior_and_missing_modality_route_execution.md`
- Function: define a staged, gated goal-mode controller for first-party explicit modality-presence conditioning plus uncertainty-weighted no-T2 edema supervision
- Do not: continue small-component postprocess, ROI thresholding, hard anatomy deletion, Focal Tversky-only tuning, current anatomy soft attenuation, validation submission, fold1-4, 5-fold, external data training, validation pseudo-label supervised training, large pretrained weight download, or bulk external repo integration

## 1. Summary And Current Evidence Chain

Round07 should proceed because Round2-Round6 have narrowed Lane A to a missing-modality supervision/routing problem rather than a simple postprocess or single-loss problem.

Evidence chain to preserve:

- Round2: edema inference postprocess route failed. Removing 1-voxel edema islands reduced component count but worsened GT-positive edema Dice and HD95; stop small components, ROI thresholds, and inference-side suppression as mainline.
- Round3: loss wiring, gradient smoke, and tiny-overfit smoke passed; this only proved the training plumbing can run, not that performance improves.
- Round4: `edema_focal_tversky + no_t2_edema_loss_downweighting` failed real fold0 short train with remote FP, no-T2 FP, HD95 regression, all-case edema Dice drop, and unclean scar guardrail.
- Round5: alignment is `watch`, boundary/distance is `watch`, anatomy soft prior was worth one bounded diagnostic.
- Round6: `anatomy_soft_prior_oracle_diagnostic` failed with `fail_stop_no_expand`; even oracle GT-myocardium soft attenuation did not cleanly improve CenterC or component behavior.
- Round6 missing-modality audit gives the strongest next signal: explicit modality presence channel / FiLM-like conditioning is `go`; uncertainty-weighted no-T2 edema supervision is `go`; hard negative is `reject`; masking/downweighting are `watch`; AdaMM/UniME/I-MMSeg-style full distillation is `postpone`.

Strategic decision:

- Round07 mainline is first-party modality-aware edema supervision.
- The model must explicitly know whether `C0`, `LGE`, and `T2` are present.
- No-T2 empty-GT cases must not be strong class_4 edema negatives.
- Class_4 edema supervision should become uncertainty-aware.
- Class_5 scar remains a hard guardrail.
- Hard gates are CenterC complete-case edema, T2-present GT-positive edema, no-T2 empty-GT stability, HD95, remote FP, component count, and scar Dice/HD95.

All Round07 outputs must be isolated under:

```text
results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/
```

## 2. Stage-Gated Goal-Mode Execution

### Stage 1: `round7_setup_and_reproducibility_gate`

Goal:

- Reconfirm Round6 outputs, fold0 split, nnU-Net501 baseline reference, label semantics, modality/center metadata, evaluation scripts, cache isolation, and output roots before any implementation or training.

Allowed:

- Create Round07 output root and execution README.
- Create first-party config templates, diagnostic wrappers, and train/eval script skeletons.
- Read existing fold0 split, Dataset501 labels, baseline validation predictions/probabilities, cases metadata, Round3-Round6 outputs.
- Confirm label semantics: compact `4=edema/myops_edema`, `5=scar/myops_scar`; raw submission labels remain unchanged.
- Confirm baseline cache path and require candidate-specific output directories.

Forbidden:

- Training.
- Slurm submission.
- Validation zip or upload.
- Modifying label/evaluator/fold semantics.
- Reusing or overwriting nnU-Net501 baseline cache.

Required outputs:

- `round7_goal_execution_readme.md`
- `train_config_modality_presence.yaml`
- `train_config_uncertainty_weighted.yaml`
- `train_commands.txt`

Pass criteria:

- Fold0 val cases, baseline predictions, metadata, and evaluator are found.
- Configs record experiment name, seed, fold, channel policy, loss policy, output dir, and cache isolation.
- No mismatch in label semantics or baseline reference.

Fail criteria:

- Missing fold0 reference, ambiguous label mapping, evaluator mismatch, or candidate output path overlaps baseline cache.

Next:

- Pass -> Stage 2.
- Fail -> stop with `fail_setup_reproducibility`.

### Stage 2: `modality_presence_conditioning_implementation`

Goal:

- Implement the smallest first-party modality presence conditioning that can be tested without adopting a full external missing-modality framework.

Candidate M1, primary: `input_level_modality_presence_channels`

- Append constant channels indicating `C0_present`, `LGE_present`, `T2_present`.
- Each channel is spatially constant per case and matches the image tensor shape.
- Preferred first candidate because it is transparent, testable, and avoids architecture rewrite.
- Requires a candidate-specific nnU-Net config/plans path or training wrapper that does not contaminate Dataset501 baseline preprocessing/cache.
- Must record final effective channel count and how missing image modalities are represented.

Candidate M2, secondary: `lightweight_film_modality_conditioning`

- Use modality presence vector to generate feature scale/shift or head conditioning.
- Only enter after M1 import/forward/gradient smoke is clean.
- Must stay lightweight; no MoE, UniME, AdaMM, or CoPeDiT-style framework implementation in Round07.

Why no full external missing-modality repo now:

- Round6 showed first-party modality mask and uncertainty policy are the immediate signal.
- Complete-case teacher is not reliable enough for distillation, especially CenterC.
- External repos require license/compliance/pretrained-data/input-output/label-mapping/one-case smoke gates before training.

Allowed:

- Add first-party trainer/wrapper under `src/care_myocardium/nnunet/`.
- Add training launcher under `scripts/training/`.
- Add diagnostics/eval wrapper under `scripts/diagnostics/`.
- Add job script only for a single bounded fold0 candidate if later stages pass.
- Run import/unit tests, one-batch forward, and gradient smoke.

Forbidden:

- Broad dataloader rewrite.
- Silent preprocessing changes.
- Label/evaluator changes.
- External repo clone/build/train.
- Fold1-4 or full schedule.

Required outputs:

- `unit_gradient_smoke.csv`
- update `train_config_modality_presence.yaml`
- update `train_commands.txt`

Pass criteria:

- Import succeeds.
- One-batch forward succeeds with expected channel count.
- Gradients are finite.
- Class_4 logits receive nonzero gradient on T2-present GT-positive samples.
- Class_5 scar gradient/metrics are not accidentally disabled.
- No NaN/Inf.

Fail criteria:

- Shape/channel mismatch, baseline cache pollution, NaN/Inf, missing class_4 gradient, unexpected class_5 interference, or need for broad nnU-Net rewrite.

Next:

- Pass M1 -> Stage 3.
- If M1 fails due local wiring only -> fix once and repeat Stage 2.
- If M1 fails due architectural incompatibility -> mark M1 `stop`, consider M2 only if it can be tested with isolated wrapper.
- If both fail -> stop Round07 implementation.

### Stage 3: `uncertainty_weighted_no_t2_edema_supervision`

Goal:

- Replace no-T2 class_4 hard-negative behavior with uncertainty-aware supervision while preserving strong T2-present edema supervision.

Policy U1, primary: `uncertainty_weighted_low_negative`

- T2-present GT-positive cases: normal class_4 edema supervision.
- No-T2 empty-GT cases: class_4 negative supervision uses low bounded weight, not zero and not full strength.
- Recommended initial no-T2 class_4 negative weight: `0.05`.
- Rationale: Round4 `0.25` downweighting still introduced no-T2 FP; `0.05` is conservative and reduces center/modality shortcut risk.

Policy U2, primary/secondary: `modality_conditioned_uncertainty_weighting`

- Weight class_4 edema loss by modality reliability:
  - `C0+LGE+T2`: `1.0`
  - `C0+LGE`: `0.05`
  - `LGE-only`: `0.05`
- Record center in metrics but do not use center as direct training target or shortcut feature.
- Use modality presence vector for conditioning, not center label.

Policy U3, diagnostic only: `teacher_or_prediction_confidence_weighted`

- Allowed only as analysis or diagnostic.
- Must not use validation pseudo-label supervised training.
- Must not rely on current complete-case teacher as truth, because Round6 teacher feasibility was `postpone` for CenterC.
- May compute confidence summaries from training predictions only if clearly marked non-supervised diagnostic.

Allowed:

- Implement class_4 auxiliary weighting or replacement policy.
- Keep nnU-Net multiclass base loss and class_5 scar supervision intact.
- Log sample-level class_4 weight, modality group, center, edema GT status, class_4 gradient norm, class_5 gradient norm.

Forbidden:

- Hard negative no-T2 class_4 supervision.
- Treating no-T2 empty-GT as reliable edema absence.
- Training on validation pseudo-labels.
- Using center label as a direct model input.

Required outputs:

- `train_config_uncertainty_weighted.yaml`
- appended rows in `unit_gradient_smoke.csv`
- `no_t2_empty_gt_stability.csv` once predictions exist

Pass criteria:

- T2-present GT-positive class_4 supervision remains strong.
- No-T2 class_4 negative contribution is bounded and logged.
- No class_5 scar loss disablement.
- No NaN/Inf.
- Gradient smoke shows no-T2 class_4 gradient is low but finite when expected.

Fail criteria:

- No-T2 behaves as full hard negative.
- T2-present class_4 gradient is weakened unintentionally.
- Scar class_5 gradient is damaged.
- Teacher/confidence policy leaks validation pseudo-label supervision.

Next:

- Pass -> Stage 4.
- Fail -> stop policy candidate and return to U1 only if failure came from U2/U3.

### Stage 4: `bounded_training_ladder`

Goal:

- Allow goal-mode to advance aggressively only through staged gates.

Training ladder:

1. `loss_unit_gradient_smoke`
2. `tiny_overfit`
3. `fold0_very_short_train`
4. `fold0_short_train`
5. `fold0_longer_train`
6. fold1-4 / 5-fold: not allowed in this plan without separate user authorization after clean fold0 gates

Allowed progression:

- Goal-mode may complete implementation, unit tests, tiny-overfit, fold0 very-short train, fold0 short train, evaluation, and decision table in one run if every previous gate passes.
- Goal-mode may enter fold0 longer train only if fold0 short train has clean positive signal and no fail criteria.
- Each stage must stop immediately on fail.

Suggested budgets:

- tiny-overfit: 2-6 cases, include CenterC T2-present GT-positive and no-T2 empty-GT.
- fold0 very-short: 3-5 epochs or equivalent small iteration cap.
- fold0 short: <=20 epochs, <=8h walltime.
- fold0 longer: only after clean short-train gate; still fold0 only and <=8h unless user separately authorizes more.

Experiment naming:

```text
laneA_modpresence_uncertainty_fold0_<stage>
```

Candidate priority:

1. M1 + U1: input-level modality presence channels + uncertainty-weighted low negative.
2. M1 + U2: input-level channels + modality-conditioned uncertainty weighting.
3. M2 + U1/U2: only if M1 is clean but insufficient and FiLM implementation remains small.

Required per-stage records:

- command
- config
- random seed
- fold split
- experiment name
- output dir
- epoch/iteration budget
- baseline comparison path
- failure flags

Required outputs:

- `tiny_overfit_metrics.csv`
- `fold0_short_train_metrics.csv`
- `baseline_vs_candidate_by_subset.csv`
- `centerC_failure_table.csv`
- `case_level_failure_flags.csv`
- optional `failure_overlays/`

Pass criteria:

- tiny-overfit: no NaN/Inf, overfits selected GT-positive edema without creating no-T2 edema FP, scar remains trainable.
- fold0 very-short: predictions export for all fold0 validation cases; label set valid; no cache pollution.
- fold0 short: clean positive signal on T2-present GT-positive edema or CenterC complete-case edema, no HD95/component/remote-FP regression, no new no-T2 FP, scar guardrail clean.
- fold0 longer: only if short train passes; must confirm signal persists rather than overfitting empty-GT artifacts.

Fail criteria:

- Any NaN/Inf.
- Missing prediction export.
- Label/evaluator/cache silent change.
- Dice gain with HD95/component/remote-FP regression.
- no-T2 empty-GT edema FP increase.
- scar Dice/HD95 clear regression.
- CenterC no improvement or worse.
- Improvement only from empty-GT cases.

Next:

- Pass tiny -> fold0 very-short.
- Pass very-short -> fold0 short.
- Pass short -> optionally fold0 longer.
- Any fail -> stop candidate, write decision, do not auto-expand.

### Stage 5: `evaluation_and_decision_gate`

Goal:

- Produce a single decision: `promote`, `watch`, `postpone`, or `stop`.

Must report separately:

- `myops_edema` class_4
- `myops_scar` class_5

Required subsets:

- all-case, context only
- T2-present GT-positive edema
- complete-modality
- CenterB
- CenterC
- no-T2 empty-GT
- modality groups: `C0+LGE+T2`, `C0+LGE`, `LGE-only`
- center subsets when meaningful

Required metrics:

- Dice
- HD
- HD95
- component count
- remote FP
- small FP
- pred/GT volume ratio
- case-level failure flags

Required outputs:

- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_stability.csv`
- `centerC_failure_table.csv`
- `case_level_failure_flags.csv`
- `round7_decision_table.md`
- `round7_next_actions.md`

Promotion criteria:

- T2-present GT-positive edema or CenterC complete-case edema has clean positive signal.
- Dice and HD95 do not show severe trade-off.
- component count and remote FP do not worsen.
- no-T2 empty-GT does not gain edema FP.
- class_5 scar Dice/HD95 does not clearly regress.
- improvement is not from empty-GT artifact handling.
- no foreground mean or all-case aggregate is used as success criterion.
- no hard deletion, label change, evaluator change, or cache contamination.

Decision rules:

- `promote`: all promotion criteria pass; allow separate plan for longer fold0 or fold expansion.
- `watch`: small positive signal but one non-critical uncertainty remains; require targeted audit before longer train.
- `postpone`: mechanism may be useful but current implementation lacks clean signal.
- `stop`: any fail criterion triggers; do not train longer or submit.

## 3. Controlled Repo Integration Branch

This branch is locked until first-party modality-aware route has a clean fold0 signal.

Mechanism slots:

| slot | candidates | Round07 stance |
| --- | --- | --- |
| missing-modality routing/distillation | AdaMM, UniME, CoPeDiT, MoE, MMPL-Seg | watch/postpone; no full repo integration until first-party signal and teacher reliability improve |
| modality/intensity prior | I-MMSeg | watch; metadata only unless modality conditioning shows clean fold0 need |
| alignment | CAA-Seg, SSA | watch from Round5; no direct implementation in Round07 |
| anatomy prior | Cascaded FSN, PT-Net | watch; current anatomy attenuation stopped |
| boundary/HD | InverseForm, surface loss | watch; small auxiliary only after modality route stabilizes |
| pretrained backbone | BiomedParse, MedNeXt, nnU-Net Task114/M&Ms | watch; no weight download in Round07 |

External repo entry requirements before any training:

- license/compliance review
- pretrained data source review
- external data risk assessment under CARE rules
- input-output shape compatibility
- label mapping compatibility
- one-case smoke
- fold0 smoke with isolated cache
- no external supervised scar/edema training data
- no validation pseudo-label supervised training

Do not clone/train all repos. Pick at most one mechanism-slot candidate only after first-party fold0 evidence shows which slot is actually needed.

## 4. Resource Stance

User token/GPU resources are assumed sufficient for goal-mode, but execution must be staged, gated, and evidence-driven.

Allowed in one goal-mode run if gates pass:

- implementation
- import/unit tests
- one-batch forward
- gradient smoke
- tiny-overfit
- fold0 very-short train
- fold0 short train
- evaluation and decision table
- fold0 longer train only after clean fold0 short gate

Still forbidden without separate authorization:

- fold1-4
- 5-fold
- validation zip
- upload
- external repo portfolio training
- large pretrained weight download
- external data training
- validation pseudo-label supervised training

Resource abundance does not permit skipping gates.

## 5. Required Output File Inventory

Minimum required files under:

```text
results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/
```

Required:

- `round7_goal_execution_readme.md`
- `train_config_modality_presence.yaml`
- `train_config_uncertainty_weighted.yaml`
- `train_commands.txt`
- `unit_gradient_smoke.csv`
- `tiny_overfit_metrics.csv`
- `fold0_short_train_metrics.csv`
- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_stability.csv`
- `centerC_failure_table.csv`
- `case_level_failure_flags.csv`
- `round7_decision_table.md`
- `round7_next_actions.md`

Optional:

```text
results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/failure_overlays/
```

Overlay priority:

- CenterC high-HD95 edema failures.
- T2-present GT-positive cases with Dice/HD95 trade-off.
- no-T2 empty-GT cases with any edema FP.
- scar guardrail regression cases.

## 6. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round07 goal-mode controller：

`docs/plans/laneA_round07_next_modality_presence_uncertainty_supervision_execution.md`

目标是尽可能推进 first-party `explicit modality presence conditioning + uncertainty-weighted no-T2 edema supervision`，但必须 staged, gated, and evidence-driven。不要重新做大范围 survey，不要继续 Round2/4/6 已停止的 postprocess、Focal Tversky-only 或 anatomy attenuation 路线。

所有输出写入：

`results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/`

必须先执行 `round7_setup_and_reproducibility_gate`：复核 Round6 outputs、fold0 split、nnU-Net501 baseline、label semantics、modality/center metadata、evaluation scripts、cache isolation 和 output roots。先写 `round7_goal_execution_readme.md`、`train_config_modality_presence.yaml`、`train_config_uncertainty_weighted.yaml`、`train_commands.txt`。

实现顺序：
1. 首选 `input_level_modality_presence_channels`：为每个 case 追加 `C0_present`、`LGE_present`、`T2_present` 常数通道或等效 first-party conditioning。
2. 只在 M1 wiring clean 后考虑轻量 `FiLM-like` conditioning；不要实现 AdaMM/UniME/CoPeDiT/MoE/I-MMSeg 完整 repo。
3. 实现 `uncertainty_weighted_low_negative` 作为 primary no-T2 edema policy：no-T2 empty-GT 不得作为 class_4 edema 强负样本；建议初始 no-T2 class_4 negative weight 为 `0.05`，并完整记录。
4. 可比较 `modality_conditioned_uncertainty_weighting`；teacher/confidence policy 只能作为 diagnostic，不能使用 validation pseudo-label supervised training，也不能依赖不可靠 complete-case teacher。

训练推进必须按 gate：
- import/unit test；
- one-batch forward；
- gradient smoke；
- tiny-overfit；
- fold0 very-short train；
- fold0 short train；
- 只有 fold0 short train clean pass 后，才允许 fold0 longer train。
任一 gate fail 必须停止当前候选并记录原因。禁止直接跳到 full 5-fold。禁止 fold1-4，除非本计划定义的 fold0 gates 全部通过且用户另行授权。禁止 validation zip、upload、下载大权重、拉大型外部 repo、external data training、validation pseudo-label supervised training、hard deletion、label/evaluator/fold silent change。

必须输出：
- `unit_gradient_smoke.csv`
- `tiny_overfit_metrics.csv`
- `fold0_short_train_metrics.csv`
- `baseline_vs_candidate_by_subset.csv`
- `no_t2_empty_gt_stability.csv`
- `centerC_failure_table.csv`
- `case_level_failure_flags.csv`
- `round7_decision_table.md`
- `round7_next_actions.md`

评估必须分别报告 `myops_edema` class_4 和 `myops_scar` class_5。必须报告 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、modality group、center subsets。Dice、HD、HD95、component count、remote FP、small FP、pred/GT volume ratio、case-level flags 必须同时报告。不要用 foreground mean 或 all-case aggregate 判定成功。

通过标准：
- T2-present GT-positive edema 或 CenterC complete-case edema 至少有 clean positive signal；
- Dice 和 HD95 不能严重一好一坏；
- remote FP/component count 不恶化；
- no-T2 empty-GT 不新增 edema FP；
- class_5 scar Dice/HD95 不明显回退；
- 不能靠 empty-GT artifact 获益；
- 不能通过 hard deletion 制造表面改善。

完成后更新 active execution record，并在 `round7_decision_table.md` 给出 `promote`、`watch`、`postpone` 或 `stop`。如果没有 clean fold0 signal，不得进入 longer train、fold1-4 或 submission。
```

## 7. Active Execution Record

Execution status: Round07 stopped before fold0 training after AMP-safe loss repair and renewed tiny gate.

Execution date: 2026-05-21.

Implemented first-party files:

- `src/care_myocardium/nnunet/laneA_round7_trainer.py`
- `scripts/training/run_laneA_round7_nnunet_train.py`
- `scripts/diagnostics/laneA_round7_modality_uncertainty.py`
- `scripts/diagnostics/laneA_round7_fold0_eval.py`
- `jobs/nnUNet/laneA_round7_fold0_very_short_train.sh`

Generated output root:

```text
results/diagnostics/phase0_phase1/laneA_myops/round7_modality_uncertainty/
```

Executed:

- Setup/reproducibility gate.
- First-party modality presence channel wiring.
- Class_4 uncertainty-weighted no-T2 edema auxiliary loss wiring.
- Unit/gradient smoke on selected fold0 cases.
- Tiny-overfit smoke on selected fold0 cases.
- Tiny-level policy sensitivity screen.
- Validation/export channel-injection helper smoke.
- Submitted one bounded fold0 very-short Slurm job:
  - job id: `51754384`
  - requested partition: `a100-gpu` fallback because `htzhulab` was occupied by long-running jobs
  - scope: fold0 very-short only, 3 epochs, 5 train iterations/epoch, 2 validation iterations/epoch
  - candidate: `U2_modality_conditioned_balanced`, `aux=1.0`, `no_t2_negative_weight=0.25`

Not executed:

- no completed nnU-Net fold0 train/evaluation yet; job `51754384` is pending;
- no fold1-4 or 5-fold;
- no validation zip;
- no upload;
- no pretrained weight download;
- no external repo clone/build/train;
- no external data training;
- no validation pseudo-label supervised training.

Selected smoke cases:

- `Case1002`: CenterA, LGE-only, no-T2 empty-GT edema.
- `Case2031`: CenterB, complete C0+LGE+T2, edema GT-positive.
- `Case3023`: CenterC, complete C0+LGE+T2, edema GT-positive.
- `Case5005`: CenterE, C0+LGE, no-T2 empty-GT edema.

Stage results:

| stage | status | evidence | next action |
| --- | --- | --- | --- |
| setup/reproducibility | pass | 11/11 checks passed; fold0 baseline, Round6 outputs, metadata, labels, and current 3-channel Dataset501 config found. | Continue. |
| modality presence conditioning | pass | Input-level constant modality channels expand data from 3 to 6 channels: `LGE,T2,C0,C0_present,LGE_present,T2_present`. | Keep first-party M1 wiring. |
| uncertainty-weighted no-T2 supervision | pass wiring | Class_4 and class_5 gradients are finite; no hard no-T2 negative is used. | Continue only through tiny gates. |
| default M1+U1 tiny gate | fail/watch | `aux=0.20`, `no_t2=0.05` reduced loss but CenterC edema tiny Dice was only `0.0412`, below the positive-edema signal gate. | Do not train default M1+U1. |
| policy sensitivity | watch | `U2_modality_conditioned_balanced` with `aux=1.0`, `no_t2=0.25` passed tiny policy screen: min T2-positive edema Dice `0.3579`, mean `0.3771`, no no-T2 edema FP voxels. | Reconfigure to U2 and rerun formal selected-policy gate before any fold0 train. |
| selected U2 tiny gate | watch/pass tiny only | `U2_modality_conditioned_balanced` passed selected-policy tiny-overfit: CenterB edema Dice `0.3579`, CenterC edema Dice `0.3962`, no no-T2 edema FP. | Do not start fold0 train until Round7 validation/export channel injection is smoke-tested. |
| validation/export channel smoke | pass | One preprocessed case was expanded from 3 to 6 channels and forwarded through a tiny test net; Round7 trainer now overrides validation export to inject modality-presence channels before prediction. | Fold0 very-short job is allowed. |
| fold0 very-short Slurm job | pending | Job `51754384` submitted; latest observed state `PD (Priority)`, start time `Unknown`, submit time `2026-05-21T14:26:05`, latest check `2026-05-21T14:39:48-04:00`. No log or predictions exist yet. | Wait for job completion, then run/verify `laneA_round7_fold0_eval.py`. |

Current decision:

```text
watch_fold0_very_short_submitted_pending
```

Interpretation:

- Round7 successfully established the first-party modality-presence and uncertainty-supervision substrate.
- The initial low-negative U1 setting is too weak for CenterC edema in tiny-overfit and should not enter fold0 training.
- A U2-style balanced policy is the best current next candidate, but it must be treated as `watch`, not `promote`, because this is still tiny-level evidence only.
- The selected U2 tiny gate has passed, and validation/export channel injection has a helper-level smoke pass. One bounded fold0 very-short job has been submitted and is pending scheduler priority. Do not submit another candidate while job `51754384` is pending/running.

### 2026-05-22 update after htzhulab rerun

The user moved the blocked A100 attempt to `htzhulab`; the observed job was:

- job id: `51989996`
- partition/node: `htzhulab`, `g1807htzh01`
- status from `sacct`: `FAILED`
- elapsed: `00:01:14`
- exit code: `1:0`
- log: `logs/LaneA_R7_F0VS_51989996_20260522_075457.log`

Failure cause:

- The first training batch failed before producing validation predictions because `torch.nn.functional.binary_cross_entropy` was called under AMP/autocast in the class_4 edema auxiliary loss.
- This was an implementation bug in the Round7 auxiliary loss wrapper, not a valid fold0 model-quality result.

Repair applied:

- `src/care_myocardium/nnunet/laneA_round7_trainer.py` now uses `binary_cross_entropy_with_logits` for the class_4 edema auxiliary BCE term.
- Syntax checks passed for the Round7 trainer, training wrapper, diagnostic script, and fold0 evaluator.
- The diagnostic script now overwrites `selected_policy_tiny_overfit_metrics.csv` with an explicit `not_run_no_policy_passed_tiny_screen` row when no candidate passes, so stale selected-policy evidence cannot authorize training.

Renewed Round7 diagnostic result after the repair:

| stage | status | evidence | decision |
| --- | --- | --- | --- |
| setup/reproducibility | pass | 11/11 setup checks passed. | continue |
| modality presence conditioning | pass | input channels `3 -> 6`; class_4/class_5 gradients finite. | keep first-party M1 wiring |
| uncertainty-weighted no-T2 supervision | pass wiring only | no-T2 class_4 negative weight remains non-hard; no NaN/Inf. | continue only through gates |
| default U1 tiny gate | fail | loss decreased, but CenterB and CenterC T2-positive edema Dice were `0.0000`. | do not train U1 |
| U2 policy sensitivity | fail | T2-positive edema Dice improved, but no-T2 empty-GT edema FP appeared: `8` voxels for U2 balanced and `10` voxels for U2 conservative. | do not train U2 |
| fold0 very-short train | not run after repair | no policy candidate passed the renewed tiny gate; no Round7 candidate validation predictions exist. | stop before fold0 |

Current decision after the repaired diagnostic:

```text
fail_stop_before_fold0_training
```

Interpretation after the repaired diagnostic:

- Round7 successfully proved the first-party modality-presence channel wiring and AMP-safe loss wiring can run through setup/gradient/network-init smoke.
- The originally selected `U2_modality_conditioned_balanced` policy is no longer eligible for fold0 training after the AMP-safe loss repair because it introduces no-T2 empty-GT edema false positives during tiny policy screening.
- No Round7 fold0 candidate metrics should be interpreted as model performance, because the only fold0 job failed before completing a training step and no validation predictions were exported.
- Do not submit another Round7 fold0 train under the current U1/U2 settings. The next step is a revised uncertainty policy or a stricter no-T2 FP guard, followed by the same setup/gradient/tiny gate before any fold0 job.
