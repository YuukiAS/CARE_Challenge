# CARE Myocardium Final Sprint System Audit

Date: 2026-06-19
Mode: read-only audit plus report writing. No training code was changed, no long training was launched, no prediction cache or submission zip was overwritten.
Report scope: final-sprint decision support for the three hosted validation metrics: `myops_scar`, `myops_edema`, and `myocardium_cinemyops`.

## Executive Summary

The main correction for the final sprint is semantic discipline. One `CARE-Myocardium-OrganAgent.zip` contains both `MyoPS/` and `CineMyoPS/`; the platform returns all three hosted metrics from that single upload. A hybrid package can use one model for the `MyoPS/` branch and another for `CineMyoPS/`, but it still spends one validation attempt and must be interpreted as three separate task scores.

Only the first visible `OrganAgent` hosted row at `20260519 00:06:58` is treated here as the trusted local hosted submission result, per instruction. Later `OrganAgent` rows exist on the leaderboard, and local upload-ready candidates exist, but this audit does not claim them as local method improvements unless the local registry explicitly ties the candidate to a hosted result. Other users' scores are external references only.

Current sprint priority should be:

1. `myocardium_cinemyops`: highest priority. The first trusted hosted result is very poor (`Dice=0.1748`, `HD=75.2130`), while local proxy metrics are known to be semantically mismatched. The biggest near-term gain is likely from hosted metric calibration and cine branch repair, not another generic model search.
2. `myops_edema`: second priority. The dataset has a structural T2/edema supervision problem: only 80/220 training cases have T2 and edema labels, while all 15 validation cases have C0+LGE+T2. T2-aware routing or complete-case teacher diagnostics are still more defensible than more whole-network fine-tuning.
3. `myops_scar`: lower priority unless a very small HD-safe postprocess or LGE scar expert shows clear evidence. nnU-Net remains the most robust local baseline; MyoPS-Net and U-MyoPS did not produce a reliable replacement.

## Source Index And Missing Files

Required files/directories checked:

| path | status | note |
| --- | --- | --- |
| `README.md` | exists | current runbook, status, submission semantics, method conclusions |
| `CARE-README.md` | missing | no separate CARE README found |
| `AGENTS.md` | exists | repo governance; current worktree has pre-existing modifications |
| `SERVER.md` | exists | data conversion and nnU-Net runbook |
| `env_nnunet.sh` | exists | sets `nnUNet_raw`, `nnUNet_preprocessed`, `nnUNet_results`, trainer |
| `jobs/README.md` | exists | benchmark entrypoint documentation |
| `jobs/run_unified_benchmark_test.sh` | exists | single-fold workflow; currently defaults `nnUNet=skip`, other baselines `run` |
| `jobs/run_unified_benchmark_all.sh` | exists | all-fold workflow; defaults all models to `run` and should not be used blindly in final sprint |
| `jobs/benchmark_protocol_helpers.sh` | exists | protocol/split helper |
| `results/submissions/` | exists | upload-ready packages and manifests |
| `results/leaderboard/` | exists | refreshed official API snapshots |
| `results/evaluation/` | missing | metrics live under `results/metrics/` and diagnostics under `results/diagnostics/` |
| `models/` | exists | symlinked nnU-Net folds and selected paper-model checkpoints |
| `data/` | exists | raw challenge data, nnU-Net data, benchmark staging |
| `data/nnUNet/` | exists | physical raw/preprocessed/results dirs |
| `docs/notes/` | exists | baseline and deep research notes |
| `prompts/DeepResearch/` | exists | `DeepResearch_prompt.md` |
| `baseline_report.md` | missing | no root-level baseline report |
| `CARE_Deep_Research_Result1.pdf` | missing | equivalent found at `docs/notes/deep_research/Result1.pdf` |
| `CARE_Deep_Research_Result2.pdf` | missing | equivalent found at `docs/notes/deep_research/Result2.pdf` |

The working tree was not clean before this audit (`AGENTS.md`, `TODO.md`, `.agents/`, Vibe-related files, etc.). No attempt was made to revert or normalize those changes.

## Official Leaderboard Snapshot

Refresh command:

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

Fetch result:

| artifact | fetched at |
| --- | --- |
| `results/leaderboard/care2026_myocardium_latest.json` | `20260619T101153Z` |
| `results/leaderboard/care2026_myocardium_myops_scar_latest.csv` | 22 rows |
| `results/leaderboard/care2026_myocardium_myops_edema_latest.csv` | 22 rows |
| `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv` | 25 rows |

Official links used:

- CARE home: `https://zmic.org.cn/care_2026/`
- CARE validation submission page: `https://zmic.org.cn/care_2026/valid_submission/`
- Evaluation API base used by script: `https://zmic.org.cn/flask`
- Scoreboard URL mentioned in local notification: `https://zmic.org.cn/care_2026/eval/scoreboard?track=myocardium`

