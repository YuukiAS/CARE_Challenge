# CARE Benchmark Runbook

## GPT / ChatGPT Route Bootstrap

Any new GPT/ChatGPT planning thread must read [START_HERE_FOR_GPT.md](START_HERE_FOR_GPT.md), [GPT_PLANNER_CARE_PROTOCOL.md](GPT_PLANNER_CARE_PROTOCOL.md), [prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md](prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md), and [prompts/GPT_HARD_GATE_PROMPT.md](prompts/GPT_HARD_GATE_PROMPT.md) before writing SRR/MyoPS/Cine milestones. It must visually read the SRR route diagrams from ChatGPT Project background files / project materials first; repository `images/` paths are canonical filenames/version references, and old chat summaries are not enough.

For current architecture and handoff state, start at [wiki/README.md](wiki/README.md). Long Slurm or high-resume-risk work must use the v2 controller-supervised flow: planner -> controller -> executor/mapper/finalizer/validator -> independent reviewer.

Benchmark training / collection / unified evaluation commands live in [jobs/README.md](/overflow/htzhu/CARE/jobs/README.md).

Most common entrypoints:

```bash
# Single-fold smoke test (default fold 0): prep + submit
bash jobs/run_unified_benchmark_test.sh

# Single-fold postprocessing after jobs finish: collect + unified eval
bash jobs/run_unified_benchmark_test.sh post --fold 0

# Full 5-fold benchmark: prep + submit
bash jobs/run_unified_benchmark_all.sh

# Full 5-fold postprocessing after jobs finish: collect + unified eval
bash jobs/run_unified_benchmark_all.sh post

# nnUNet501 + nnUNet502 were already trained: collect all 5 folds into models/
bash jobs/collect_benchmark_weights.sh --folds "0 1 2 3 4" --only nnUNet
```

Notes:

- `jobs/benchmark_protocol_helpers.sh` is a helper for protocol generation and split injection. You usually do not call it directly except for inspection/debugging.
- `jobs/run_unified_benchmark_test.sh` and `jobs/run_unified_benchmark_all.sh` each contain a single `BENCHMARK_MODEL_PLAN` block near the top. Edit that list to mark each model as `run`, `eval`, or `skip`. Right below it, **`UMYOPS_BENCHMARK_STAGES`** controls U-MyoPS Slurm submits when `U-MyoPS=run`: **`stage1`** (default), **`stage2`** only, or **`both`** / **`all`**.

```bash
UMYOPS_BENCHMARK_STAGES=both bash jobs/run_unified_benchmark_all.sh submit
```

## Slurm Queue Note

`htzhulab` jobs may not appear in a plain user queue query. Always check the lab partition explicitly before assuming a CARE job has finished or disappeared:

```bash
squeue -p htzhulab -u "$USER"
```

For current CARE model work, treat `htzhulab` as the preferred partition. Use school GPU fallbacks only when `htzhulab` has a materially long wait; see `AGENTS.md` for the exact `a100-gpu` and `volta-gpu` headers.

## Validation Submission Semantics

The upload artifact is one `CARE-Myocardium-OrganAgent.zip` containing both `MyoPS/` and `CineMyoPS/` folders. Each upload is one validation submission attempt, and the platform returns three task metrics from that same zip:

| Leaderboard task | Uses branch in zip | Primary local reference |
| --- | --- | --- |
| `myops_scar` | `MyoPS/.../*_pred.nii.gz` | Dataset501 class_5 |
| `myops_edema` | `MyoPS/.../*_pred.nii.gz` | Dataset501 class_4 |
| `myocardium_cinemyops` | `CineMyoPS/.../*_pred.nii.gz` | Dataset502 class_1 proxy plus class_3 sanity |

Do not plan three separate uploads for the three metrics. A hybrid package can still mix model sources across branches, for example nnU-Net on MyoPS and CineMyoPS on Cine, but it consumes one submission and should be interpreted as one package with three returned scores. When comparing methods, analyze each returned metric separately rather than collapsing them into a single score.

## CARE Myocardium Current Status

