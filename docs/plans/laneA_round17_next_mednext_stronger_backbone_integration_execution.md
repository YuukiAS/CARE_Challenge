Plan metadata:
- Type: next/planned round execution
- Lane: Lane A, MyoPS scar/edema
- Round scope: Round17
- Status: next goal-mode controller
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: `docs/plans/laneA_round16_next_external_mechanism_integration_large_smoke_execution.md`
- Function: define a staged, gated MedNeXt / stronger-backbone CARE-native integration route after Round16 stopped all first-party feature/refiner candidates
- Do not: train in this planning pass; submit Slurm; create validation zip; upload; download weights; use external image/label data; expand fold1-4/5-fold; continue Round15/16 A/C/E/F by simply adding epochs

# Lane A Round17: MedNeXt / Stronger Backbone Integration Plan

## Path Normalization Note

本轮 prompt 中仍出现 legacy output root：

```text
results/diagnostics/phase0_phase1/laneA_myops/round17_mednext_backbone/
```

当前 repo 已完成诊断目录清理，新的 canonical root 是：

```text
results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/
```

Round17 goal-mode 必须使用新的 `care_myocardium` root，不应重新创建 `phase0_phase1` 目录。若旧脚本仍硬编码 legacy path，应在 Round17 setup gate 中修正到新 root，并记录 path normalization。

## Current Evidence Chain

Lane A 已经连续排除浅层小修路线：

| round | tested route | decision |
| --- | --- | --- |
| Round2 | edema inference postprocess: small components / ROI / suppression | `fail`: component count 可下降，但 GT-positive edema Dice/HD95 不 clean。停止小组件删除和 ROI 阈值主线。 |
| Round3 | loss wiring, gradient, tiny-overfit | engineering pass only，不代表性能。 |
| Round4 | `edema_focal_tversky + no_t2_edema_loss_downweighting` fold0 short | `fail`: remote FP、no-T2 FP、HD95 和 scar guardrail 不干净。停止 recall-heavy Focal Tversky 和 simple no-T2 downweighting。 |
| Round5 | mechanism audit | alignment / CAA-Seg-SSA 为 `watch`，boundary/distance 为 `watch`，anatomy soft prior 进入 bounded diagnostic。 |
| Round6 | anatomy soft attenuation, missing-modality audit | anatomy attenuation `fail`；no-T2 empty-GT 不能作为 class_4 强负样本；modality presence / uncertainty supervision 是信号。 |
| Round7 | 6-channel modality presence + scalar no-T2 weighting | pipeline 可行，但 U1/U2 tiny gate 不 clean。停止 scalar weighting 微调。 |
| Round8 | T2-present edema expert / separated supervision | tiny signal exists，但 scratch / near-scratch very-short fold0 全面崩；不能用 scratch 3-epoch 改结构模型硬比完整 nnU-Net501。 |
| Round9 | nnU-Net501 checkpoint transfer to 6-channel; whole-network fine-tune | checkpoint preserving 可行，但 whole-network fine-tune 只有极弱 edema signal，component/HD95/scar 不 clean。停止 whole-network fine-tune。 |
| Round10-Round14 | add-only refiner, bidirectional refiner, fallback salvage, intensity/anatomy features, component/voxel calibrator | baseline-preserving class_4-only substrate 可保持 scar/no-T2 安全，但不能产生 clean CenterC / T2-present edema improvement。 |
| Round15 | DeepResearch-guided first-party feature-head portfolio | A 有极弱 intensity signal 但 CenterC component safety fail；B/C fallback baseline；无 fold0 short promotion。 |
| Round16 | external mechanism large smoke + first-party A/C/E/F very-short | A/C/E target deltas = 0；F small MoE severe target regression；final gate `stop_no_promoted_candidate`。 |

Round16 后的 hard-case analysis 进一步说明：

