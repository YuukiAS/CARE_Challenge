# CineMA Adapter Pilot 20260620

## Scope

This note records an isolated CineMA -> CARE CineMyoPS anatomy adapter pilot. It did not modify the main training
pipeline, old CineMyoPS wrappers, validation packaging, or upload-ready submission artifacts.

## Rules Applied

- Task entry: `prompts/tasks/20260620_cinema_adapter_pilot_task.md`.
- Result entry: `prompts/tasks/20260620_cinema_adapter_pilot_result.md`.
- External upload remained disabled.
- Single Slurm job walltime was capped at `08:00:00`.
- GPU job used `htzhulab` with the CARE timestamped tee log style.

## Data Recheck

Output: `results/diagnostics/cinemyops_raw_structure_audit_20260620/`.

Current raw CineMyoPS structure matches the prior concern:

| item | value |
| --- | ---: |
| train cases | 64 |
| validation cases | 15 |
| train frame counts | 64 cases with 30 frames |
| validation frame counts | 14 cases with 30 frames, 1 case with 50 frames |
| train direction hashes | 64 unique |
| validation direction hashes | 6 unique |
| train labels matching one 3D cine frame geometry | 64/64 |
| Dataset502 `imagesTr` / `labelsTr` | 64 / 64 |

Raw train labels used values `{0, 200, 500, 2221}` in 63/64 cases and `{0, 200, 500}` in 1/64 cases. Dataset502 is
documented as `CARE CineMyoPS_train (single Cine frame, middle time by default)`, so it is not a true 4D cine dataset.

## CineMA Resource Check

CineMA was cloned to `results/cinema_adapter/external/CineMA` at commit
`c10daa1d93f0ea28d8b9ad9206b0f673d25805c1`.

Verified from the local clone:

- License: MIT, `results/cinema_adapter/external/CineMA/LICENSE`.
- README: `https://github.com/mathpluscode/CineMA`, mirrored in
  `results/cinema_adapter/external/CineMA/README.md`.
- SAX segmentation inference: `results/cinema_adapter/external/CineMA/cinema/examples/inference/segmentation_sax.py`.
- Input: one SAX timeframe.
- Output labels from the example: `1=RV`, `2=myocardium`, `3=LV`.
- Fine-tuned weights source: `mathpluscode/CineMA` HuggingFace repo, path
  `finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors`.

`env_CARE` did not have MONAI, so `monai==1.5.2` was installed with `--target` into
`results/cinema_adapter/python_deps/` rather than changing the main environment package set.

## Adapter Design

New files:

- `scripts/diagnostics/cinemyops_raw_structure_audit.py`
- `scripts/external_adapters/cinema_care_adapter.py`
- `jobs/experiments/run_cinema_adapter_pilot.sh`

The adapter:

- selects ED/frame 0, middle frame, and one representative frame based on max mean absolute difference from temporal mean;
- center crop/pads each 3D frame to CineMA's fixed `192x192x16` SAX input shape;
- runs CineMA ACDC SAX seed 0 segmentation;
- maps predictions back into the original 3D frame geometry with zero outside the crop/pad region;
- writes one NIfTI prediction per selected frame;
- computes train-case Dice/HD95 against CARE compact `myocardium=1` and `LV=2` labels after raw label remap
  `{200:1, 500:2, 2221:3}`;
- records validation predictions as unlabeled diagnostics only.

## Run

Slurm job:

- Job ID: `55524633`
- Partition: `htzhulab`
- Node: `g1807htzh01`
- Log: `logs/CineMAAdapter_55524633_20260619_131229.log`
- Output: `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`
- Runtime recorded by adapter: `144.341` seconds
- Rows: 234 selected frames
- Train cases: 64
- Validation cases: 15

Files written under the output directory:

- `run_info.json`
- `manifest.csv`
- `metrics.csv`
- `metrics_summary.json`
- `predictions/train/.../*.nii.gz`
- `predictions/val/.../*.nii.gz`

## Metrics

Train, all selected frames:

| metric | mean | median |
| --- | ---: | ---: |
| myocardium Dice | 0.4655 | 0.4866 |
| LV Dice | 0.6775 | 0.7288 |
| myocardium HD95 | 12.1390 | 7.9567 |
| LV HD95 | 12.3675 | 9.1264 |

Train, frame 0 only:

| metric | mean | median |
| --- | ---: | ---: |
| myocardium Dice | 0.5723 | 0.6861 |
| LV Dice | 0.7779 | 0.9092 |
| myocardium HD95 | 11.0684 | 6.0000 |
| LV HD95 | 10.7595 | 6.0000 |

Train, non-frame-0 selected frames:

| metric | mean | median |
| --- | ---: | ---: |
| myocardium Dice | 0.4108 | 0.4204 |
| LV Dice | 0.6261 | 0.6676 |
| myocardium HD95 | 12.6871 | 8.8991 |
| LV HD95 | 13.1978 | 10.9729 |

Validation has no GT in this task; predictions were non-empty for all selected validation frames.

## Interpretation

CineMA can be fetched, loaded, and run on CARE raw 4D CineMyoPS without touching the main pipeline. The adapter preserves
original NIfTI frame geometry for written outputs.

The strongest local signal is at frame 0/ED: LV segmentation is often good and myocardium is usable for many
center_alpha cases. The weak center_beta cases and non-frame-0 Dice show two constraints:

- CARE train GT appears tied to one 3D reference frame, so comparing all timeframes against that label underestimates
  anatomy tracking quality and should not be used as a final multiframe score.
- The current simple center crop/pad is not enough for all centers/geometries, especially small-slice or thick-spacing
  center_beta cases.

Existing `results/metrics/unified/CineMyoPS/aggregate.json` was readable but only had one aggregated fold entry
(`class_1 mean 0.0003976`, `class_2 mean 0.3091`, `class_3 mean 0.00162`), so it is weak comparison evidence rather
than a full 5-fold local baseline summary.

## Next Steps

1. Add a geometry-aware crop around the heart/body foreground instead of center crop, then rerun the same 64/15 pilot.
2. Use frame 0 as the first supervised comparison target unless a reliable ED/ES/reference-frame mapping is proven for
   every train case.
3. Try CineMA `mnms` and `mnms2` SAX checkpoints with the same adapter to test domain robustness.
4. Convert only myocardium/LV anatomy masks into an isolated prior candidate after the crop strategy is stable; do not
   integrate into the main pipeline yet.