Snapshot: 2026-05-23. nnU-Net remains the operational MyoPS baseline. MyoPS-Net and U-MyoPS remain negative evidence and mechanism sources, but they should not be patched as the main route. Lane B is waiting for hosted calibration from the third validation attempt. Lane A has now tested shallow postprocess, loss, modality-mask, anatomy-prior, whole-network adaptation, and refiner routes through Round11; no Lane A candidate has passed a validation-submission gate.

Current Lane A strategic reading:

- The edema bottleneck is not simple class imbalance, inference fragments, one loss weight, or simple anatomy support.
- Class-4 edema learning is jointly limited by T2 presence, center, label availability, boundary/topology, and baseline representation limits.
- CenterC complete-modality edema is the current key failure zone.
- no-T2 empty-GT cases cannot be treated as strong edema negatives, but simply weakening no-T2 supervision can create edema false positives.
- The nnU-Net baseline gives stable scar/anatomy structure, but its edema representation is still weak for CenterC/T2-present cases.
- Refiner-style work is safer than whole-network fine-tuning because scar can stay unchanged and no-T2 FP can be controlled, but current refiner variants are not effective enough. Treat the refiner route as a baseline-preserving auxiliary substrate, not the sole mainline to extend with more epochs.

### Validation Submission Attempts

CARE Myocardium validation uses one upload package containing both `MyoPS/` and `CineMyoPS/`. One attempt returns all three hosted metrics: `myops_scar`, `myops_edema`, and `myocardium_cinemyops`. Do not split these into three independent submissions, and do not use `foreground_mean` to hide a single-task failure.

| attempt | package / branch | status and purpose |
| --- | --- | --- |
| 1 | early validation package | Failed because prediction format was wrong. Keep only as a packaging lesson. |
| 2 | `nnUNet_MyoPS + CineMyoPS pathology_direct` | Baseline hosted package. It established the visible baseline row but left hosted `myocardium_cinemyops` weak. |
| 3 | `nnUNet5fold_MyoPS + Cine_topology_lcc_round03` | Hosted calibration package, not a final leaderboard push. It tests whether Cine topology LCC improves hosted `myocardium_cinemyops` HD/Dice while keeping a conservative nnU-Net 5-fold MyoPS fallback. |

Current third-attempt zip:

```text
/overflow/htzhu/CARE/results/submissions/care_myocardium_validation/upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/CARE-Myocardium-OrganAgent.zip
```

Current hosted status: the third attempt is a hosted-calibration submission, not a final leaderboard push. Do not start another Cine topology guard experiment while waiting for the hosted result. Lane A has no candidate authorized for validation packaging or upload.

### Lane B: Cine Topology

Round2/Round3 show `topology_lcc` is the cleanest Cine topology candidate so far. The local class-3 comparison is:

| Cine candidate | class_3 Dice | class_3 HD95 | components |
| --- | ---: | ---: | ---: |
| `pathology_direct` | ~0.4378 | ~26.6533 | ~5.5385 |
| `topology_lcc` | ~0.4441 | ~18.7983 | ~1.0000 |

Round3 packaging QA passed:
- 15/15 Cine validation cases matched.
- Raw labels are legal: `{0,200,500,2221}`.
- Compact-to-raw mapping stayed `1->200, 2->500, 3->2221`.
- Raw `2221` is non-empty in 15/15 cases.
- No fallback labels were injected.
- 15/15 cases have exactly one Cine class-3 component.
- The MyoPS branch hash matches the conservative nnU-Net package.

Current decision: wait for hosted results. If hosted Cine HD clearly improves, promote `topology_lcc` as the default Cine fallback. If hosted Cine does not improve, stop further topology-guard tuning and move to hosted metric semantic analysis or a stronger Cine model route. Lane B should not open more local topology guard variants before that hosted result returns.

### Lane A: MyoPS Edema Evidence Chain

Lane A is now past minor tweak territory. The evidence chain should be read by stage, not as a list of promising variants:

