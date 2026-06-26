# Result 20260625 Fast Goal

status: `MYOPS_SRR_SELECTED`

## Summary

- Completed Phase 1 SRR router recovery with three htzhulab GPU jobs.
- Recovery decision: `GO_RESCUE_ABLATION`.
- Completed Phase 2 rescue ablation with two additional htzhulab GPU jobs plus two anchors.
- Model selection: `SELECT_SRR_RECOVERED`; selected `srr_expert_dropout` / `best_srr_recovered`.
- Completed Cine geometry safe/mismatch split and safe-subset reference preflight.
- Cine decision: `GO_CINE_TEMPORAL_PREFLIGHT`.

## MyoPS Selection

| ablation | variant | edema GT+ Dice | edema GT+ HD95 | scar all Dice | scar all HD95 |
| --- | --- | ---: | ---: | ---: | ---: |
| B0 | `best_conditional_control` | `0.1103` | `138.1377` | `0.0581` | `113.4492` |
| B1 | `best_srr_recovered` | `0.1928` | `97.7248` | `0.0923` | `127.0317` |
| B2 | `late_fusion_no_dictionary` | `0.0601` | `129.9965` | `0.0442` | `130.5623` |
| B3 | `retrieval_no_sip_or_weak_sip` | `0.1358` | `115.4910` | `0.0702` | `129.1230` |

Selected `best_srr_recovered` because it is strongest on edema GT-positive Dice and scar all-case Dice among the tested fold0 options. Absolute scores remain low, so the next MyoPS task should target compact lesion localization and false-positive reduction before any fold expansion.

## Cine Result

- Geometry split: `59` strict safe cases and `5` mismatch cases.
- Mismatch cases: `center_alpha_Case1009`, `center_alpha_Case1018`, `center_alpha_Case1020`, `center_alpha_Case1024`, `center_beta_Case2023`.
- Crop/inverse protocol check preserved foreground for all 64 train cases.
- Safe-subset reference preflight used existing CineMA frame0 predictions.
- Safe-subset metrics: class_1 myocardium Dice mean `0.5626`, class_2 LV Dice mean `0.7709`, class_3 scar sanity `0.0000`.

## Verification

- `./envs/env_CARE/bin/python -m py_compile scripts/training/run_srr_myops_fold0.py scripts/evaluation/report_srr_fold0.py` passed.
- `./envs/env_CARE/bin/python -m unittest src.care_myocardium.tests.test_srr_losses src.care_myocardium.tests.test_srr_missingness src.care_myocardium.tests.test_srr_shapes` passed earlier in the goal: 7 tests.
- Phase 1 and Phase 2 Slurm jobs listed in `final_status.md` completed with exit code `0:0`.

## Not Done

- No validation submission, upload-ready package, external upload, external data, networking, folds1-4 expansion, or 5-fold expansion.
- Cine temporal route remains a follow-up after `GO_CINE_TEMPORAL_PREFLIGHT`.
