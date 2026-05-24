# U-MyoPS Improvement Round8

Date: 2026-05-19

## Goal

Round8 tested the prompt8 hypothesis that the round7 gap to nnU-Net might come from a small number of unreliable Stage1-prior or outlier cases. This was an export-only fold0 round: no training, no fold expansion, no nnU-Net fallback.

The latest fetched CARE2026 validation scar leaderboard file is:

- `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`

It still shows the current `OrganAgent` validation MyoPS scar result as Dice `0.5969`, HD `16.2536`, but that official package used nnU-Net for the MyoPS branch, not U-MyoPS.

## Command

```bash
./env_CARE/bin/python code/U-MyoPS/apply_round8_prior_reliability_gate.py
```

Inputs:

- Round7 baseline: `results/predictions/U-MyoPS_round7_lge_dilated_prior_model_best/fold_0`
- LGE-only fallback: `results/predictions/U-MyoPS_round5_lge_only_no_prior_model_best/fold_0`
- Stage1 prior root: `third_party/U-MyoPS_myops/outputs/asn_myo_tps_tps_ZS_unaligned_1.0_fold0/gen_res`
- Prior tag: `img_de_branch_lab`

## Low-Case Taxonomy

Artifacts:

- `results/diagnostics/baseline_paper_models/U-MyoPS/round08_prior_gate/case_failure_taxonomy.csv`
- `results/diagnostics/baseline_paper_models/U-MyoPS/round08_prior_gate/case_failure_taxonomy.md`

Main findings:

| category | n | mean scar Dice | representative cases |
| --- | ---: | ---: | --- |
| `gt_empty_pred_nonempty` | 1 | 0.0000 | `Case7005` |
| `very_low_prior_pathology_overlap` | 2 | 0.2305 | `Case1029`, `Case8021` |
| `under_segmentation` | 3 | 0.3952 | `Case1053`, `Case5005`, `Case2020` |
| `over_segmentation` | 1 | 0.4545 | `Case3004` |
| `localization_or_mixed` | 37 | 0.6019 | includes `Case1045`, `Case3038`, `Case1062` |

The failure set is heterogeneous. A single broad reliability rule is unlikely to fix all low cases without harming GT-positive small scars.

## Results

Round7 was re-evaluated with HD/HD95 for same-metric comparison.

| variant | all-case scar Dice | scar-positive Dice | complete/T2-present scar | missing-modality scar | scar HD | scar HD95 | interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| round7 baseline | 0.5539 | 0.5668 | 0.6571 | 0.4949 | 35.0772 | 14.6865 | baseline |
| `drop_empty_gt_like_false_positive_proxy` | 0.5581 | 0.5478 | 0.6255 | 0.5196 | 34.4867 | 13.8297 | not reliable; deletes GT-positive tiny scars |
| `tiny_c0_lge_no_t2_suppression` | 0.5766 | 0.5668 | 0.6571 | 0.5306 | 34.2800 | 14.3527 | diagnostic-only; crosses via one empty-GT case |
| `prior_reliable_keep_lge_fallback` | 0.5426 | 0.5552 | 0.6500 | 0.4812 | 35.8062 | 16.0122 | worse |
| `component_hd_guard` | 0.5553 | 0.5682 | 0.6567 | 0.4974 | 28.3333 | 13.8978 | best reliable HD/Dice tradeoff |
| `volume_ratio_guard` | 0.5542 | 0.5671 | 0.6570 | 0.4954 | 31.5742 | 14.6030 | modest HD gain |

Prediction/metric dirs:

- `results/predictions/U-MyoPS_round8_drop_empty_gt_like_false_positive_proxy/fold_0`
- `results/predictions/U-MyoPS_round8_tiny_c0_lge_no_t2_suppression/fold_0`
- `results/predictions/U-MyoPS_round8_prior_reliable_keep_lge_fallback/fold_0`
- `results/predictions/U-MyoPS_round8_component_hd_guard/fold_0`
- `results/predictions/U-MyoPS_round8_volume_ratio_guard/fold_0`
- Matching metrics live under `results/metrics/unified/<variant>/fold_0/`

## Interpretation

The only all-case Dice crossing rule is `tiny_c0_lge_no_t2_suppression`, but it changes exactly one case: `Case7005`, which has empty GT scar and a tiny U-MyoPS scar prediction. The rule does not improve scar-positive Dice; it only changes the local empty-GT accounting from 0 to 1 for that case. This is a useful diagnostic that empty-GT false positives matter, but it is not enough evidence for a robust U-MyoPS submission branch.

The best reliable export-only result is `component_hd_guard`: all-case scar improves slightly from `0.5539` to `0.5553`, scar-positive improves from `0.5668` to `0.5682`, and scar HD improves from `35.08` to `28.33`. It is a genuine HD/outlier cleanup, but it remains below the nnU-Net Dataset501 fold0 scar `0.5602` and 5-fold mean scar `0.5592`.

The LGE-only fallback and volume ratio guards do not solve the core problem. They either hurt Dice or provide only small HD gains.

## Decision

Round8 is not a strong success for U-MyoPS. Pure U-MyoPS has not produced a reliable fold0 improvement over nnU-Net. The diagnostic-only tiny-scar suppression can be kept as an audit artifact, but should not justify expanding folds or replacing nnU-Net in the MyoPS validation branch.

Recommendation:

- Do not expand U-MyoPS folds 1-4.
- Do not submit U-MyoPS as the MyoPS branch.
- If a round9 is required, it should not be another post-processing gate. The only defensible U-MyoPS continuation is a very small model-side HD/outlier fine-tune based on `component_hd_guard`; otherwise stop the U-MyoPS baseline mainline and move effort to a new `src/` model or nnU-Net/MyoPS-Net branch improvements.