| round | route tested | conclusion |
| --- | --- | --- |
| Round2 | edema inference postprocess | Failed. Small connected-component deletion and ROI thresholds reduced component count but did not cleanly improve GT-positive edema Dice/HD95. Stop small-component deletion, ROI thresholding, and inference-side suppression as mainlines. |
| Round3 | loss wiring / gradient / tiny-overfit smoke | Engineering pass only. It showed candidate losses could run without NaN/Inf and without class-5 interference, but it did not prove performance. |
| Round4 | `edema_focal_tversky + no_t2_edema_loss_downweighting` fold0 short train | Failed. There was a tiny local Dice signal, but remote FP, no-T2 FP, HD95, and scar guardrails were not clean. Stop recall-heavy Focal Tversky and simple no-T2 downweighting as mainlines. |
| Round5 | controlled mechanism audit | Alignment / CAA-Seg-SSA stayed `watch`; boundary/distance stayed `watch`; anatomy-guided soft prior entered bounded diagnostic. |
| Round6 | anatomy soft attenuation and missing-modality audit | Anatomy distance attenuation failed, even with GT myocardium-derived oracle-style support. Stop anatomy distance attenuation and hard ROI/hard deletion. Anatomy may still be a future feature or regularizer. Missing-modality audit gave the key positive signal: no-T2 empty-GT is not a reliable strong negative; explicit modality presence and uncertainty-aware supervision remain important directions. |
| Round7 | first-party six-channel modality-presence pipeline | Engineering feasible, but simple presence channels plus scalar no-T2 weighting failed the tiny gate. U1 was too weak; U2 had edema signal but created no-T2 FP. Stop U1/U2 scalar-weight tuning. |
| Round8 | T2-present edema expert / separated edema supervision | Tiny gate had signal, but scratch / near-scratch fold0 very-short training collapsed. Do not interpret this as the mechanism being impossible; interpret it as evidence that a scratch 3-epoch structure-change model should not be compared directly to a fully trained nnU-Net501 baseline. Lane A needs baseline-preserving adaptation. |
| Round9 | nnU-Net501 checkpoint migration to six-channel model and whole-network fine-tune | Checkpoint migration worked: initial logits could match baseline exactly. Whole-network checkpoint-initialized fine-tune still failed with weak edema signal and unclean component/HD95/scar guardrails. Stop whole-network fine-tune as a mainline. The edema-only residual-refiner safety gate passed, supporting a baseline-preserving class-4-only route. |
| Round10 | add-only conservative edema residual refiner | Safer than whole-network fine-tune: scar was voxel-level unchanged and no-T2 empty-GT got no new edema FP. Effectiveness was weak: tiny Dice gain, HD95/component not clean, `Case2031` and `Case3012` component worsened. Do not just add epochs or expand folds. |
| Round11 | component-safe bidirectional edema refiner | Failed. Scar stayed unchanged and no-T2 empty-GT stayed clean, but CenterC and remote-FP guardrails were not clean. `Case3011` and `Case3040` were flagged `edema_remote_fp_worse`. This candidate must not enter fold0 short, fold0 longer, fold1-4, 5-fold, validation packaging, or submission. |

Stopped or downgraded Lane A routes:

- Stop: small-component/ROI postprocess, recall-heavy Focal Tversky, simple no-T2 downweighting, anatomy distance attenuation, hard ROI/hard deletion, scratch separated route, whole-network checkpoint fine-tune, add-only residual refiner, and current bidirectional residual refiner.
- Downgrade: refiner route. It is a useful baseline-preserving substrate because it can protect class-5 scar and no-T2 empty-GT stability, but it has not solved CenterC/T2-present edema localization or remote FP.
- Preserve as mechanism sources only: alignment, anatomy support, boundary/HD, intensity prior, and missing-modality representation ideas from Deep Research.

### Lane A Round11 Failure Summary

The detailed Round11 failure-case summary has been generated under:

```text
results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/failure_case_summary/
```

Key case findings:

| case | observed failure | current interpretation |
| --- | --- | --- |
| `Case2031` | Round10 component worsening; Round11 improves component count but still has low-support edge activation | `threshold_fragmentation`, `refiner_random_edge_activation`, `T2_support_weak_or_ambiguous` |
| `Case3012` | Round10 component worsening; Round11 component fallback returns to baseline | Fusion safety works, but the refiner does not provide a useful correction for this case |
| `Case3011` | Round11 remote FP worsens despite component improvement | `add_residual_remote_island`, `T2_support_weak_or_ambiguous` |
| `Case3040` | Round11 Dice/HD95/remote FP worsen despite component improvement | `refiner_random_edge_activation`, `add_residual_remote_island`, `T2_support_weak_or_ambiguous` |