- `Case3011` 和 `Case3040` 是 CenterC complete-modality T2-present GT-positive 关键失败点。baseline edema localization 已弱，residual/refiner/calibrator 容易在 T2 weak/ambiguous 区域产生 remote 或 edge activation。
- `Case2031` 有局部 Dice 正信号，但 fragmentation / HD95 仍不 clean。
- `Case3012` 的 component-safe fallback 能保护安全性，但也说明当前 refiner 不能提供有效 correction。
- scar guardrail 多数保持 unchanged，no-T2 empty-GT 多数 clean；这说明此前 edema-only refiner/calibrator 的安全 substrate 可行，但有效性不足。进入 backbone route 后，scar 不应只作为被动 guardrail，而应作为 co-primary non-regression / improvement metric。

## Strategic Decision

Round17 不再继续以下方向：

- 普通 refiner / calibrator / feature-head 小修。
- 给 Round15/16 A/C/E/F 直接加 epoch。
- fold1-4 / 5-fold 扩展。
- validation zip 或 upload。
- Focal Tversky、小组件后处理、hard ROI、anatomy attenuation、whole-network nnU-Net small tweak。
- 无合规检查的 external data / pretrained weight usage。

Round17 主线进入：

```text
MedNeXt / stronger backbone CARE-native integration
```

目标不是继续修补 nnU-Net501 输出，而是测试更强 3D segmentation backbone 是否能 **jointly improve MyoPS scar and edema**。MedNeXt / stronger backbone route aims to improve MyoPS scar and edema jointly, with edema as the hardest primary gate and scar as a co-primary non-regression/improvement metric. 其中 edema 仍是最难、最硬的 primary gate，尤其 CenterC / T2-present GT-positive edema；scar 是 co-primary non-regression / improvement metric，而不是只有“别坏掉”的附带检查。理想候选应至少保持 scar Dice/HD95 clean，并优先寻找 scar 同步改善或不退的 backbone 表征增益。

MedNeXt 是当前优先候选，因为 Round16 metadata/import/one-case smoke 中它是最干净的 stronger-backbone readiness candidate：`MIC-DKFZ/MedNeXt` repo 可达，Apache-2.0-like license detected，import 和 instantiate smoke 通过。预训练权重和训练数据来源仍必须单独合规审查；Round17 第一主线应优先做 code-only architecture route，只使用 CARE training data。

Round17 promotion interpretation:

- **Strong promote**: edema 在 T2-present GT-positive 或 CenterC 上 clean improvement，且 scar Dice/HD95 同步改善或保持完全 clean。
- **Promote with caution**: edema 有 clean improvement，scar 不退但没有明显改善。
- **Watch**: scar 有改善但 edema 没有 CenterC/T2-present signal；这是 backbone 表征信号，但不能作为 Lane A promoted candidate，因为 edema 仍是 Round17 最硬 primary gate。
- **Fail**: edema 有局部 Dice gain 但 HD95/component/remote FP 恶化，或 scar 明显回退。

## Main Route 1: `MedNeXt_v1_CARE_only_architecture_route`

目标：将 MedNeXt v1 architecture 接入 CARE Dataset501 fold0 pipeline，只使用 CARE 训练数据，不使用 external images/labels，不下载大权重。

Design constraints:

- Prefer reusing MedNeXt as a PyTorch module / block library instead of copying its whole nnU-Net v1 training pipeline.
- Align output classes with Dataset501 compact labels: `0 background`, `1 myocardium`, `2 LV`, `3 RV`, `4 edema`, `5 scar`.
- Report class_4 `myops_edema` and class_5 `myops_scar` as joint task outputs; edema is the hardest primary gate and scar is co-primary non-regression / improvement. Never use foreground_mean as success criterion.
- Use the same fold0 validation cases as nnU-Net501 local reference.
- Do not pollute `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` baseline outputs/cache.
- First implementation should be small and tractable: MedNeXt-S or equivalent, kernel size 3, CARE-compatible patch shape, deep supervision explicitly documented on/off.

Minimal candidates:

