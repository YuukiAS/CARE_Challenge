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

## Current Myocardium Status

Snapshot: 2026-05-18. Local numbers below are protocol/fold validation results, not hosted validation leaderboard scores.

| Branch | Current best candidate | Local target metric | nnU-Net reference | Status |
| --- | --- | ---: | ---: | --- |
| CineMyoPS | `CineMyoPS_R6_pathology_direct`, fold0, `CARECineMyoPSTrainerBNCalib` | class_1 myocardium proxy `0.6933`; class_3 scar sanity `0.4378` | Dataset502 5-fold class_1 `0.6808`; class_3 `0.2586` | Locally beats nnU-Net on the Cine branch and is the current validation-submission candidate. |
| MyoPS-Net | round4/round7 `combined_safe` route | edema/class_4 `0.3733`; scar/class_5 `0.5048` | Dataset501 5-fold edema `0.4197`; scar `0.5592` | Still below nnU-Net; export-only edema calibration did not help. Continue only with model-level missing-modality/T2-aware changes. |
| U-MyoPS | round5/round6 LGE-only/no-prior scar specialist; round7 prior repair running | previous pure best scar/class_5 `0.5352`; complete/T2-present scar about `0.6463` | Dataset501 5-fold scar `0.5592` | More promising than MyoPS-Net for scar, but not yet above nnU-Net all-case; edema remains weak and should not be assigned to U-MyoPS. |
| nnU-Net | Dataset501/502 5-fold baselines | MyoPS edema `0.4197`, scar `0.5592`; Cine class_1 `0.6808` | reference | Conservative fallback for any branch not yet proven better. |

Current upload-ready package:

```text
results/submissions/care_myocardium_validation/upload_ready/nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921/CARE-Myocardium-OrganAgent.zip
```

This package uses nnU-Net for the MyoPS branch and CineMyoPS `pathology_direct` for the CineMyoPS branch. If uploaded, it will return all three hosted metrics in one submission attempt: MyoPS scores are the nnU-Net baseline branch, while the CineMyoPS score tests the `pathology_direct` branch. Before upload, always run a label-level zip QA, not just a file-count check: every MyoPS case must contain at least one pathology label from `{1220, 2221}`, and every CineMyoPS case must contain `2221`.

## CARE Myocardium Prompt Direction

Current model-improvement prompts under `prompts/{CineMyoPS,MyoPS-Net,U-MyoPS}/` are meant to adapt the three paper baselines to the CARE challenge, not to replace them with unrelated postprocessing. Use this boundary when launching the next Codex round.

| Model | Current prompt | Paper-alignment status | Guardrail |
| --- | --- | --- | --- |
| CineMyoPS | `prompts/CineMyoPS/prompt7_pathology_direct_validation_submission.md` | Closest to the paper route: `pathology_direct` fixed inference uses cine temporal/motion features, ED anatomy, and pathology/scar branch, and now needs official validation packaging. | `cardiac_only` is diagnostic only; final candidates should not permanently discard the pathology branch unless the official metric is confirmed to ignore it. |
| MyoPS-Net | `prompts/MyoPS-Net/prompt7_edema_calibration_and_scar_preservation.md` | CARE adaptation is valid, but this round is last-mile edema calibration, not a replacement for flexible multi-sequence fusion. | If calibration does not clearly help, stop postprocess stacking and return to model-level modality mask/dropout, T2-aware edema head, or robust fusion. |
| U-MyoPS | `prompts/U-MyoPS/prompt7_stage1_prior_repair.md` | Current strongest route (`LGE-only/no-prior`) is a CARE-driven ablation/scar-specialist path, so the next paper-aligned route is Stage1 prior repair rather than more postprocessing. | Label nnU-Net fallback/hybrid as diagnostic; if pure U-MyoPS cannot cross nnU-Net, either use it as a complete-case scar specialist or stop the U-MyoPS mainline. |

The shared goal remains: beat the nnU-Net reference on the relevant CARE leaderboard metric while preserving the literature idea where it is still supported by evidence. When the evidence contradicts a paper assumption, record the result as a CARE-specific ablation rather than presenting it as a faithful paper implementation.
