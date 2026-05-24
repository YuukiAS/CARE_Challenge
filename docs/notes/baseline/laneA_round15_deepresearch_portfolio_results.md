# Lane A Round15 DeepResearch Portfolio Results

Date: 2026-05-23

## Scope

Round15 executed the DeepResearch-guided first-party portfolio gate for Lane A MyoPS edema. It tested the highest-priority CARE-first trainable candidates through bounded fold0 very-short evaluation, without validation packaging, fold1-4 expansion, or external repo training.

Generated diagnostics are under:

```text
results/diagnostics/phase0_phase1/laneA_myops/round15_deepresearch_portfolio/
```

`results/diagnostics/` is intentionally gitignored, so this note preserves the durable result summary.

## Candidates

| candidate | mechanism | gate |
| --- | --- | --- |
| `R15_A_intensity_prior_feature_head_fold0_vs` | T2/LGE intensity-prior feature head | `fail_stop_no_longer_train` |
| `R15_B_anatomy_pathology_cascade_fold0_vs` | anatomy/pathology consistency feature head | `watch_stop_no_clear_positive_signal` |
| `R15_C_intensity_plus_anatomy_support_head_fold0_vs` | combined intensity + anatomy support feature head | `watch_stop_no_clear_positive_signal` |

Overall status:

```text
stop_or_watch_no_promoted_candidate
```

No candidate is promoted to fold0 short, fold1-4, 5-fold, validation zip creation, or upload.

## Key Findings

- All three candidates completed bounded very-short fold0 validation with 44/44 predictions.
- Training losses decreased and no NaN/Inf was observed, so this was not a wiring failure.
- Class-5 scar was unchanged for all candidates.
- no-T2 empty-GT edema stability was clean for all candidates because validation fallback-to-baseline prevented no-T2 FP drift.
- `R15_A` produced the only meaningful prediction change, but the signal was too small and failed component safety.
- `R15_B` and `R15_C` were safe but effectively collapsed to baseline under the conservative fusion threshold.

## Candidate A Failure

`R15_A_intensity_prior_feature_head_fold0_vs` showed a tiny edema Dice/HD95 signal, mostly CenterB-driven:

- all-case edema Dice delta: `+0.002397`
- T2-present GT-positive Dice delta: `+0.002397`
- CenterB Dice delta: `+0.004342`
- CenterC Dice delta: `+0.000884`

The candidate failed because CenterC component behavior was not clean:

- CenterC HD95 slightly worsened.
- CenterC component count worsened.
- `Case3011`, `Case3012`, and `Case3044` were flagged `edema_component_worse`.

Interpretation: the intensity-prior feature head learned a weak correction near the fusion threshold, but it can fragment CenterC edema components. This is not safe enough to continue with more epochs.

## Candidate B/C Failure

`R15_B_anatomy_pathology_cascade_fold0_vs` and `R15_C_intensity_plus_anatomy_support_head_fold0_vs` produced validation predictions effectively identical to baseline:

- edema Dice delta: `0.0`
- edema HD95/component/remote-FP delta: `0.0`
- scar Dice/HD95 delta: `0.0`
- no-T2 empty-GT stability: unchanged

Interpretation: the current anatomy/support scalar features are too weak or too conservative. They do not create unsafe output, but they also do not create useful class-4 edema correction.

## Decision

Do not run longer versions of A/B/C as-is.

Round16 should be narrower and mechanism-specific:

1. Redesign the intensity-support representation so it does not fragment CenterC components.
2. Treat current anatomy scalar features as insufficient; move to stronger lesion-level or representation-level anatomy support if continuing this slot.
3. If using external methods, start with metadata and one-case smoke only, especially I-MMSeg-style intensity prior, Cascaded FSN/PT-Net-style anatomy-lesion consistency, and InverseForm/surface/HD only as a small auxiliary after support is reliable.

Primary evidence files in the ignored diagnostics root:

- `round15_detailed_failure_analysis.md`
- `round15_decision_table.md`
- `round15_candidate_result_collection.csv`
- `baseline_vs_candidate_by_subset.csv`
- `case_level_failure_flags.csv`
- `R15_A_intensity_prior_feature_head_fold0_vs/validation_change_summary.csv`
- `R15_B_anatomy_pathology_cascade_fold0_vs/validation_change_summary.csv`
- `R15_C_intensity_plus_anatomy_support_head_fold0_vs/validation_change_summary.csv`