The public validation submission page states the CARE-Myocardium zip layout has top-level `MyoPS/` and `CineMyoPS/` branches. It also says validation evaluation is allowed up to 10 times per task per team. In this repo, the practical packaging rule is stricter and safer for Myocardium: one zip contains both branches and returns all three task metrics together.

### `myops_scar` latest snapshot

Leaderboard columns: `rank`, `user`, `time`, `Dice`, `HD`, `PRE`, `SEN`, `score`.

| rank | user | ours? | time | Dice | HD | PRE | SEN | note |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | ZQH | no | 20260515 16:16:04 | 0.8390 | 6.2775 | 0.8252 | 0.8563 | external reference only |
| 2 | ZQH | no | 20260610 00:01:21 | 0.7140 | 13.9073 | 0.7174 | 0.7373 | external reference only |
| 3 | Sheffield_Heart | no | 20260607 00:00:09 | 0.7087 | 16.1831 | 0.6869 | 0.7546 | external reference only |
| 4 | Sheffield_Heart | no | 20260610 00:21:35 | 0.7087 | 16.1831 | 0.6869 | 0.7546 | external reference only |
| 5 | CTest | no | 20260604 00:43:45 | 0.7068 | 16.1211 | 0.6757 | 0.7669 | external reference only |
| 6 | Monster | no | 20260605 00:00:49 | 0.7068 | 16.1211 | 0.6757 | 0.7669 | external reference only |
| 7 | Sheffield_Heart | no | 20260603 00:00:14 | 0.6871 | 18.8667 | 0.6647 | 0.7312 | external reference only |
| 18 | OrganAgent | yes, trusted first hosted row | 20260519 00:06:58 | 0.5969 | 16.2536 | 0.5675 | 0.7130 | first local hosted submission for this audit |

Other `OrganAgent` rows are present at ranks 8, 9, 15, and 18, but only rank 18 at `20260519 00:06:58` is used as the trusted local hosted result in this report.

### `myops_edema` latest snapshot

Leaderboard columns: `rank`, `user`, `time`, `Dice`, `HD`, `PRE`, `SEN`, `score`.

| rank | user | ours? | time | Dice | HD | PRE | SEN | note |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | ZQH | no | 20260515 16:16:04 | 0.8536 | 8.6853 | 0.8575 | 0.8591 | external reference only |
| 2 | ZQH | no | 20260610 00:01:21 | 0.7324 | 20.4347 | 0.7826 | 0.7229 | external reference only |
| 3 | ZQH | no | 20260522 00:31:02 | 0.7058 | 23.6721 | 0.7228 | 0.7479 | external reference only |
| 4 | ZQH | no | 20260527 16:54:28 | 0.7058 | 23.6721 | 0.7228 | 0.7479 | external reference only |
| 5 | CTest | no | 20260604 00:43:45 | 0.6884 | 27.2799 | 0.6683 | 0.7539 | external reference only |
| 6 | Monster | no | 20260605 00:00:49 | 0.6884 | 27.2799 | 0.6683 | 0.7539 | external reference only |
| 7 | Monster | no | 20260611 01:25:42 | 0.6790 | 22.1213 | 0.6379 | 0.8000 | external reference only |
| 16 | OrganAgent | yes, trusted first hosted row | 20260519 00:06:58 | 0.6496 | 22.0125 | 0.6392 | 0.7256 | first local hosted submission for this audit |

Other `OrganAgent` rows are present at ranks 12, 16, 20, and 22, but only rank 16 at `20260519 00:06:58` is used as the trusted local hosted result in this report.

### `myocardium_cinemyops` latest snapshot

Leaderboard columns: `rank`, `user`, `time`, `Dice`, `HD`, `score`.

| rank | user | ours? | time | Dice | HD | note |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | NCC1H | no | 20260515 16:16:58 | 0.2594 | 38.1004 | external reference only |
| 2 | NCC1H | no | 20260515 16:16:45 | 0.2560 | 40.1528 | external reference only |
| 3 | NCC1H | no | 20260529 00:31:26 | 0.2533 | 40.1827 | external reference only |
| 4 | NCC1H | no | 20260517 00:59:34 | 0.2504 | 37.7931 | external reference only |
| 5 | NCC1H | no | 20260520 01:16:18 | 0.2468 | 44.1389 | external reference only |
| 6 | NCC1H | no | 20260515 16:16:32 | 0.2464 | 38.5015 | external reference only |
| 7 | NCC1H | no | 20260521 02:01:47 | 0.2442 | 41.2517 | external reference only |
| 8 | NCC1H | no | 20260527 17:17:09 | 0.2329 | 44.7131 | external reference only |
| 13 | OrganAgent | yes, trusted first hosted row | 20260519 00:06:58 | 0.1748 | 75.2130 | first local hosted submission for this audit |

Other `OrganAgent` rows are present at ranks 11, 12, 13, and 19, but only rank 13 at `20260519 00:06:58` is used as the trusted local hosted result in this report.

## Submission Semantics

Verified sources:

