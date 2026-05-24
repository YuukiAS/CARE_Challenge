# Lane A Round06 Next Anatomy Soft Prior And Missing-Modality Route Execution

Plan metadata:
- Type: next execution controller
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round06 anatomy soft-prior trainable smoke and missing-modality route audit
- Status: ready for goal-mode execution
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round05_active_controlled_mechanism_integration_execution.md`
- Function: define the next bounded Lane A execution stage: anatomy-guided soft-prior smoke plus missing-modality routing/supervision audit
- Do not: run fold1-4, run 5-fold, create validation zip, upload, download large weights, clone/build/train large external repos, use external data training, use validation pseudo-label supervised training, hard-delete edema by ROI, or use foreground/all-case aggregate as the success criterion
- Rule exception: `docs/plans/care_myocardium_plan_registry_rules.md` originally defines Round06 as fold expansion and submission strategy. The user explicitly selected `Round06 override`; this file uses Round06 for a mechanism-execution controller and is not a fold-expansion/submission plan.

## 1. Current Lane A Evidence Chain

Lane A has already passed the point where small postprocess or single-loss tweaks are credible as the main route.

### Round2: edema postprocess route failed

Round2 tested inference-side edema component/ROI cleanup on existing nnU-Net501 fold0 predictions.

Key evidence:

- Removing 1-voxel edema islands reduced component count from `3.3182` to `1.7273`.
- GT-positive edema Dice decreased from `0.3944` to `0.3935`.
- GT-positive edema HD95 worsened from `20.0115` to `20.0234`.
- CenterC complete-case edema remained weak.

Decision preserved for Round06:

- Stop small-component deletion as a mainline.
- Stop ROI thresholding and inference-side suppression as a mainline.
- Do not call empty-GT artifact cleanup a valid edema improvement.

### Round3: trainable wiring smoke passed, not performance

Round3 proved that class_4 edema-specific loss wiring and tiny-overfit smoke can run:

- `edema_focal_tversky` passed gradient smoke.
- `no_t2_edema_loss_downweighting` passed training-strategy smoke.
- tiny-overfit gate passed and allowed one bounded fold0 short train.

Decision preserved for Round06:

- Round3 was a wiring gate, not a model-quality gate.
- It does not justify continuing Focal Tversky as the mainline after Round4 failed.

### Round4: focal Tversky + no-T2 downweighting failed real fold0 short train

Round4 ran:

```text
edema_focal_tversky + no_t2_edema_loss_downweighting
```

Scope:

- fold0 only.
- 20 bounded epochs.
- 44/44 fold0 validation predictions exported.

Final gate:

```text
fail_stop_no_longer_train
```

Key failure evidence:

| subset | edema Dice delta | edema HD95 improvement delta | edema component improvement delta | edema remote FP improvement delta | scar Dice delta | scar HD95 improvement delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all_case | -0.1252 | -2.1090 | -1.3864 | -2.0000 | -0.0037 | -1.3937 |
| T2-present GT-positive | 0.0094 | -1.1069 | 1.3750 | -0.3125 | -0.0149 | -1.4646 |
| CenterC | 0.0068 | 0.5097 | 2.2222 | -0.3333 | -0.0161 | -0.9040 |
| no-T2 empty-GT | NA | 0.0000 | -2.9643 | -2.9643 | 0.0027 | -1.3501 |

Interpretation:

- T2-present GT-positive edema Dice improved only slightly, while HD95 and remote FP worsened.
- CenterC edema showed only a small signal and still worsened remote FP.
- No-T2 empty-GT cases developed new edema false positives.
- All-case edema Dice fell sharply.
- Scar class_5 HD95 guardrail was not clean.

Decision preserved for Round06:

- Do not extend this candidate to longer fold0 training.
- Do not train folds 1-4.
- Do not submit it to validation.
- Do not keep tuning Focal Tversky as the main route.

### Round5: mechanism audit selected anatomy soft prior

Round5 ran CARE-only mechanism audits:

- `alignment_feasibility_audit`
- `anatomy_soft_prior_feasibility`
- `boundary_distance_failure_audit`

Decision table:

| route | status | evidence | next action |
| --- | --- | --- | --- |
| CAA-Seg/SSA-style alignment audit | `watch` | `geometry_mismatch=0`; weak body-bbox/HD95 correlation; CenterC still has 6 high-HD95 cases | Small visual/metadata review only; current proxies are not enough for SSA as the first trainable route. |
| anatomy-guided cascade / soft prior | `go` | Round4 has 8 no-T2 empty-GT edema FP cases; anatomy support explains important outliers | Prototype soft anatomy support/penalty with no hard deletion and explicit no-T2 FP guard. |
| conservative boundary/distance objective | `watch` | Round4 has 13 remote-or-empty-FP modes versus 3 boundary-overreach modes | Boundary loss can be a small auxiliary only after anatomy/remote-FP guard. |

Round06 decision:

- Main trainable route: bounded anatomy-guided soft prior.
- Auxiliary route: missing-modality routing and supervision audit.
- Watch routes: SSA/alignment and boundary/surface objective.
- Explicitly stop: hard ROI deletion, small-component cleanup, Focal Tversky-only retuning.

## 2. Round06 Goal-Mode Boundary

Round06 is a bounded execution controller for the next goal-mode run. It should generate evidence, not a leaderboard package.

Allowed next goal actions:

- Add minimal first-party anatomy soft-prior implementation.
- Run tiny subset or bounded fold0 short train for one selected anatomy candidate.
- Evaluate against existing nnU-Net501 fold0 baseline on identical fold0 validation cases.
- Generate case-level metrics, subgroup tables, failure flags, and optional overlays.
- Execute missing-modality audit and complete-case teacher feasibility audit.
- Keep all outputs isolated under:

```text
results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/
```

Explicitly disallowed next goal actions:

- fold1-4 training.
- full 5-fold training.
- validation zip creation.
- validation upload.
- external data training.
- validation pseudo-label supervised training.
- large pretrained weight download.
- large external repo clone/build/train.
- hard anatomy deletion or hard ROI filtering.
- modifying label semantics, evaluator semantics, fold splits, or baseline caches.

## 3. Main Module A: `anatomy_guided_soft_prior_bounded_smoke`

Purpose: move Round5 anatomy-guided soft prior from audit to a trainable smoke while preserving nnU-Net501 comparability and scar class_5 guardrails.

### Candidate A1: `distance_map_input_channel`

Mechanism:

- Add one or more soft anatomy channels to the model input:
  - myocardium distance map,
  - combined anatomy distance map,
  - dilated myocardium support map,
  - optional signed/normalized support map.
- The network can learn to use anatomy context, but no voxel is deleted by rule.

Recommended first priority: `yes`.

Implementation complexity: low to medium.

Preprocessing requirement:

- Generate distance/support maps from CARE compact labels for training.
- For validation/inference smoke, use a consistent anatomy source:
  - preferred smoke source: existing model/GT-derived diagnostic path only if explicitly labelled as oracle/diagnostic;
  - trainable candidate source: first-party anatomy prediction/probability if available;
  - if no non-oracle anatomy prediction exists, run this first as a diagnostic upper-bound smoke and mark it as not submission-eligible.

Class_5 scar impact:

- Low direct risk if class_5 loss remains unchanged.
- Must still report scar Dice/HD/HD95 because added channels can shift shared features.

Anatomy uncertainty handling:

- Normalize distances and clip to a maximum physical radius.
- Use soft continuous maps, not binary deletion masks.
- For uncertain anatomy, keep the original image channels dominant and use anatomy as context only.

Fail-fast:

- Any evidence that edema GT-positive voxels are systematically suppressed by distance/support channels.
- Any scar class_5 HD95 guardrail regression.

### Candidate A2: `edema_anatomy_distance_weighted_loss`

Mechanism:

- Add a class_4 edema auxiliary loss with spatial weighting based on anatomy distance.
- Penalize confident edema probability far from myocardium/anatomy more than near anatomy.
- Keep baseline multiclass Dice/CE unchanged.

Recommended first priority: `yes`, but only with conservative weight.

Implementation complexity: medium.

Preprocessing requirement:

- Distance map can be computed online from labels for training.
- For prediction-time evaluation, no hard mask is applied.

Class_5 scar impact:

- Medium risk because shared logits/backbone may shift.
- Class_5 loss must remain unchanged, and class_5 metrics are mandatory guardrails.

Anatomy uncertainty handling:

- Distance weighting must have lower/upper bounds.
- Weights must never zero-out edema GT-positive voxels.
- Use smooth decay or clipped linear/logistic weight, not hard threshold.

Fail-fast:

- T2-present GT-positive edema Dice drops while remote FP improves.
- CenterC edema loses lesion volume.
- Any improvement depends on empty-GT cases.

### Candidate A3: `remote_edema_probability_soft_penalty`

Mechanism:

- Add a small penalty for edema probability outside soft/dilated anatomy support.
- This targets Round4 remote FP and no-T2 empty-GT FP.

Recommended first priority: `watch / optional add-on`.

Implementation complexity: low to medium.

Preprocessing requirement:

- Same support map as A1/A2.
- No additional external dependency.

Class_5 scar impact:

- Medium risk if penalty competes with shared pathology representation.
- Keep weight small and report scar guardrail.

Anatomy uncertainty handling:

- Use a wide physical support radius.
- Do not apply penalty inside any GT edema region during supervised training.
- Do not convert penalty into inference deletion.

Fail-fast:

- Any GT-positive edema suppression.
- HD95 improves only via volume collapse.

### Candidate A4: `anatomy_probability_attention_guide`

Mechanism:

- Use anatomy probability map as an auxiliary feature or attention-like guide in edema route.

Recommended first priority: `postpone/watch`.

Implementation complexity: medium to high.

Preprocessing requirement:

- Requires reliable anatomy probability source.
- If anatomy probability comes from a separate model, output provenance and cache isolation must be recorded.

Class_5 scar impact:

- Medium to high; architecture coupling can affect scar.

Anatomy uncertainty handling:

- Probability map must be soft.
- Attention cannot hard gate edema logits to zero.

Fail-fast:

- Any hidden hard gate behavior.
- Any need to rewrite trainer/dataloader broadly in Round06.

### Round06 anatomy candidate selection

The next goal should not run all candidates. Use this selection order:

1. Primary: `distance_map_input_channel`.
2. Optional if minimal: `remote_edema_probability_soft_penalty`.
3. Hold unless primary wiring is clean: `edema_anatomy_distance_weighted_loss`.
4. Postpone: `anatomy_probability_attention_guide`.

Default training budget:

- tiny subset smoke first if implementation is not already proven;
- then bounded fold0 short train only if tiny smoke is stable;
- walltime target <= 8h;
- use isolated experiment name:

```text
laneA_anatomy_soft_prior_fold0_short
```

No candidate is submission-eligible from Round06 alone.

## 4. Main Module B: `missing_modality_routing_and_supervision_audit`

Purpose: address the structural missing-modality problem without prematurely integrating AdaMM, UniME, CoPeDiT, I-MMSeg, or a large missing-modality framework.

### Task B1: `modality_center_supervision_audit`

Required reporting by modality group:

- `C0+LGE+T2`
- `C0+LGE`
- `LGE-only`

Required reporting by center when possible:

- CenterA/B/C/E/F/G/H.

Metrics and fields:

- case count.
- edema GT prevalence.
- scar GT prevalence.
- edema prediction FP count.
- scar prediction FP count.
- edema Dice/HD/HD95 on GT-positive cases.
- scar Dice/HD/HD95 on GT-positive cases.
- edema component count.
- edema remote FP.
- pred/GT volume ratio.
- no-T2 empty-GT false positive rate.

Purpose:

- Determine whether current failures are mostly modality-driven, center-driven, or both.
- Prevent no-T2 centers from being treated as reliable edema-negative sources.

Output:

- `missing_modality_supervision_audit.csv`
- `missing_modality_supervision_audit.md`

### Task B2: `no_t2_supervision_policy_audit`

Compare these policy options without doing large training:

| policy | description | expected risk | Round06 default |
| --- | --- | --- | --- |
| `hard_negative` | treat no-T2 empty-GT as full edema-negative supervision | high; center shortcut and T2-missing shortcut | reject unless audit proves no FP and no shortcut |
| `masking` | remove class_4 edema auxiliary loss on no-T2 cases | medium; may reduce regularization | watch |
| `downweighting` | keep low class_4 weight on no-T2 cases | medium; Round4 still created FP | watch only, not enough alone |
| `uncertainty_weighted` | weight edema supervision by modality/anatomy reliability | lower if implemented conservatively | preferred future route |

Decision rule:

- No-T2 empty-GT cannot be used as strong negative evidence.
- Any policy that improves only empty-GT artifacts is diagnostic, not primary.

### Task B3: `explicit_modality_mask_feasibility`

Evaluate whether the next first-party model should include:

- modality-presence input channels;
- metadata vector `[lge_present, t2_present, c0_present]`;
- FiLM-like conditioning;
- modality-group-specific normalization/adapters.

Audit questions:

- Are current edema/FP failures stratified by missing T2?
- Does center explain more variance than modality group?
- Would modality mask reduce ambiguity from zero-filled missing channels?
- Can the mechanism be added without changing label/evaluator semantics?

Gate:

- `go` if no-T2 false positives, center-confounded edema supervision, or zero-filled channel ambiguity remain important after anatomy soft-prior smoke.
- `watch` if anatomy prior resolves most no-T2 instability.
- `postpone` if implementation would require broad trainer/backbone rewrite before evidence.

### Task B4: `complete_case_teacher_feasibility`

Purpose: decide whether CARE-only complete cases can support future AdaMM-style distillation.

Audit scope:

- complete C0+LGE+T2 cases only.
- fold0 complete train/val counts.
- CenterB vs CenterC split.
- teacher quality proxy from nnU-Net501 / any anatomy prior candidate.
- edema GT-positive stability.

Required outputs:

- `complete_case_teacher_feasibility.csv`
- `complete_case_teacher_feasibility.md`

Decision questions:

- Are complete cases numerous enough for a teacher?
- Is teacher edema stable on CenterC?
- Does teacher improve HD95/remote FP, not only Dice?
- Would teacher encode center style instead of pathology?

Gate:

- `go` for future CARE-only distillation only if complete-case teacher has clean edema Dice/HD95/remote-FP behavior, especially CenterC.
- `watch` if teacher is useful only for anatomy or scar.
- `stop/postpone` if teacher repeats Round4 failure or depends on external data.

## 5. Prep Module: `controlled_repo_integration_readiness`

Round06 does not clone/train external repos. It only classifies future candidates by mechanism slot and defines entry requirements.

| mechanism slot | candidates | use in Round06 |
| --- | --- | --- |
| alignment | CAA-Seg / SSA | watch; only metadata/visual feasibility after current alignment proxy was weak |
| anatomy-guided prior | Cascaded FSN / PT-Net | concept source for soft prior; do not hard-code external repo |
| boundary / HD | InverseForm / surface loss / differentiable HD | watch; small auxiliary only after anatomy guard |
| missing-modality / intensity prior | AdaMM / UniME / CoPeDiT / I-MMSeg / MoE | audit-only; no full implementation |
| pretrained backbone | BiomedParse / MedNeXt / nnU-Net Task114 / M&Ms | metadata-only readiness; no large download |

Any future external repo/weight must pass all gates before formal training:

1. license and allowed-use check.
2. pretrained data source and challenge-compliance record.
3. input/output shape compatibility with Dataset501.
4. compact/raw label mapping compatibility.
5. no external supervised scar/edema data.
6. one-case smoke.
7. fold0 smoke with isolated cache.
8. no validation pseudo-label supervised pathology training.

If any candidate requires external data training, generated external training samples, validation pseudo-label supervised learning, or unclear license/weights provenance, mark it `postpone/reject`.

## 6. Required Round06 Output Files

All files must be written under:

```text
results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/
```

Required:

- `anatomy_soft_prior_train_config.yaml`
- `anatomy_soft_prior_train_command.txt`
- `anatomy_soft_prior_metrics.csv`
- `anatomy_soft_prior_summary.md`
- `baseline_vs_anatomy_prior_by_subset.csv`
- `case_level_anatomy_failure_flags.csv`
- `missing_modality_supervision_audit.csv`
- `missing_modality_supervision_audit.md`
- `complete_case_teacher_feasibility.csv`
- `complete_case_teacher_feasibility.md`
- `round6_laneA_decision_table.md`
- `round6_next_goal_prompt.md`

Optional:

```text
results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/failure_overlays/
```

Overlay rules:

- Generate only if existing dependencies are enough.
- Prioritize CenterC high-HD95 cases and no-T2 empty-GT FP cases.
- Do not introduce long plotting or visualization dependencies.

## 7. Required Metrics And Subsets

Do not use foreground mean as a success criterion.

Report `myops_edema` class_4:

- Dice.
- HD.
- HD95.
- component count.
- small FP.
- remote FP.
- pred/GT volume ratio.
- no-T2 empty-GT FP count.
- anatomy support / distance statistics when relevant.

Report `myops_scar` class_5 as guardrail:

- Dice.
- HD.
- HD95.
- component count when available.
- pred/GT volume ratio when available.

Required subsets:

- all-case, for context only.
- T2-present.
- T2-present GT-positive edema.
- complete-modality.
- CenterC complete-case edema.
- no-T2 empty-GT edema stability.
- modality group: `C0+LGE+T2`, `C0+LGE`, `LGE-only`.
- center when sample count is meaningful.

Any all-case improvement must be decomposed into the above subsets before being considered real.

## 8. Pass Criteria

Anatomy-guided soft prior can be promoted only if all conditions hold:

- no-T2 empty-GT edema FP decreases or does not increase.
- T2-present GT-positive edema Dice or HD95 improves, and the other does not worsen.
- CenterC complete-case edema has a clean positive signal.
- remote FP does not worsen.
- component count does not worsen.
- class_5 scar Dice does not clearly regress.
- class_5 scar HD95 does not clearly regress.
- improvement is not primarily from empty-GT artifact handling.
- no hard deletion or hard ROI filtering is used.
- label/evaluator/fold/cache semantics remain unchanged and recorded.

Missing-modality route can proceed only if at least one audit shows clear signal:

- modality mask feasibility is positive;
- uncertainty-weighted no-T2 policy is safer than hard negative/downweighting;
- complete-case teacher is reliable enough for future CARE-only distillation;
- center/modality confounding is measurable and actionable.

## 9. Fail / Stop Criteria

Fail anatomy soft-prior smoke if:

- anatomy prior suppresses true GT-positive edema.
- Dice improves but HD95/component/remote FP worsens.
- no-T2 edema FP continues to increase.
- CenterC complete-case edema worsens or has no clean signal.
- class_5 scar Dice/HD95 guardrail worsens.
- result requires silent label/evaluator/preprocessing change.
- result only looks positive in all-case aggregate.
- result depends on hard anatomy deletion.

Reject or postpone missing-modality route if:

- it requires external data training.
- it requires validation pseudo-label supervised pathology training.
- it requires large external weights before license/provenance check.
- complete-case teacher is unstable on CenterC edema.
- no-T2 policy treats empty-GT as strong negative without evidence.

Do not expand to folds 1-4 from Round06 alone. Fold expansion requires a separate compliant plan after a clean fold0 gate.

## 10. Suggested Goal-Mode Implementation Steps

The next goal-mode execution should follow this order:

1. Create output root:
   - `results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/`
2. Write `anatomy_soft_prior_train_config.yaml` before running any smoke:
   - candidate name.
   - input channels.
   - distance/support map source.
   - whether the anatomy source is oracle/diagnostic or prediction-based.
   - loss weights.
   - no-T2 policy.
   - fold.
   - seed.
   - output directories.
   - runtime cap.
3. Implement minimal first-party `distance_map_input_channel` path.
4. Run tiny smoke if wiring is new.
5. Run one bounded fold0 short train only if tiny smoke passes.
6. Evaluate against existing nnU-Net501 fold0 baseline.
7. Generate required subset and case-level metrics.
8. Run missing-modality supervision audit.
9. Run complete-case teacher feasibility audit.
10. Write `round6_laneA_decision_table.md`.
11. Write `round6_next_goal_prompt.md`.

If any fail-fast criterion triggers, stop and record `fail_stop_no_expand`.

## 11. Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请执行 Lane A Round06 bounded anatomy-guided soft-prior smoke + missing-modality audit。使用计划文件：

`docs/plans/laneA_round06_next_anatomy_soft_prior_and_missing_modality_route_execution.md`

本轮只允许实现最小 first-party anatomy soft prior candidate，优先 `distance_map_input_channel`，可选小权重 `remote_edema_probability_soft_penalty`。同时执行 modality/center supervision audit、no-T2 supervision policy audit、explicit modality mask feasibility、complete-case teacher feasibility。

所有输出写入：

`results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/`

必须先写 `anatomy_soft_prior_train_config.yaml` 和 `anatomy_soft_prior_train_command.txt`，记录实际候选、distance/support map 来源、loss weights、no-T2 policy、fold、seed、输出目录和运行边界。

允许 tiny subset smoke 或 bounded fold0 short train。禁止 fold1-4、禁止 5-fold、禁止 validation zip、禁止上传、禁止下载大权重、禁止拉大型外部 repo、禁止 external data training、禁止 validation pseudo-label supervised training、禁止 hard anatomy deletion、禁止改 label/evaluator/fold semantics。

必须同时报告 `myops_edema` 和 `myops_scar`，并按 T2-present GT-positive、complete-modality、CenterC、no-T2 empty-GT、modality group、center 分组。Dice、HD、HD95、component count、remote FP、volume ratio 必须同时报告。任何 Dice gain 伴随 HD95/component/remote FP 回退、任何来自 empty-GT artifact 的 improvement、任何 scar guardrail 明显回退，都必须 fail。

完成后更新 `round6_laneA_decision_table.md`，说明是否建议进入 longer fold0、是否建议 missing-modality controlled integration，以及哪些路线 stop/watch/go。
```

