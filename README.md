# CARE Benchmark Runbook

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

## CARE Myocardium Status

Snapshot: 2026-05-19. The current phase is a baseline exit-gate: decide which adapted paper baselines are still worth improving, and preserve the lessons before new model work moves into `src/`.

### Official Validation

The submitted hybrid package was:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip
```

It used nnU-Net for `MyoPS/` and CineMyoPS `pathology_direct` for `CineMyoPS/`. The platform evaluates one zip and returns all three metrics together.

| hosted metric | package branch | OrganAgent Dice | HD | rank | current interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| `myops_scar` | nnU-Net MyoPS | 0.5969 | 16.2536 | 4/5 | Usable baseline, but far behind rank 1 `0.8390 / 6.2775`. |
| `myops_edema` | nnU-Net MyoPS | 0.6496 | 22.0125 | 4/5 | Usable baseline, but far behind rank 1 `0.8536 / 8.6853`. |
| `myocardium_cinemyops` | CineMyoPS `pathology_direct` | 0.1748 | 75.2130 | 6/9 | Dice improved over older attempts, but HD is unacceptable and hosted metric semantics remain partly mismatched with local proxies. |

Current round8 Cine repair candidate, not yet submitted:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_lcc_hd_repair_20260519_083839/CARE-Myocardium-OrganAgent.zip
```

Round8 found 14/15 Cine validation predictions had multiple disconnected `2221` components. The largest-component repair improved local protocol scar HD from `40.4694` to `27.7648` and HD95 from `26.6533` to `18.7983` while slightly improving scar Dice from `0.4378` to `0.4441`.

### Local References

| branch | local best paper-baseline result | nnU-Net reference | decision |
| --- | ---: | ---: | --- |
| CineMyoPS | class_1 proxy `0.6933`; class_3 scar sanity `0.4378`; LCC scar sanity `0.4441` | Dataset502 class_1 `0.6808`; class_3 `0.2586` | Continue only for hosted-metric/HD repair. |
| MyoPS-Net | round4 `combined_safe`: edema `0.3733`, scar `0.5048`; round8 raw expert worse | Dataset501 edema `0.4197`, scar `0.5592` | Stop as a baseline-improvement mainline. |
| U-MyoPS | round7 scar `0.5539`; round8 reliable HD guard `0.5553`; diagnostic-only variant `0.5766` by deleting one empty-GT false positive | Dataset501 scar `0.5592` | Stop as a replacement candidate; keep as ablation evidence. |
| nnU-Net | MyoPS edema `0.4197`, scar `0.5592`; Cine class_1 `0.6808` | reference | Conservative submission fallback. |

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

1. Keep the submitted nnU-Net MyoPS branch as the conservative MyoPS baseline.
2. Submit or inspect the CineMyoPS LCC HD-repair package only as a hosted-metric calibration experiment.
3. Do not expand MyoPS-Net or U-MyoPS to folds 1-4.
4. Move new MyoPS model work into `src/` using the data-driven rules above and the DeepResearch notes under `prompts/DeepResearch/`.
5. Preserve MyoPS-Net and U-MyoPS round8 reports as negative baseline evidence:
   - `docs/notes/baseline/MyoPS-Net_improvement_round8.md`
   - `docs/notes/baseline/U-MyoPS_improvement_round8.md`