- `README.md` says one `CARE-Myocardium-OrganAgent.zip` contains both `MyoPS/` and `CineMyoPS/`, and each upload returns `myops_scar`, `myops_edema`, and `myocardium_cinemyops`.
- `scripts/submission/prepare_care_myocardium_validation.py` builds the same layout, remaps compact labels to raw labels, and validates both branches in one zip.
- Official validation page shows the CARE-Myocardium zip layout with both `MyoPS/` and `CineMyoPS/`.

Important consequence: do not plan three separate validation uploads for scar, edema, and CineMyoPS. A final-sprint package can mix model sources across branches, for example `nnUNet` for MyoPS plus a topology-repaired or motion-aware CineMyoPS branch, but that package still spends one validation attempt and all three hosted metrics must be interpreted separately.

## Data Structure Audit

### Raw data and nnU-Net tasks

| task | raw source | nnU-Net dataset | training cases | validation raw cases | model input |
| --- | --- | --- | ---: | ---: | --- |
| MyoPS | `data/CARE_Challenge/MyoPS_train` | `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS` | 220 | 15 | 3D LGE/T2/C0 |
| CineMyoPS | `data/CARE_Challenge/CineMyoPS_train` | `data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS` | 64 | 15 | 4D cine reduced to one 3D frame for Dataset502 |

`SERVER.md` and `data/nnUNet/nnUNet_raw/*/dataset.json` define:

- Dataset501 channels: `0=LGE`, `1=T2`, `2=C0`.
- Dataset501 labels: `1=myocardium`, `2=LV_blood`, `3=RV_blood`, `4=edema`, `5=scar`.
- Dataset502 channel: `0=Cine`.
- Dataset502 labels: `1=myocardium`, `2=LV_blood`, `3=scar`.

Raw-to-compact mapping in `code/nnUNet/nnunet_label_utils.py`:

| raw label | compact | meaning |
| ---: | ---: | --- |
| 0 | 0 | background |
| 200 | 1 | myocardium |
| 500 | 2 | LV blood |
| 600 | 3 | RV blood |
| 1220 | 4 | edema |
| 2221 or 1 | 5 | scar |

Submission compact-to-raw mapping:

- MyoPS compact `1/2/3/4/5` -> raw `200/500/600/1220/2221`.
- Cine compact `1/2/3` -> raw `200/500/2221`.
- The packager enforces at least one pathology raw label because the official validator rejected missing pathology labels in an earlier package.

### MyoPS modality, label, and center structure

Read-only scan over `data/CARE_Challenge/MyoPS_train`:

| modality group | cases | share | centers | edema label present | scar label present |
| --- | ---: | ---: | --- | ---: | ---: |
| `C0+LGE+T2` | 80 | 36.4% | CenterB 35, CenterC 45 | 80/80 | 79/80 |
| `C0+LGE` | 24 | 10.9% | CenterE 7, CenterF 9, CenterG 8 | 0/24 | 18/24 |
| `LGE only` | 116 | 52.7% | CenterA 81, CenterH 35 | 0/116 | 115/116 |

Validation `MyoPS_val` is structurally different:

- 15/15 cases have `C0+LGE+T2`.
- Validation labels are not provided locally.
- Validation spacing is mostly 10 mm through-plane; in-plane spacing varies.

Implications:

- Edema supervision is structurally tied to T2 availability. No-T2 cases should not be treated as strong edema negatives.
- Missingness is center-correlated. A model can learn center shortcuts if missing T2 is represented only as a zero image.
- nnU-Net zero-fills missing T2/C0. This is operationally simple but semantically risky for edema.
- Scar is mostly LGE-driven and remains present even in no-T2 cases, so scar and edema should not share one unqualified missing-modality conclusion.

### CineMyoPS structure

Read-only scan over `data/CARE_Challenge/CineMyoPS_train`:

| item | finding |
| --- | --- |
| cases | 64 |
| raw cine dimensionality | 4D `(x, y, z, t)` |
| frame counts | 64/64 have 30 frames |
| centers | `center_alpha` 40, `center_beta` 24 |
| raw labels | `{0, 200, 500, 2221}` |
| scar raw `2221` presence | 63/64 cases |

Read-only scan over `data/CARE_Challenge/CineMyoPS_val`:

| item | finding |
| --- | --- |
| cases | 15 |
| frame counts | 14 cases have 30 frames, 1 case has 50 frames |
| labels | no validation labels locally |

Dataset502 conversion:

- `code/nnUNet/convert_cine_to_nnunet.py` extracts one 3D frame from the 4D cine. Default `--time-index -1` means the middle frame.
- The local Dataset502 label space has no edema label and only treats compact class `3` as scar.
- This makes local `class_1` myocardium Dice, local `class_3` scar sanity, and hosted `myocardium_cinemyops` difficult to align. Current reports already define `hosted_local_metric_mismatch` as a risk category.

## Baseline And Local Results

### nnU-Net baseline

`results/metrics/nnUNet.md` is the most trustworthy 5-fold structured summary.

Dataset501 fold-wise mean validation Dice:

| fold | mean val Dice |
| ---: | ---: |
| 0 | 0.6940 |
| 1 | 0.7139 |
| 2 | 0.7326 |
| 3 | 0.7084 |
| 4 | 0.6991 |

