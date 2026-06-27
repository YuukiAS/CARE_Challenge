# Dictionary Bank Selection

status: `SELECT_DICTIONARY_VARIANT`

selected_variant: `cross_modal_interaction_dictionary`

## Decision

Select D4 `cross_modal_interaction_dictionary` for the next compactness/localization step.

## Comparison Matrix

| route | edema GT+ Dice | edema GT+ HD95 | scar all Dice | scar all HD95 | budget status |
| --- | ---: | ---: | ---: | ---: | --- |
| previous `best_srr_recovered` | 0.1928 | 97.7248 | 0.0923 | 127.0317 | reference |
| D1 `multiscale_dictionary` | 0.1001 | 46.4887 | 0.0253 | 109.2368 | OK |
| D2 `task_specific_dictionary` | 0.0968 | 119.2192 | 0.0956 | 126.2523 | OK |
| D4 `cross_modal_interaction_dictionary` | 0.1599 | 114.0297 | 0.1054 | 129.2199 | OK |
| D5 `anchor_guided_dictionary` | 0.1755 | 102.8765 | 0.0877 | 136.8017 | OK |
| D6 `hierarchical_router_dictionary` | 0.2079 | 120.2979 | 0.0651 | 121.4527 | UNDER_BUDGET_MAX_STEPS |

## Rationale

- D4 is the only new variant that clearly improves scar all-case Dice over the previous recovered SRR baseline while keeping an edema signal.
- D6 has the best edema GT-positive Dice, but scar all-case Dice drops below the recovered SRR baseline and the run stopped under the effective-time budget.
- D5 is the best budget-complete edema-side variant, but its scar signal is weaker than both D4 and the previous recovered SRR baseline.
- D2 improves scar slightly over the previous recovered SRR baseline but has the weakest edema behavior and high overprediction burden.
- D1 is not competitive on scar and is not selected despite low edema HD95 on the partial metrics.

## Caveats

- D4 is not submission-ready. Its HD95, component count, and remote false-positive burden remain high.
- The selected next step should be compactness/localization repair for D4, not fold expansion or validation upload.
- No validation upload, external upload, external data, external weights, fold expansion, evaluator change, label mapping change, or split change was performed.