| candidate | purpose | initial stance |
| --- | --- | --- |
| `R17_A_mednext_s_kernel3_standard_dicece_fold0_vs` | Small MedNeXt CARE-only architecture with standard Dice/CE | first priority |
| `R17_B_mednext_b_kernel3_standard_dicece_fold0_vs` | Base-size architecture if memory permits | second priority |
| `R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs` | Larger kernel / UpKern-inspired variant | only after A import/adapter gate passes |
| `R17_D_mednext_s_modality_channels_fold0_vs` | Add modality presence channels if low cost | watch; do not block A/B |
| `R17_E_mednext_s_small_boundary_aux_fold0_vs` | Small boundary/surface auxiliary | auxiliary only after standard Dice/CE signal exists |

## Main Route 2: `MedNeXt_baseline_preserving_or_pretrained_initialization_route`

目标：判断 MedNeXt 是否能安全利用初始化，而不是盲目 scratch long training。

Allowed candidates:

- CARE-only MedNeXt from scratch, with explicit short budgets.
- UpKern small-to-large kernel only if implemented without external weights and without changing label/evaluator semantics.
- Public pretrained initialization only after compliance gate passes.

Compliance rules:

- Public pretrained weights may be potentially allowed by CARE rules, but only if provenance is explicit.
- Record pretrained data source, license, weight URL, model card / README evidence, and whether any external image/label data would influence training.
- Do not download or use large weights during planning. In future goal-mode, do not download weights until compliance matrix says `pass_weight_gate` and user authorization is clear.
- No external image/label dataset may be mixed into training.
- No validation pseudo-label supervised training.

Initial Round17 decision:

- Default to code-only MedNeXt architecture trained on CARE fold0 data.
- Treat pretrained MedNeXt-v2 / M&Ms / nnU-Net Task114 weights as `watch` until weight provenance and challenge compliance are documented.

## Main Route 3: `MedNeXt_plus_joint_scar_edema_objective_route`

目标：在 stronger backbone 上先建立 conservative scar+edema joint objective，再按证据加入小权重 edema-specific auxiliary。不要重复 Round4 的 recall-heavy Focal Tversky failure，也不要为了 edema 牺牲 LGE-driven scar。

Initial loss policy:

- First MedNeXt jobs should use conservative standard Dice/CE or the repo-equivalent baseline segmentation objective.
- Do not start with Focal Tversky as the main objective.
- Do not make class_4 recall-heavy at the cost of HD/component/remote FP.
- Do not downweight or ignore class_5 scar; scar supervision remains a co-primary objective because a stronger backbone should plausibly improve both LGE-driven scar and T2-driven edema representation.
- T2-present and no-T2 policies should be recorded in metrics/reporting first; do not add complex no-T2 loss changes before MedNeXt baseline signal is known.

Optional later auxiliary objectives:

| objective | role | gate |
| --- | --- | --- |
| small-weight surface / boundary loss | HD95 watch item | only if standard MedNeXt has positive Dice/localization signal but boundary remains bad |
| component-aware auxiliary | component / remote FP guard | only small weight, never primary recall driver |
| T2-present edema weighting | reporting-guided supervision | only after standard model shows no no-T2 FP drift |
| scar boundary / LGE lesion consistency | scar co-primary auxiliary | only if scar has baseline-level or positive signal and no edema regression |

## Auxiliary Route 1: `MedNeXt_external_repo_compliance_and_import_route`

目标：系统审查 MedNeXt v1/v2 repo、license、dependencies、model size、spacing assumption、pretrained assets and integration risk。

Known starting point from Round16:

| item | current evidence |
| --- | --- |
| repo | `https://github.com/MIC-DKFZ/MedNeXt.git` cloned during Round16 metadata smoke under ignored diagnostics root |
| license | Apache-2.0-like detected |
| import / instantiate | passed Round16 one-case instantiate smoke, about 5.55M params in tested configuration |
| limitation | original project is nnU-Net-v1-oriented; CARE repo uses current Dataset501/nnU-Net-compatible first-party tooling |
| risk | MedNeXt paper assumptions include 1mm isotropic spacing in some settings; CARE nnU-Net median spacing / preprocessing must be verified, not assumed |