Dataset501 per-class Dice mean over folds:

| class | meaning | mean Dice |
| ---: | --- | ---: |
| 1 | myocardium | 0.7547 |
| 2 | LV_blood | 0.9272 |
| 3 | RV_blood | 0.8872 |
| 4 | edema | 0.4197 |
| 5 | scar | 0.5592 |

Dataset502 per-class Dice mean over folds:

| class | meaning | mean Dice |
| ---: | --- | ---: |
| 1 | myocardium | 0.6808 |
| 2 | LV_blood | 0.8874 |
| 3 | scar | 0.2586 |

Caveat: `results/metrics/unified/nnUNet501/aggregate.json` is only one fold and has a class-4 value whose evaluation denominator differs from `nnUNet.md`; do not mix these numbers.

### First trusted hosted OrganAgent package

Local candidate path:

```text
results/submissions/care_myocardium_validation/upload_ready/20260518_030921__nnUNet_MyoPS+CineMyoPS_pathology_direct/CARE-Myocardium-OrganAgent.zip
```

Manifest summary:

| branch | model source | details |
| --- | --- | --- |
| `MyoPS/` | nnU-Net | `folds=['0']`, `checkpoint_best.pth` |
| `CineMyoPS/` | CineMyoPS | `fold_0`, `Task026_Cine_4D`, `CARECineMyoPSTrainerBNCalib`, `model_final_checkpoint`, `num_frames=4`, `combine_mode=pathology_direct` |
| package QA | pass | 30 prediction files; no pathology fallback cases |

Trusted hosted result at `20260519 00:06:58`:

| task | hosted Dice | hosted HD | local interpretation |
| --- | ---: | ---: | --- |
| `myops_scar` | 0.5969 | 16.2536 | MyoPS nnU-Net fold0 validation branch |
| `myops_edema` | 0.6496 | 22.0125 | same MyoPS branch; validation data complete-modality |
| `myocardium_cinemyops` | 0.1748 | 75.2130 | CineMyoPS `pathology_direct`; severe hosted/local semantic or topology risk |

## Submission Candidate Audit

| candidate path | local branch sources | submitted? | hosted metrics accepted in this audit? | metrics | risk |
| --- | --- | --- | --- | --- | --- |
| `results/submissions/care_myocardium_validation/nnunet_5fold_best/packages/CARE-Myocardium-OrganAgent_20260512_124536.zip` | nnU-Net 5-fold | yes, failed | no | platform error: missing pathology label in `Case1009` | high; packaging lesson only |
| `results/submissions/care_myocardium_validation/nnunet_5fold_best/packages/CARE-Myocardium-OrganAgent_20260517_formatfix.zip` | nnU-Net 5-fold plus pathology fallback | archive/review | no | no trusted hosted row tied here | medium; fallback changed 3 Cine cases |
| `upload_ready/20260517_reviewtest__nnUNet_reviewtest/CARE-Myocardium-OrganAgent.zip` | explicit nnU-Net 5-fold MyoPS and Cine | archive/debug | no | no trusted hosted row tied here | medium; 3 one-voxel Cine fallbacks |
| `upload_ready/20260518_030921__nnUNet_MyoPS+CineMyoPS_pathology_direct/CARE-Myocardium-OrganAgent.zip` | MyoPS nnU-Net fold0; CineMyoPS fold0 `pathology_direct` | yes | yes, first hosted row only | scar 0.5969/16.2536; edema 0.6496/22.0125; cine 0.1748/75.2130 | trusted baseline |
| `upload_ready/20260519_083839__nnUNet_MyoPS+CineMyoPS_pathology_direct_lcc_hd_repair/CARE-Myocardium-OrganAgent.zip` | MyoPS copied from first package; Cine LCC repair | local candidate | no | local class_3 LCC improved Dice/HD95 but no trusted hosted row tied here | medium; hosted metric hypothesis unconfirmed |
| `upload_ready/20260519_084057__nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8/CARE-Myocardium-OrganAgent.zip` | nnU-Net 5-fold MyoPS and Cine | local comparison anchor | no | no trusted hosted row tied here; manifest has 3 Cine fallback cases | medium-high; fallback may distort hosted Cine |
| `upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/CARE-Myocardium-OrganAgent.zip` | MyoPS copied from 20260519 nnU-Net 5-fold anchor; Cine topology LCC | recommended local candidate | no | local Cine class_3 HD95 improved; no trusted hosted row tied here | medium; best calibration package, but upload status/hosted score must be manually confirmed |

The upload-ready README calls the 20260520 topology LCC package the current recommendation. This audit agrees it is the cleanest Cine hosted-calibration candidate, but it does not count it as a local hosted improvement without an explicit hosted row mapping.

## Task-Specific Bottleneck Audit

### 1. `myops_scar`

Evidence:

- Scar is present in 212/220 Dataset501 labels and is not tied to T2 availability.
- Scar appears in 115/116 LGE-only cases and 18/24 C0+LGE no-T2 cases.
- nnU-Net 5-fold local scar mean Dice is 0.5592; trusted hosted scar Dice is 0.5969 with HD 16.2536.
- MyoPS-Net and U-MyoPS did not reliably beat nnU-Net on fold0 all-case scar.

Technical bottleneck:

- Scar is small and LGE-driven. Dice can look acceptable while remote false positives hurt HD.
- The main risk is not missing T2; it is small lesion localization, remote islands, and HD-sensitive topology.
- More generic multimodal fusion is unlikely to help unless it preserves LGE scar localization and improves HD.

Route assessment:

- nnU-Net remains the operational baseline.
- MyoPS-Net round8 raw expert failed badly: all-case scar Dice 0.2426; hybrid 0.5048, still below nnU-Net fold0 0.5602.
- U-MyoPS round8 `component_hd_guard` improved HD modestly but all-case scar Dice 0.5553 stayed below nnU-Net fold0/5-fold.
- Further scar work should be limited to HD-safe postprocess diagnostics or a deployable LGE scar calibration rule. Do not restart MyoPS-Net or U-MyoPS as a mainline.

### 2. `myops_edema`

Evidence:

- Edema label presence is perfectly aligned with T2 presence in training: 80/80 complete cases have edema; 140/140 no-T2 cases have no edema.
- Validation `MyoPS_val` is 15/15 complete-modality.
- nnU-Net zero-fills missing T2/C0, which can make missing T2 look like a real low-intensity channel.
- Local nnU-Net 5-fold edema Dice mean is 0.4197, while trusted hosted edema Dice is 0.6496. The hosted validation set likely rewards complete-modality behavior more than all-training-case local fold metrics.

Technical bottleneck:

- The problem is not simply class imbalance. It is T2-dependent label observability plus center-confounded missingness.
- Complete-case training can overfit CenterB/CenterC style.
- No-T2 cases should not contribute strong edema-negative supervision, but simply downweighting them created false-positive risks in prior rounds.

Route assessment:

- Round2 small-component/ROI postprocessing failed.
- Round4 focal/Tversky/no-T2 downweighting failed guardrails.
- Round7 six-channel modality-presence pipeline showed feasible wiring but no clean gate.
- Round8 T2-present edema expert had a plausible mechanism but scratch/very-short training collapsed and did not beat nnU-Net.
- Rounds9-15 baseline-preserving adaptation/refiner/feature-head routes were safe but too weak or fragmented CenterC cases.

Most useful next direction:

- A bounded T2-present/complete-case teacher or calibrator should be tested only if it preserves scar unchanged, keeps no-T2 empty-GT clean, and improves CenterC component/HD behavior. Otherwise stop Lane A and spend attempts on Cine.

### 3. `myocardium_cinemyops`

Evidence:

- Trusted hosted Dice is only 0.1748 with HD 75.2130.
- Dataset502 local class_1 myocardium Dice is around 0.6808 over 5 folds, but hosted `myocardium_cinemyops` is far lower, so class_1 is not a reliable hosted proxy by itself.
- Dataset502 local class_3 scar mean Dice is only 0.2586 over 5 folds, closer to hosted magnitudes.
- The Cine wrapper and submission map compact class `3` to raw `2221`; no edema exists in Dataset502.
- Cine local LCC topology repair improved class_3 HD95 from 26.6533 to 18.7983 and reduced components from 5.5385 to 1.0000 without changing class_1.

Technical bottleneck:

- The hosted metric name `myocardium_cinemyops` is ambiguous relative to local class names. Local reports already warn that class_1 stability plus class_3/raw topology changes may be a hosted/local mismatch.
- The current nnU-Net Dataset502 baseline extracts a single frame from a 4D cine; the CineMyoPS paper-replication path samples multiple frames, but current submission candidates still need hosted calibration.
- Hosted HD is extremely poor in the first trusted row, consistent with fragmented or remote pathology/topology problems.

Most useful next direction:

- First resolve hosted semantics and topology by submitting or confirming the 20260520 LCC calibration candidate if it has not already been evaluated.
- If LCC does not improve hosted Cine, stop class_3 postprocess tuning and move to a motion/temporal cine route, ideally using a preverified open foundation/strain component in a one-case smoke test before training.

## Prior Route Failure Audit

### nnU-Net baseline

Original purpose: strong self-configuring segmentation baseline.

CARE adaptation:

- Dataset501: LGE/T2/C0, zero-filled missing T2/C0, compact 6-class labels.
- Dataset502: single 3D cine frame from 4D cine, compact 4-class labels.

Status:

- Best local baseline for MyoPS scar/edema.
- Weak for Cine hosted metric because local Dataset502 semantics and hosted `myocardium_cinemyops` do not line up cleanly.

### MyoPS-Net

Original paper assumption: multi-sequence pathology segmentation with coherent multi-sequence inputs and modality-specific fusion.

CARE adaptation:

- The wrapper had to handle `C0/LGE/T2` plus blank `T1m` and `T2starm` channels in the submission packager.
- Later notes say the Challenge3 variant removed nonexistent `T1m/T2*` mapping paths, changed edema supervision to CARE raw labels, disabled incompatible PI/mapping losses, and tried T2-aware/boundary/ROI losses.

Mismatch:

- CARE has 52.7% LGE-only and 10.9% C0+LGE no-T2 training cases.
- A hard multi-sequence fusion architecture is a bad fit unless missingness is first-class.

Result:

- Round8 raw expert all-case edema 0.2779, scar 0.2426.
- Round8 round4-scar hybrid edema 0.3293, scar 0.5048.
- Both fail vs nnU-Net fold0 edema 0.3944 and scar 0.5602.

Conclusion:

- Stop as a baseline-improvement route. Keep only the useful diagnostics and explicit modality metadata ideas.

### U-MyoPS

Original paper assumption: multi-sequence alignment and anatomy/pathology priors.

CARE adaptation:

- Stage1/Stage2 pipeline was adapted with subject metadata, CARE folds, absent-modality handling, and export fixes.

Mismatch:

- CARE is not a fully observed three-sequence setting.
- Stage1 prior reliability is heterogeneous.
- Validation Stage1-to-Stage2 inference is not fully packaged for validation submission; the packager explicitly raises unless a compact prediction dir is supplied.

Result:

- Best reliable round8 scar tradeoff (`component_hd_guard`) reached all-case scar Dice 0.5553, still below nnU-Net fold0 0.5602 and 5-fold 0.5592.
- Apparent all-case Dice crossing came from an empty-GT artifact, not scar-positive improvement.

Conclusion:

- Useful evidence source for anatomy/prior reliability, not a replacement branch.

### CineMyoPS

Original paper assumption: cine-only joint pathology inference from temporal information.

CARE adaptation:

- Current repo has both Dataset502 single-frame nnU-Net and Task026/CineMyoPS-style multi-frame wrappers.
- Submission maps compact class `3` to raw scar `2221`; no edema branch exists for Cine.

Mismatch:

- Hosted `myocardium_cinemyops` does not clearly equal local class_1 myocardium.
- Local class_3 scar sanity/topology may matter more than local class_1 Dice.

Result:

- First trusted hosted Cine row is weak: Dice 0.1748, HD 75.2130.
- Local LCC repair improved class_3 HD/HD95 and components, but hosted confirmation is not accepted in this audit.

Conclusion:

- Highest priority, but the first step is hosted semantic calibration, not broader paper hunting.

### Postprocessing

MyoPS:

- Edema small-component/ROI deletion and hard anatomy support did not produce clean improvements and can delete true lesions.
- Scar HD-sensitive postprocess remains plausible only if bounded and deployable.

Cine:

- LCC topology repair is the best-supported postprocess candidate because it improves class_3 HD95 and components without class_1 drift.
- It still needs hosted confirmation.

### Submission packaging

Strengths:

- The current packager enforces legal raw labels, branch structure, case counts, and pathology presence.
- Upload-ready directories are timestamp-first and include manifests.

Risks:

- Pathology fallback can create artificial one-voxel scars for missing-pathology cases. This may satisfy the validator but can distort hosted HD/Dice.
- Some local zips include directory entries, so `zipinfo` file counts can include directories; manifest-level branch QA is more reliable than raw zip entry count.

## Deep Research Report Assessment

PDFs inspected:

- `docs/notes/deep_research/Result1.pdf`, 6 pages, title `深度调研报告：2024年以来心肌CARE任务相关进展`
- `docs/notes/deep_research/Result2.pdf`, 9 pages, title `心肌分割竞赛文献检索`

Overall judgment: the reports contain useful search leads, but they overstate readiness. They mix confirmed open repositories, unverified future/preprint claims, cross-domain brain-tumor methods, and broad method names. They should not drive another auto-research sprint. Every item must enter through a small, measurable CARE-specific gate.

### Can try immediately, but only as bounded smoke

| method | evidence | task fit | constraint |
| --- | --- | --- | --- |
| CineMA | arXiv and GitHub confirm code, MIT license, HuggingFace fine-tuned models; targets cine ventricle/myocardium segmentation | `myocardium_cinemyops` anatomy/feature backbone | first do one-case inference/shape/license smoke; do not assume scar prediction |
| CAA-Seg / SSA | arXiv and GitHub confirm code, MIT license; directly addresses multi-sequence CMR misalignment | `myops_scar`, maybe `myops_edema` | only useful if overlays show C0/T2/LGE slice mismatch; CARE missing T2 limits broad use |
| BoundaryDoU / lightweight boundary losses | code exists for a medical boundary loss; simpler than InverseForm | scar/edema HD auxiliary | use only in a tiny loss smoke or post-hoc evaluator; not a full training route |
| Unified Focal Loss | GitHub exists per report and is lightweight | small lesion imbalance | prior Focal/Tversky route failed; can only be auxiliary, not mainline |

### Worth querying but not confirmed enough for mainline