Salvage reading:

- Post-hoc fallback of `Case3011` and `Case3040` to baseline would remove the remote-FP regression and preserve part of the tiny Dice gain, but this is not deployable by itself because it uses case IDs and validation behavior.
- A final fusion-level salvage is only worth considering if it uses deployable proxies such as residual magnitude, distance to baseline edema, distance to myocardium/anatomy support, component size, T2 intensity support, and largest-component fraction.
- If a deployable fallback/fusion rule cannot remove remote/component worsening while preserving the tiny Dice gain, the refiner route should stop as a mainline.

### Next Lane A Direction

Do not train the current refiner longer. Do not submit Lane A. The next Lane A step is either:

1. one final bounded deployable fallback-rule diagnostic for the refiner, using only proxy rules and no GT-based case picking; or
2. downgrade the refiner to an auxiliary substrate and move the mainline to controlled external/high-upside mechanism integration.

Future mechanisms must enter by slot, not by wholesale repo reproduction:

- I-MMSeg-style T2/LGE intensity prior: improve edema support and suppress weak-T2 remote activation.
- Cascaded FSN / PT-Net-style anatomy/pathology cascade: provide structured anatomy support without hard deletion.
- InverseForm / surface / HD-aware objective: boundary/topology watch item, not a standalone fix.
- AdaMM / UniME / CoPeDiT / MoE: missing-modality representation and routing, but only after compliance, complete-case teacher reliability, and external-data risk are audited.
- CAA-Seg / SSA: alignment watch; raise priority only if failure overlays show sequence mismatch.
- BiomedParse / MedNeXt / nnU-Net Task114/M&Ms: future pretrained feature/backbone watch, subject to license, pretrained data source, and CARE external-data rules.

### Traceable Files

| area | path |
| --- | --- |
| Lane A Round10 active execution | `docs/plans/laneA_round10_active_edema_only_residual_refiner_execution.md` |
| Lane A Round11 active execution | `docs/plans/laneA_round11_active_component_safe_bidirectional_edema_refiner_execution.md` |
| Lane A Round10 refiner model | `src/care_myocardium/refiner/laneA_round10_model.py` |
| Lane A Round11 refiner model | `src/care_myocardium/refiner/laneA_round11_model.py` |
| Lane A Round11 diagnostic script | `scripts/diagnostics/laneA_round11_component_safe_refiner.py` |
| Lane A Round11 train/smoke entrypoint | `scripts/training/run_laneA_round11_bidirectional_refiner_train.py` |
| Lane A Round10 outputs | `results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner/` |
| Lane A Round11 outputs | `results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/` |
| Lane A Round11 failure summary | `results/diagnostics/care_myocardium/laneA_myops/round11_component_safe_refiner/failure_case_summary/` |
| Lane B Round3 hosted calibration prep | `scripts/diagnostics/laneB_round03_hosted_calibration_prep.py` |
| Lane B Round3 hosted calibration outputs | `results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration/` |
| Current hosted calibration zip | `/overflow/htzhu/CARE/results/submissions/care_myocardium_validation/upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/CARE-Myocardium-OrganAgent.zip` |
| Submission package registry | `results/submissions/care_myocardium_validation/upload_ready/README.md` |
| MyoPS-Net stop note | `docs/notes/baseline/MyoPS-Net_improvement_round8.md` |
| U-MyoPS stop note | `docs/notes/baseline/U-MyoPS_improvement_round8.md` |
| Dice/HD caveat note | `docs/notes/baseline/Dice_HD.md` |

## CARE Data Facts That Drive the Decision

The CARE MyoPS training set is not the same regime assumed by the original MyoPS-Net and U-MyoPS papers.

