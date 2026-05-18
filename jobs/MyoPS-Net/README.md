# MyoPS-Net

CARE MyoPS-Net wrappers live in `code/MyoPS-Net/` and `jobs/MyoPS-Net/`. The current active route is fold0-only, short-budget iteration against Dataset501 compact labels `class_4` edema and `class_5` scar.

## Current Status

Latest useful results:

| variant | scope | myops_edema / class_4 | myops_scar / class_5 | note |
| --- | --- | ---: | ---: | --- |
| round4 `combined_safe` | 44 all val cases | 0.3733 | 0.5048 | best export-only all-case result so far |
| round5 full-modality expert | 16 C0+LGE+T2 val cases | 0.3746 | 0.6163 | scar beats nnU-Net on complete cases; edema still below nnU-Net |
| nnU-Net Dataset501 | 5-fold reference | 0.4197 | 0.5592 | direct local baseline |

Round5 trained only on complete C0+LGE+T2 cases and exported on the 16 complete validation cases. It did not yet produce an all-case hybrid package. That is the purpose of round6 below.

## Round6 Export-Only Hybrid

No training. The script exports the round5 full-modality checkpoint on the all-val staging root, then routes:

- complete C0+LGE+T2 cases to the round5 full-modality expert;
- T2-missing cases to the round4 `combined_safe` fallback.

The routing case list must come from the protocol fold validation split (`--fold-json` / `--fold`).
The staging `modalities_present.json` contains train and val cases, so it is metadata only and must not be used as the case list by itself.

Run:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/MyoPS-Net/sbatch_round6_hybrid_export.sh
```

Main outputs:

- `results/metrics/unified/MyoPS-Net_round6_fullmod_on_allval/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/routing_summary.json`
- `results/metrics/unified/MyoPS-Net_round6_hybrid_fullmod_plus_round4/fold_0/modality_group_metrics.md`

Decision rule:

- If hybrid all-case scar exceeds round4 and approaches/exceeds nnU-Net while edema remains stable, use it as the next validation submission candidate for the MyoPS side.
- If fullmod-on-allval collapses on missing-modality cases, keep routing and do not expand to folds 1-4.
- If edema remains below nnU-Net, the next training round should be a T2-present edema expert or calibration round, not a longer continuation of the same full-modality run.

## Round7 Edema Calibration

No training. This is a fold0 export-only calibration round that keeps `class_5` scar from round4 `combined_safe` and only tests label-level edema changes on T2-present or complete-modality cases.

Run:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/MyoPS-Net/sbatch_round7_edema_calibration.sh
```

Implemented variants:

- `keep_round4_scar_round5_edema_complete`: copy round5/fullmod edema on complete C0+LGE+T2 cases, then reapply round4 scar.
- `edema_component_filter`: remove small `class_4` edema components only; scar is unchanged.
- `round5_edema_component_filter`: copy round5/fullmod edema on complete cases, filter small edema components, then reapply round4 scar.
- `edema_support_limited`: limit round4 edema to prediction-derived pathology support on T2-present cases; scar is unchanged.

Main outputs:

- `results/predictions/MyoPS-Net_round7_<variant>/fold_0`
- `results/metrics/unified/MyoPS-Net_round7_<variant>/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round7_<variant>/fold_0/modality_group_metrics.md`

The export wrapper also supports `--edema-softmax-dir` for future T2 edema probability maps if a separate threshold-sweep round is justified. Do not continue postprocessing if label-level calibration remains below the prompt7 stop threshold; the next distinct attempt should be a T2-present edema expert or robust missing-modality fusion round.

## Slurm Notes

Default partition is `htzhulab`. Only switch to `a100-gpu` or `volta-gpu` if `htzhulab` has a materially long wait; use the headers in repo `AGENTS.md` and always set an explicit `--qos`.