## 12. Active Execution Record

Execution status: completed first Round06 bounded diagnostic/audit pass.

Execution date: 2026-05-20.

Output root:

- `results/diagnostics/care_myocardium/laneA_myops/round06_anatomy_missing_modality/`

Implemented first-party diagnostic script:

- `scripts/diagnostics/laneA_round06_anatomy_missing_modality.py`

Executed tasks:

- Wrote `anatomy_soft_prior_train_config.yaml` and `anatomy_soft_prior_train_command.txt`.
- Ran a CARE-only anatomy soft-prior diagnostic using existing nnU-Net501 fold0 probabilities and GT-derived myocardium distance support as an oracle upper-bound analysis.
- Generated diagnostic candidate predictions under `predictions/anatomy_soft_prior_oracle_diagnostic/`.
- Evaluated baseline versus candidate on fold0 validation cases with edema/scar metrics and required subsets.
- Ran missing-modality supervision audit.
- Ran complete-case teacher feasibility audit.
- Generated small failure overlay PNGs for flagged cases.

Explicitly not executed:

- no training;
- no Slurm submission;
- no fold1-4 or 5-fold expansion;
- no validation zip;
- no upload;
- no large pretrained weight download;
- no external repo clone/build/train;
- no external data training;
- no validation pseudo-label supervised training;
- no hard ROI deletion;
- no label/evaluator/fold semantics change.