Required Round17 compliance outputs:

- license file excerpt / classification.
- repository URL and commit hash.
- dependency list and incompatibilities.
- nnU-Net v1/v2 assumptions.
- model sizes S/B/M/L and estimated GPU memory.
- expected input channels and output classes.
- pretrained weights available? yes/no/unclear.
- pretrained weight source and data provenance if any.
- compliance risk under “pretrained allowed, external training data not allowed”.

## Auxiliary Route 2: `Round18_external_method_fallback_readiness`

If MedNeXt has no clean signal, Round18 should not revert to generic feature-head/refiner epochs. It should choose one of the following controlled external mechanisms:

| mechanism slot | candidate source | Round18 stance |
| --- | --- | --- |
| intensity prior | I-MMSeg-style T2/LGE intensity prior | metadata/import dependency repair and one-case feature smoke |
| anatomy/pathology cascade | Cascaded FSN / PT-Net | anatomy-lesion consistency, not hard ROI deletion |
| boundary / HD | InverseForm / surface / HD-aware loss | auxiliary only; license/dependency risk remains |
| missing-modality representation | UniME / AdaMM / CoPeDiT / MoE / MMPL-Seg | no full distillation until complete-case teacher reliability and external data compliance are solved |
| alignment | CAA-Seg / SSA | watch; raise only if overlays show sequence mismatch |
| pretrained feature/backbone | MedNeXt-v2, MIST, nnU-Net pretrained, M&Ms/Task114 | compliance-first, no weights without provenance |

## Stage 1: `round17_mednext_reproducibility_and_registry_gate`

Goal:

- Reproduce the current Round16 stop decision and locate all baseline references before touching MedNeXt integration.

Allowed:

- Read README/TODO/plans/diagnostics.
- Create Round17 output root and readme.
- Create config drafts, candidate registry, and path manifest.
- Verify Dataset501 fold0 baseline paths, fold split, label semantics, evaluator, export mapping, spacing/patch metadata, and GPU memory assumptions.

Forbidden:

- Training.
- Slurm submission.
- External repo clone/install.
- Weight download.
- Validation zip/upload.

Expected outputs:

- `round17_goal_execution_readme.md`
- `round17_reproducibility_gate.csv`
- `round17_baseline_path_manifest.csv`
- `round17_mednext_candidate_matrix.csv`

Pass criteria:

- nnU-Net501 fold0 reference predictions and metrics can be located.
- Dataset501 labels class_4 edema and class_5 scar are confirmed.
- Fold0 validation list and hard cases `Case2031`, `Case3011`, `Case3012`, `Case3040`, `Case3044` are identified.
- Output root is isolated under `results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/`.

Fail criteria:

- Baseline metrics/path cannot be found.
- Label/evaluator semantics are ambiguous.
- Any script would write into nnU-Net501 baseline cache.

Next if pass: Stage 2.

## Stage 2: `mednext_repo_metadata_and_compliance_audit`

Goal:

- Audit MedNeXt v1/v2 metadata and decide whether Round17 can use code-only architecture and whether any weight-based path is allowed later.

Allowed:

- Read existing Round16 cloned MedNeXt repo metadata if present.
- Inspect license, README, setup, model definitions, documentation, dependency assumptions.
- Record repo URL / commit hash.
- If existing clone is missing, future goal-mode may clone the repo for metadata only after confirming no weights/data download.

Forbidden:

- Download pretrained weights.
- Download external datasets.
- Train external code.
- Treat weights as allowed without data provenance.

Expected outputs:

- `round17_mednext_compliance_matrix.csv`
- `round17_mednext_repo_metadata_audit.md`
- `round17_pretrained_weight_provenance_audit.csv`

Pass criteria:

- Code license is acceptable for research use.
- Architecture code can be used or vendored/referenced with traceable provenance.
- Weight usage status is clearly one of `not_used`, `blocked_pending_provenance`, or `pass_weight_gate`.

Fail criteria:

- License blocks use.
- Dependencies require disruptive global environment changes.
- Weight provenance is unclear but a candidate attempts to use weights.

Next if code-only pass: Stage 3.

## Stage 3: `mednext_import_and_onecase_shape_smoke`

Goal:

- Verify minimal MedNeXt import, instantiate, forward/backward shape, output class mapping, and memory footprint.

Allowed:

- Create first-party wrapper under `src/care_myocardium/backbones/` or `src/care_myocardium/mednext/` in future goal-mode.
- Create diagnostic smoke script under `scripts/diagnostics/`.
- Run CPU/GPU one-case shape smoke, not long training.
- Test 3 input channels first; optional 6-channel modality presence only if low risk.

Forbidden:

- Full training.
- External data.
- Weight download.
- Modifying evaluator or label semantics.

Expected outputs:

- `round17_import_onecase_smoke_summary.csv`
- `round17_network_shape_smoke.md`
- `round17_memory_footprint_estimate.csv`

Pass criteria:

- Forward/backward runs with finite gradients.
- Output logits can map to 6 compact classes.
- No NaN/Inf.
- Memory footprint is compatible with planned htzhulab/A100/volta budgets.

Fail criteria:

- Import blocked by dependency conflict that requires large environment changes.
- Shape mismatch cannot be isolated.
- First layer/channel logic is unclear.

Next if pass: Stage 4.

## Stage 4: `mednext_care_dataset_adapter_smoke`

Goal:

- Connect MedNeXt to CARE Dataset501 fold0 data path without changing baseline preprocessing/evaluator semantics.

Allowed:

- Implement minimal dataset adapter or reuse existing nnU-Net/Dataset501 preprocessed tensors.
- One-batch train/validation smoke.
- Verify C0/LGE/T2 channel order and missing-modality behavior.
- Verify patch extraction and spacing/affine consistency.

Forbidden:

- Long training.
- Silent label remapping.
- Writing into baseline nnU-Net validation directories.

Expected outputs:

- `round17_dataset_adapter_smoke_summary.csv`
- `round17_channel_label_semantics_audit.csv`
- `round17_train_config_templates/`

Pass criteria:

- One train batch and one validation batch load successfully.
- Class labels remain 0-5 with edema=4 and scar=5.
- Predictions can be exported to the evaluator format.

Fail criteria:

- Channel order is ambiguous.
- Patch/spacing mismatch makes comparisons invalid.
- Export cannot preserve compact labels.

Next if pass: Stage 5.

## Stage 5: `mednext_fold0_very_short_training_batch`

Goal:

- Submit a bounded batch of MedNeXt fold0 very-short jobs only after import/adapter gates pass.

Allowed:

- Multiple independent fold0 very-short Slurm jobs.
- Preferred partition `htzhulab`; fallback to `a100-gpu` then `volta-gpu` only if htzhulab wait is materially long.
- Each job must have isolated output dir, config, random seed, and job name.
- Suggested walltime: <= 8 hours per job; use explicit epoch/iteration/max-runtime cap.

Forbidden:

- fold1-4 or 5-fold.
- validation zip/upload.
- Using pretrained weights without completed pass_weight_gate.
- Continuing failed jobs by simply extending epochs.

Candidate batch:

| candidate | job type | priority | notes |
| --- | --- | --- | --- |
| `R17_A_mednext_s_kernel3_standard_dicece_fold0_vs` | fold0 very-short | high | first baseline stronger-backbone candidate |
| `R17_B_mednext_b_kernel3_standard_dicece_fold0_vs` | fold0 very-short | high if memory permits | checks capacity effect |
| `R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs` | fold0 very-short | medium | only if large-kernel path is clean |
| `R17_D_mednext_s_modality_channels_fold0_vs` | fold0 very-short | medium | only if 6-channel handling is safe |
| `R17_E_mednext_s_small_boundary_aux_fold0_vs` | fold0 very-short | low/watch | only after A/B show viable training signal |

Expected outputs:

- `round17_batch_job_submission_plan.md`
- `round17_batch_job_status.csv`
- per-candidate `train_config.yaml`
- per-candidate `train_command.txt`
- `round17_fold0_very_short_results.csv`

Pass criteria:

- 44/44 fold0 validation predictions generated per completed candidate.
- Training stable with no NaN/Inf.
- At least one candidate shows clean T2-present GT-positive or CenterC edema signal while scar Dice/HD95 is non-regressed or improved, and no-T2/component/remote FP guardrails are clean.

Fail criteria:

- Empty predictions.
- Label/evaluator/cache silent change.
- Severe target subset regression like Round16 F.
- No candidate changes target subsets beyond baseline fallback.

Next if at least one candidate passes: Stage 6 then Stage 7.

## Stage 6: `mednext_result_collection_and_gate`

Goal:

- Collect all very-short results and decide which, if any, can enter fold0 short.

Required metrics:

- `myops_edema` class_4 Dice, HD, HD95.
- `myops_scar` class_5 Dice, HD, HD95 as co-primary non-regression / improvement metric.
- component count, small FP, remote FP.
- pred/GT volume ratio.
- no-T2 edema FP voxel count and case count.
- training stability, runtime, memory.
- cache/label/evaluator integrity.

Required subsets:

- all-case.
- T2-present GT-positive.
- complete-modality.
- CenterB.
- CenterC.
- no-T2 empty-GT.
- C0+LGE no-T2.
- LGE-only.
- center groups.
- `Case2031`, `Case3011`, `Case3012`, `Case3040`, `Case3044`.

Expected outputs:

- `round17_baseline_vs_candidate_by_subset.csv`
- `round17_centerC_edema_table.csv`
- `round17_no_t2_empty_gt_fp_table.csv`
- `round17_scar_guardrail_table.csv`
- `round17_component_remote_fp_table.csv`
- `round17_case_level_failure_flags.csv`
- optional `overlays/`

Promotion rules:

- `strong_promote_to_fold0_short`: T2-present GT-positive edema or CenterC edema has clear positive signal; HD95/component/remote FP not worse; scar Dice/HD95 also improves or is exactly clean; no-T2 FP controlled.
- `promote_to_fold0_short`: edema has clean primary-gate signal and scar is non-regressed, even if scar does not improve.
- `watch`: scar improves but edema has no CenterC/T2-present signal, or edema signal is weak with one borderline guardrail; no automatic expansion unless user explicitly chooses.
- `stop`: no target signal, baseline fallback only, severe regression, scar/no-T2/component/remote FP failure, or any cache/label/evaluator issue.

Next if promoted: Stage 7.

## Stage 7: `promoted_mednext_fold0_short_training`

Goal:

- Run fold0 short only for candidates promoted by Stage 6.

Allowed:

- One or more promoted fold0 short jobs.
- Same evaluator and subsets as Stage 6.
- Runtime <= 8 hours unless user explicitly approves longer.

Forbidden:

- fold1-4 / 5-fold.
- validation zip/upload.
- Adding new loss/architecture changes while moving from very-short to short; keep candidate identity stable.

Expected outputs:

- `round17_fold0_short_results.csv`
- `round17_fold0_short_candidate_decision.md`
- updated candidate rows in all subset/guardrail tables.

Pass criteria:

- Clear improvement in T2-present GT-positive or CenterC edema.
- Scar class_5 Dice/HD95 improves or remains cleanly non-regressed versus nnU-Net501 baseline.
- Dice and HD95 do not show severe tradeoff.
- component count and remote FP do not worsen.
- no-T2 empty-GT edema FP not uncontrolled.

Fail criteria:

- Improvement only appears in all-case or empty-GT artifact.
- CenterC does not improve or worsens.
- HD95/component/remote FP deteriorates.
- scar co-primary metric not clean: Dice or HD95 clearly regresses.

Next if pass: Stage 8. Do not auto-expand folds.

## Stage 8: `round17_decision_and_round18_recommendation`

Goal:

- Decide whether MedNeXt becomes the next Lane A mainline or whether Round18 should move to another high-upside route.

Expected outputs:

- `round17_candidate_decision_table.md`
- `round17_round18_recommendation.md`
- `round17_deep_research_need_assessment.md`

Decision logic:

| outcome | decision |
| --- | --- |
| MedNeXt improves edema and preserves/improves scar in very-short and fold0 short | prepare Round18 MedNeXt fold0 longer / fold expansion plan; do not execute fold1-4 without user authorization |
| MedNeXt improves scar but not edema | watch as backbone representation signal; do not promote Lane A unless edema primary gate is addressed |
| MedNeXt has weak but stable edema signal with scar non-regression | watch; consider one narrower MedNeXt objective/config pass |
| MedNeXt no signal but engineering stable | stop expansion; Round18 should focus I-MMSeg intensity prior or another external mechanism with one-case smoke |
| MedNeXt engineering blocked | assess MedNeXt-v2/MIST/other backbone only after metadata/compliance audit |
| all stronger-backbone candidates fail | request narrower deep research on CenterC/T2 edema representation, complete-case teacher reliability, and CMR edema label ambiguity |

## Unified Evaluation Rules

Every Round17 candidate must be compared against the same nnU-Net501 fold0 baseline. Report:

- `myops_edema` class_4.
- `myops_scar` class_5 as co-primary non-regression / improvement metric.
- all-case.
- T2-present GT-positive.
- complete-modality.
- CenterB.
- CenterC.
- no-T2 empty-GT.
- C0+LGE no-T2.
- LGE-only.
- center groups.
- `Case2031`, `Case3011`, `Case3012`, `Case3040`, `Case3044`.

Metrics:

- Dice.
- HD.
- HD95.
- component count.
- small FP.
- remote FP.
- pred/GT volume ratio.
- no-T2 edema FP voxel count.
- no-T2 edema FP case count.
- scar Dice/HD95 co-primary non-regression / improvement.
- training NaN/Inf.
- runtime and memory.
- cache/label/evaluator integrity.

Hard failure conditions:

- Any silent label remap or evaluator change.
- Candidate only wins foreground_mean or all-case aggregate.
- Candidate gains only by empty-GT artifact.
- no-T2 edema FP becomes uncontrolled.
- class_5 scar co-primary metric regresses.
- CenterC or T2-present GT-positive edema has no signal.
- HD95/component/remote FP clearly worsens.
- external data or unclear pretrained weights are used.

## Output Root And Files

Canonical Round17 root:

```text
results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/
```

Minimum expected outputs:

```text
round17_goal_execution_readme.md
round17_reproducibility_gate.csv
round17_baseline_path_manifest.csv
round17_mednext_compliance_matrix.csv
round17_mednext_repo_metadata_audit.md
round17_pretrained_weight_provenance_audit.csv
round17_import_onecase_smoke_summary.csv
round17_network_shape_smoke.md
round17_memory_footprint_estimate.csv
round17_dataset_adapter_smoke_summary.csv
round17_channel_label_semantics_audit.csv
round17_mednext_candidate_matrix.csv
round17_batch_job_submission_plan.md
round17_batch_job_status.csv
round17_fold0_very_short_results.csv
round17_fold0_short_results.csv
round17_baseline_vs_candidate_by_subset.csv
round17_centerC_edema_table.csv
round17_no_t2_empty_gt_fp_table.csv
round17_scar_guardrail_table.csv
round17_component_remote_fp_table.csv
round17_case_level_failure_flags.csv
round17_candidate_decision_table.md
round17_round18_recommendation.md
round17_deep_research_need_assessment.md
```

Per-candidate outputs should live under:

```text
results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/<candidate_id>/
```

Overlays or feature visualizations:

```text
results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/overlays/
```

## Future Goal-Mode Resource Stance

用户 token、Slurm、GPU 资源充足，goal-mode 可以尽可能多往前推进，但推进方式必须是 staged, gated, compliance-checked, and comparable。

Allowed in one future goal-mode run if gates pass:

- MedNeXt metadata/compliance audit.
- import / one-case shape smoke.
- CARE Dataset501 adapter smoke.
- multiple fold0 very-short jobs.
- automatic result collection.
- promoted fold0 short jobs only for candidates that pass very-short gate.
- decision table and Round18 recommendation.

Still requires separate user authorization:

- fold1-4.
- 5-fold.
- validation zip.
- validation upload.
- downloading or using large pretrained weights, unless compliance and user authorization are explicit.

Do not skip import/shape/cache/evaluator gates because resources are available.

## Next Goal Execution Prompt Draft

```text
你现在在 `/overflow/htzhu/CARE` 中工作。请按

`docs/plans/laneA_round17_next_mednext_stronger_backbone_integration_execution.md`

执行 Lane A Round17 MedNeXt / stronger backbone CARE-native integration。资源充足，可以尽可能向前推进，但必须 staged、gated、compliance-checked、comparable。

严格禁止：validation zip/upload、fold1-4、5-fold、external image/label training、使用 provenance 不清楚的 pretrained weights、跳过 import/shape/cache/evaluator gates、继续 Round15/16 A/C/E/F 加 epoch、回到 Focal Tversky/小组件/hard ROI/anatomy attenuation/whole-network nnU-Net small tweak。

请执行以下阶段：

1. 复核 Round16 final gate `stop_no_promoted_candidate`、nnU-Net501 fold0 baseline、Dataset501 split、label semantics、evaluator/export/cache/spacing。所有 Round17 outputs 使用：
   `results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone/`
   不要创建 legacy `phase0_phase1` 目录。

2. 审查 MedNeXt v1/v2 repo metadata、license、dependencies、nnU-Net assumptions、model sizes、spacing assumptions、pretrained weight provenance。默认只允许 code-only CARE-only architecture route；不得下载大权重或外部数据。

3. 做 MedNeXt import / instantiate / one-case forward+backward shape smoke，记录 input channels、output classes 0-5、deep supervision、memory、NaN/Inf。

4. 接入 CARE Dataset501 fold0 adapter，验证 C0/LGE/T2 channel order、可选 modality presence channels、class_4 edema/class_5 scar semantics、patch/spacing、prediction export。

5. 通过前置 gates 后，批量提交 fold0 very-short MedNeXt candidates。至少尝试：
   - `R17_A_mednext_s_kernel3_standard_dicece_fold0_vs`
   - `R17_B_mednext_b_kernel3_standard_dicece_fold0_vs`
   只有实现成本低且 gates clean 时再尝试：
   - `R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs`
   - `R17_D_mednext_s_modality_channels_fold0_vs`
   - `R17_E_mednext_s_small_boundary_aux_fold0_vs`
   每个 job 必须独立 output dir、config、seed、job name；默认 htzhulab，只有 htzhulab 预计长等待时才按 AGENTS fallback 到 a100-gpu/volta-gpu。

6. 自动收集结果并与 nnU-Net501 fold0 baseline 比较。必须报告 `myops_edema` class_4 和 `myops_scar` class_5。Round17 的 stronger-backbone route 目标是 scar+edema joint improvement：edema 是最硬 primary gate，scar 是 co-primary non-regression / improvement metric。必须报告 all-case、T2-present GT-positive、complete-modality、CenterB、CenterC、no-T2 empty-GT、C0+LGE no-T2、LGE-only、Case2031/3011/3012/3040/3044，以及 Dice、HD、HD95、component count、small/remote FP、pred/GT volume ratio、scar co-primary delta、runtime/memory/cache integrity。

7. 只对 very-short gate clean 的 candidate 继续 fold0 short。若无 candidate 有 clean CenterC/T2-present signal，直接 stop and record，不要扩大训练。若 fold0 short clean，只准备 Round18 fold0 longer/fold1-4 plan，不自动执行 fold1-4 或 validation upload。

完成后更新 Round17 output readme、candidate decision table、Round18 recommendation，并给出 promote/watch/stop 结论。
```