| method | why query | decision criterion | fallback |
| --- | --- | --- | --- |
| MTI-MyoScarSeg | arXiv confirms strong Cine scar relevance, but no code was confirmed in web search | code/weights/license available; can extract motion features without reimplementing 400-1000 epoch pipeline | use classical/learned registration or StrainNet-derived motion features as a smoke |
| StrainNet / StrainNet-Transformer | GitHub and Dropbox pre-trained model exist; license unclear from page | license and input requirements compatible; can run on short-axis masks/images within 1 day | use it only as frozen feature/QC; otherwise skip |
| CorSeg-CineSAX | report claims source/weights; quick search did not confirm a clean repo | downloadable weights, permissive license, executable inference on CARE cine | use CineMA or nnU-Net Task114/M&Ms instead |
| ViTa | arXiv confirms a cardiac MRI foundation framework; repo claim needs confirmation and may require tabular inputs | usable weights and simple cine segmentation adaptation | use CineMA first |
| nnU-Net Task114/M&Ms weights | known pretrained direction; needs current compatibility check | can be downloaded via official nnU-Net/Zenodo and license allows challenge | use existing nnU-Net502 as baseline if download or license unclear |
| InverseForm | GitHub/arXiv exists, but it is not a medical-specific 2024 method and integration cost is nontrivial | plug-in loss works on current trainer without destabilizing Dice | use simpler boundary/HD proxy first |

### Not recommended for this sprint

| method | reason |
| --- | --- |
| YoloSAM / SAM-based lesion pipeline | requires box/prompt design and likely external prompt/foundation complexity; not aligned with existing 3D submission pipeline |
| Large-scale MyoPS-Net repair | already failed multiple CARE-specific gates; core modality assumptions mismatch |
| Full U-MyoPS Stage1/Stage2 extension | validation inference bridge incomplete and prior reliability heterogeneous |
| Domain randomization as a mainline | too nonspecific; no evidence it targets the current hosted gaps |
| Whole-network nnU-Net fine-tuning for edema | already failed to produce clean guardrails; high scar regression risk |
| Generic foundation models unrelated to cardiac cine or CMR | likely compliance and integration risk within 20 days |

### Evidence-insufficient or possibly inflated in Deep Research

Items that require external verification before being used for any plan:

- Reports cite several 2026 or future-looking items (`Fang 2026`, `CorSeg-CineSAX 2026`, `CATMIL 2026`, `FALCON 2026`, `CoPeDiT 2026`, future arXiv IDs). Treat as unverified until links, code, license, and reproducibility are checked.
- Claims that CineMA/CorSeg/ViTa can "directly" improve scar are overstated. They primarily improve anatomy or representation unless a scar head is trained.
- Claims that CAA-Seg SSA is "low risk" are overstated for CARE because 140/220 MyoPS cases lack T2 and 116/220 are LGE-only; alignment helps only where multiple real sequences exist.
- Claims that InverseForm is a direct HD shortcut are overstated; it is a loss integration, not a validator-level HD guarantee.

## Further External Query Checklist

These are targeted decision queries, not broad literature search.

| query target | exact question | success criterion | fallback if failed |
| --- | --- | --- | --- |
| CARE leaderboard/submission semantics | Does platform count the Myocardium zip as one upload returning three tasks? Can hosted rows be mapped to uploaded package timestamps? | official answer or dashboard screenshot tying `OrganAgent` timestamps to package names | keep only first trusted row and local manifests; do not claim later hosted gains |
| CAA-Seg / SSA | Is `github.com/yifangao112/CAA-Seg` complete enough to run SSA preprocessing independently? | MIT license, runnable preprocessing/inference docs, no hidden data dependency | implement only a local slice-overlap/alignment diagnostic, not full CAA-Seg |
| MTI-MyoScarSeg | Is code or pretrained motion extractor available? | repo/weights/license found and runnable on one CARE cine case | use optical-flow/registration feature smoke or StrainNet feature audit |
| StrainNet | Can pretrained StrainNet run on CARE short-axis cine using available masks or images? | license clear; one-case output strain/motion map within 1 day | skip; do not hand-build strain pipeline |
| CineMA | Are HuggingFace models downloadable and license-compatible? | MIT/compatible model card; one-case short-axis segmentation inference works | use nnU-Net Task114/M&Ms anatomy pretraining instead |
| CorSeg-CineSAX | Is there a real GitHub repo/weights? | repo, weights, license, inference docs | deprioritize; do not plan around it |
| ViTa | Are weights and segmentation fine-tuning code available without tabular dependency? | model checkpoint plus inference/fine-tune examples | use CineMA first |
| nnU-Net Task114/M&Ms | Can the pretrained model be downloaded and used legally? | official/Zenodo source, model compatible with current nnU-Net, no challenge rule conflict | keep current nnU-Net502 and test only LCC/temporal features |
| InverseForm/boundary loss | Can it be inserted into current nnU-Net/MedNeXt path without trainer surgery? | 1-file loss smoke, no NaN, no Dice collapse on tiny fold | use BoundaryDoU or surface-distance evaluator only |
| small-lesion loss | Is there a lightweight implementation with 3D support? | unit test on current tensors and one fold0 smoke | no loss rewrite; use post-hoc component/threshold diagnostics |