Generated required files:

- `anatomy_soft_prior_train_config.yaml`
- `anatomy_soft_prior_train_command.txt`
- `anatomy_soft_prior_metrics.csv`
- `anatomy_soft_prior_summary.md`
- `baseline_vs_anatomy_prior_by_subset.csv`
- `case_level_anatomy_failure_flags.csv`
- `missing_modality_supervision_audit.csv`
- `missing_modality_supervision_audit.md`
- `complete_case_teacher_feasibility.csv`
- `complete_case_teacher_feasibility.md`
- `round6_laneA_decision_table.md`
- `round6_next_goal_prompt.md`

Key result:

- Overall decision: `fail_stop_no_expand` for the current anatomy soft-prior diagnostic configuration.
- Anatomy-guided soft prior route status: `stop` for the current GT-distance probability-attenuation configuration.
- Missing-modality routing/supervision route status: `go` for controlled first-party explicit modality mask / uncertainty-weighted no-T2 policy design.
- Controlled external repo integration status: `postpone`.

Subset signal from `anatomy_soft_prior_summary.md`:

| subset | delta edema Dice | delta edema HD95 improvement | delta component improvement | interpretation |
| --- | ---: | ---: | ---: | --- |
| all_case | -0.0008 | 0.0171 | -0.0227 | no clean improvement |
| t2_present_gt_positive | -0.0008 | 0.0469 | -0.0625 | HD95 tiny improvement but Dice/component fail |
| complete_modality | -0.0008 | 0.0469 | -0.0625 | same as T2-present complete cases |
| CenterC | 0.0002 | -0.0186 | -0.2222 | CenterC does not pass gate |
| no_t2_empty_gt | 0.0000 | 0.0000 | 0.0000 | stable but no benefit |