| modality group in `MyoPS_train` | cases | share | main centers | implication |
| --- | ---: | ---: | --- | --- |
| C0 + LGE + T2 | 80 | 36.4% | CenterB 35, CenterC 45 | Only this subset supports faithful three-sequence fusion and T2-aware edema learning. |
| C0 + LGE, no T2 | 24 | 10.9% | CenterE 7, CenterF 9, CenterG 8 | Scar may be learnable from LGE, but edema supervision is weak or absent. |
| LGE only | 116 | 52.7% | CenterA 81, CenterH 35 | More than half of training lacks the modalities expected by multi-sequence paper models. |
| LGE + T2, no C0 | 0 | 0.0% | none | There is no center distribution that teaches a natural C0-missing/T2-present pathway. |

Key consequences:

- Edema is structurally under-supervised: T2 is the primary imaging cue, but only `80/220` cases have T2. Any edema model that treats missing T2 as a normal zero-valued channel learns a center-confounded shortcut.
- Modality missingness is center-correlated. Complete cases come mainly from CenterB/CenterC, while LGE-only cases come mainly from CenterA/CenterH. A complete-case expert risks learning center style as much as pathology.
- Official validation MyoPS has complete LGE+C0+T2 for all 15 cases, but the training signal remains dominated by incomplete cases. The validation input being complete does not fix the lack of T2+edema supervision during training.
- Dice and HD are not interchangeable. Several variants improve one metric while damaging the other; small remote pathology components can leave Dice acceptable while making HD unusable.

## Why MyoPS-Net Stops Here

The MyoPS-Net paper idea is multi-sequence pathology segmentation with modality-specific feature extraction and fusion. In the original setting, the model can assume a relatively coherent multi-sequence input protocol. CARE violates that assumption.

What was fixed:

- The CARE Challenge3 variant removed the nonexistent T1m/T2* mapping path from the forward computation.
- Water-edema supervision was changed from the paper-style edema/scar union to CARE's strict raw labels.
- PI loss and mapping losses that relied on incompatible label/modality assumptions were disabled.
- Export-only calibration, round4 `combined_safe`, full-modality routing, and round8 T2-aware boundary/ROI losses were tested.

Why it still fails:

- After removing T1m/T2*, the model is no longer the original full paper model, but it still inherits a hard multi-sequence fusion bias. That bias is mismatched with `52.7%` LGE-only training data.
- The round8 complete-case expert trained on only 64 fold0 train cases and had weak 2D validation signal: best scar Dice `0.0996`, edema Dice `0.0566`, best epoch 12. It cannot learn a robust 3D pathology model from the small complete subset.
- Complete-case performance still trails nnU-Net: round8 raw expert on C0+LGE+T2 cases reached edema `0.3474`, scar `0.6135`, while nnU-Net fold0 reached edema `0.3944`, scar `0.6933`.
- All-case performance is worse because the expert collapses on missing-modality groups: raw round8 LGE-only scar was `0.0000`, and the hybrid route still only reached edema `0.3293`, scar `0.5048`.
- HD diagnostics did not reveal a simple postprocess fix. Round4 scar Dice `0.5048` and HD `32.6475` remain worse than nnU-Net fold0 scar Dice `0.5602` and HD `25.9706`.

Conclusion: MyoPS-Net has been adapted as far as is useful for this dataset. Its core fusion assumption is now the bottleneck. Further gains would require replacing the model with explicit modality masks, center-aware training, T2-aware edema routing, and a stronger nnU-Net/MedNeXt-style pathology head, which belongs in `src/`, not more patches to `third_party/MyoPS-Net`.

## Why U-MyoPS Stops Here

The U-MyoPS paper idea is to use multi-sequence alignment and anatomy/pathology priors so that C0, T2, and LGE can support each other. CARE again changes the operating regime: more than half of cases are LGE-only, T2 is absent in most training cases, and missingness is center-specific.

What was fixed:

- The original center-slice training bug was replaced with per-slice sampling using `subject_meta.json`.
- Official CARE folds were wired in.
- Stage1/Stage2 export was rewritten to avoid 2D/3D spatial aggregation errors.
- Missing modalities are explicitly recorded, and Stage1 TPS warp skips absent modalities instead of warping zero images as if they were real inputs.
- LGE-only, no-prior, dilated-prior, and prior-reliability variants were tested.

Why it still fails:

- The most reliable U-MyoPS scar result, round8 `component_hd_guard`, reached all-case scar Dice `0.5553`, still below nnU-Net 5-fold `0.5592` and fold0 `0.5602`.
- The only apparent Dice crossing variant, `tiny_c0_lge_no_t2_suppression` at `0.5766`, changes exactly one empty-GT case (`Case7005`). It does not improve scar-positive Dice, so it is a diagnostic artifact rather than a robust model improvement.
- Stage1 prior reliability is heterogeneous. Low cases include empty-GT false positive, weak prior/pathology overlap, under-segmentation, over-segmentation, and mixed localization failures. A single gate cannot fix them without deleting true small scars.
- The paper-style prior helps complete/T2-present cases more than missing-modality cases: round7 complete/T2-present scar was `0.6571`, but missing-modality scar was only `0.4949`.
- U-MyoPS edema is not a trustworthy success signal. High all-case edema values are inflated by empty-GT cases; GT-positive/T2-present edema remains weak. This is exactly the failure mode expected from T2-limited, center-confounded supervision.

Conclusion: U-MyoPS is useful as evidence that anatomy/prior information can help complete cases, but it is not robust enough to replace nnU-Net on CARE MyoPS. The paper's alignment-prior idea should be carried forward only with reliability-aware gating, modality-aware routing, and explicit fallback behavior in a new model.

## Design Rules for New `src/` Models

The next phase should not start by re-implementing another paper verbatim. It should start from CARE's data distribution and hosted metrics.

Required properties:

- Use explicit modality-presence metadata. Zero-filled C0/T2 should never be treated as a real image without a mask.
- Separate scar and edema objectives. Scar is primarily LGE-driven; edema should be T2-aware and reported on T2-present/GT-positive subsets.
- Report every result by modality group and, when possible, by center. A single all-case Dice hides the CenterB/CenterC complete-case versus CenterA/CenterH LGE-only split.
- Optimize Dice and HD/HD95 together. Track connected components, remote components, bbox distance, and volume ratio for pathology labels.
- Use anatomy as a soft reliability constraint, not a hard rule that deletes small true lesions.
- Prefer robust segmentation backbones and CARE-specific routing over fragile paper code paths. A reasonable MyoPS direction is CAA-Seg/SSA-style alignment plus anatomy/pathology cascade with nnU-Net/MedNeXt-like heads. A reasonable Cine direction is motion/strain-aware modeling with explicit hosted-metric calibration.
- Keep nnU-Net as the operational baseline until a new model beats it on the relevant local protocol metric and does not regress hosted validation HD.

## Current Next Steps

1. Wait for the Lane B hosted result from the Round3 `topology_lcc` calibration package.
2. If hosted `myocardium_cinemyops` HD clearly improves, promote `topology_lcc` as the default conservative Cine fallback; otherwise stop topology-guard tuning and analyze hosted metric semantics or stronger Cine model routes.
3. For Lane A, do not add epochs to the current Round11 refiner and do not submit it. Use the Round11 failure-case summary as the current evidence base.
4. If attempting one final refiner salvage, restrict it to a deployable fallback/fusion rule diagnostic using proxy signals only: residual magnitude, distance to baseline edema, distance to myocardium/anatomy support, component size, T2 support, and largest-component fraction. Do not use validation GT, case IDs, or hosted feedback to choose fallbacks.
5. If that deployable salvage is not clean, downgrade the refiner route to an auxiliary baseline-preserving substrate and move Lane A mainline to controlled external/high-upside mechanism integration: T2/LGE intensity prior, anatomy/pathology cascade, boundary/HD control, or missing-modality representation.
6. Do not continue Lane A shallow tweaks: no small-component/ROI postprocess, no Focal Tversky retuning, no simple no-T2 scalar weighting, no anatomy attenuation/hard deletion, no scratch separated route, no whole-network fine-tune, and no direct longer training of Round10/Round11 refiner candidates.
7. Keep the one-zip submission rule explicit: a validation package must contain both `MyoPS/` and `CineMyoPS/`, and the returned `myops_scar`, `myops_edema`, and `myocardium_cinemyops` metrics must be interpreted separately. Lane A currently has no candidate that passes packaging or upload gates.