## 20-Day Sprint Recommendation

### Priority 1: `myocardium_cinemyops`

Why:

- Hosted first trusted Dice/HD is worst among all tasks.
- Local/hosted metric mismatch is unresolved.
- A low-cost LCC candidate already exists and directly targets HD/topology.
- The branch can be changed while preserving the MyoPS branch in a hybrid package.

Do first:

- Confirm whether `20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED` has already been uploaded and what hosted row it maps to.
- If not uploaded and attempts allow, consider it the next calibration upload, not a final method claim.
- If hosted improves, make LCC the default Cine fallback and only then consider one small CineMA/StrainNet smoke.
- If hosted does not improve, stop LCC tuning and move to hosted semantic analysis/motion route.

### Priority 2: `myops_edema`

Why:

- There is a real structural T2 supervision gap and the validation set is complete-modality.
- Hosted gap to top teams is meaningful but not as catastrophic as Cine.
- Prior rounds show many safe but weak attempts; any new attempt must be mechanism-specific.

Do second:

- Run a no-training audit or one tiny fold0 diagnostic to test whether T2-present complete-case teacher/calibrator improves CenterC without scar drift.
- Do not submit edema unless fold0 evidence clears scar/no-T2/HD guardrails.

### Priority 3: `myops_scar`

Why:

- nnU-Net is stable.
- Hosted first trusted scar is not catastrophic.
- Paper baselines failed to replace it.

Do only if cheap:

- A deployable LGE scar component/HD audit, not new architecture work.

## Next Minimal Executable Experiments

### Experiment A: hosted Cine LCC calibration mapping

| field | value |
| --- | --- |
| target | `myocardium_cinemyops` |
| input | `upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/CARE-Myocardium-OrganAgent.zip`; latest leaderboard CSVs |
| change scope | none if checking upload status; possible manual validation upload only after user decision |
| expected metric | hosted Cine Dice > 0.1748 and HD < 75.2130; ideally HD approaches < 50 |
| failure criterion | hosted Cine unchanged/worse, or MyoPS branch metrics unexpectedly drift |
| rollback | keep first trusted package as baseline; do not promote LCC |
| note | consumes one validation attempt only if actually uploaded |

### Experiment B: CineMA one-case anatomy smoke

| field | value |
| --- | --- |
| target | `myocardium_cinemyops` |
| input | one `data/CARE_Challenge/CineMyoPS_val/*_Cine.nii.gz` and one training case with label |
| change scope | external repo/weight screening only; no training; outputs under diagnostics if run |
| expected metric | successful shape/spacing-compatible myocardium prediction or feature map; no label-space mismatch |
| failure criterion | cannot download legally, incompatible input orientation, no short-axis model, or no license clarity |
| rollback | delete no files; do not use model; keep nnU-Net/CineMyoPS branch |

### Experiment C: T2-present edema calibrator audit

| field | value |
| --- | --- |
| target | `myops_edema` |
| input | nnU-Net501 fold0 predictions, fold0 GT, modality/center metadata, T2-present CenterB/CenterC cases |
| change scope | read-only or small diagnostic under `results/diagnostics/`; no validation zip |
| expected metric | T2-present GT-positive edema Dice/HD95 improves, CenterC not worse, scar unchanged, no-T2 empty-GT remains clean |
| failure criterion | any scar voxel change, no-T2 FP, CenterC HD/component regression, or only <0.003 Dice gain |
| rollback | keep nnU-Net MyoPS baseline; no package creation |

### Experiment D: CAA-Seg SSA feasibility audit

| field | value |
| --- | --- |
| target | `myops_scar` and `myops_edema` only for complete-modality cases |
| input | a few C0/LGE/T2 complete training cases with known labels |
| change scope | metadata/slice-correspondence diagnostic only |
| expected metric | detect real C0/T2/LGE slice mismatch that correlates with poor edema/scar cases |
| failure criterion | no measurable misalignment or no deployable way to apply only to validation |
| rollback | do not integrate CAA-Seg; keep conversion unchanged |

## Final Decision Rules

1. Do not report leaderboard rows from other users as local results.
2. Do not report later `OrganAgent` rows as local method improvements unless package mapping is manually confirmed.
3. Do not create three separate upload packages for the three metrics.
4. Do not run all-fold benchmark scripts in default mode during final sprint.
5. Do not expand MyoPS-Net/U-MyoPS.
6. For any candidate, report `myops_scar`, `myops_edema`, and `myocardium_cinemyops` separately.
7. For MyoPS, always stratify by T2 presence and center when interpreting edema.
8. For Cine, treat local class_1 and class_3 as separate proxies until hosted semantics are confirmed.
9. Any validation upload must name the exact branch source and expected risk before upload.
10. The immediate next action is hosted Cine LCC calibration mapping, not another broad auto-research loop.