Case-level fail flags:

- `Case2031`: edema Dice dropped.
- `Case3004`: edema component count worsened.
- `Case3012`: edema component count worsened.
- `Case3034`: edema component count worsened.
- `Case3038`: edema component count worsened.

Round06 decision table:

| route | status | evidence | next action |
| --- | --- | --- | --- |
| anatomy_guided_soft_prior_bounded_smoke | stop | Dice/component/CenterC gates did not pass under the current soft-prior diagnostic configuration. | Do not train this configuration longer. |
| missing_modality_routing_and_supervision_audit | go | no-T2 hard-negative policy remains high risk; explicit modality mask / uncertainty-weighted policy is the cleanest next first-party route. | Plan a controlled modality-mask / uncertainty-weighted no-T2 smoke. |
| controlled_repo_integration_readiness | postpone | No external repo or weights were needed; first-party signal is not yet clean. | Keep AdaMM/UniME/I-MMSeg and similar methods as mechanism sources only. |

Important interpretation:

- The executed anatomy soft prior used GT myocardium as an oracle diagnostic support source, so it is not submission-eligible and must not be treated as a deployable model.
- Even this oracle-style soft attenuation did not produce a clean edema gate, so the current soft-prior configuration should stop rather than move to longer fold0 training.
- The strongest Round06 next signal is missing-modality supervision/routing, especially explicit modality presence conditioning and uncertainty-weighted no-T2 edema supervision.
